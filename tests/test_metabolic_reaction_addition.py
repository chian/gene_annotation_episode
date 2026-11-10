"""Selected direct COBRA addition using an actual retained reaction lookup.

The selected case supplies a numerical control model, explicit participant
correspondences, bounds and independent expected answers. It does not infer an
annotation, choose a model correspondence or prescribe an episode workflow.
"""
from copy import deepcopy
from fractions import Fraction
import builtins
import hashlib
import io
import json
import math
import os
from pathlib import Path

import pytest

from gene_annotation_episode.chemistry import accession, rhea_response, rhea_row
from gene_annotation_episode.domain import RECORD_SCHEMAS, validate_schema
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.native_flux_balance_contracts import (
    ATTEMPT_DIRECTORY_NAME, POLICY, RUN_PLAN_FILENAME, flux_balance_driver_argv,
    flux_balance_environment, validate_flux_balance_software,
)
from gene_annotation_episode.native_flux_balance_storage import (
    file_pin, immutable_bytes, immutable_json, read_json,
)
from test_native_flux_balance_producer_688 import _plan, _parsed_calculated, _selected_bound


ATTEMPT = Path(os.environ["HMMER529_ATTEMPT"]) if "HMMER529_ATTEMPT" in os.environ else None
pytestmark = pytest.mark.skipif(ATTEMPT is None, reason="requires bounded529")


_EDIT_PROGRAM = r'''
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import sys

from gene_annotation_episode.native_flux_balance_driver import _verify_software
from gene_annotation_episode.native_flux_balance_storage import file_pin, immutable_json, read_json

request = read_json(sys.argv[1])
software = read_json(request["software_file"])
_verify_software(software)
import cobra
from cobra.io.dict import model_to_dict
cobra.Configuration().solver = "glpk"

original = Path(request["original_model_file"])
before = file_pin(original)
assert before == request["original_model_pin"]
model = cobra.io.load_json_model(original)
assert model.objective.direction == "max", "this selected JSON control uses a max objective"
before_model = model_to_dict(model)
reaction_record = request["reaction_record"]
participants = {row["ordinal"]: row for row in reaction_record["participants"]}
assert len(participants) == len(reaction_record["participants"])
mapping = request["participant_mapping"]
assert {row["ordinal"] for row in mapping} == set(participants)
assert len(mapping) == len(participants)
assert request["mapping_basis"] == "caller_selected_numerical_control"
assert request["orientation_basis"] == "caller_selected_numerical_control"
assert request["reaction_id"] not in model.reactions, "duplicate reaction IDs must not be silently ignored"
lower, upper = request["bounds"]
assert lower <= upper
if reaction_record["source_direction"] == "left_to_right":
    assert lower >= 0
elif reaction_record["source_direction"] == "right_to_left":
    assert upper <= 0

stoichiometry = {}
resolved = []
for selected in mapping:
    participant = participants[selected["ordinal"]]
    assert selected["chemical_ref"] == participant["chemical_ref"]
    assert selected["source_accession"] == participant["source_accession"]
    metabolite = model.metabolites.get_by_id(selected["model_metabolite_id"])
    assert metabolite.compartment == selected["compartment"]
    coefficient = Fraction(participant["coefficient_expression"])
    assert coefficient > 0, "source coefficient must be an explicit positive constant"
    numeric = float(coefficient)
    assert 0 < numeric < float("inf"), "source coefficient must be finite"
    signed = -numeric if participant["side"] == "left" else numeric
    stoichiometry[metabolite] = stoichiometry.get(metabolite, 0.) + signed
    resolved.append({**selected, "source_side": participant["side"],
        "source_location": participant["source_location"],
        "coefficient_expression": participant["coefficient_expression"],
        "source_coefficient_text": participant["source_coefficient_text"],
        "coefficient_basis": participant["coefficient_basis"], "signed_coefficient": signed})
assert any(value < 0 for value in stoichiometry.values())
assert any(value > 0 for value in stoichiometry.values())
reaction = cobra.Reaction(request["reaction_id"], name=reaction_record["source_equation"],
    lower_bound=lower, upper_bound=upper)
reaction.annotation["rhea"] = reaction_record["accession"]
reaction.add_metabolites(stoichiometry)
model.add_reactions([reaction])
actual_stoichiometry = {met.id: coefficient for met, coefficient in reaction.metabolites.items()}
assert actual_stoichiometry == request["expected_stoichiometry"]
assert len(model.reactions) == len(before_model["reactions"]) + 1
assert model.objective.direction == "max"

output = Path(request["edited_model_file"])
assert not output.exists(), "a new selected model must not replace existing bytes"
cobra.io.save_json_model(model, output)
reopened = cobra.io.load_json_model(output)
assert model_to_dict(reopened) == model_to_dict(model)
assert reopened.objective.direction == "max"
assert {met.id: coefficient for met, coefficient in reopened.reactions.get_by_id(
    request["reaction_id"]).metabolites.items()} == request["expected_stoichiometry"]
assert file_pin(original) == before
_verify_software(software, native_loaded=True)
receipt = {"schema": "direct_cobra_reaction_addition_receipt_v1", "original_model": before,
    "edited_model": file_pin(output), "reaction_record_ref": request["reaction_record_ref"],
    "source_ref": reaction_record["source_ref"], "source_accession": reaction_record["accession"],
    "source_direction": reaction_record["source_direction"], "mapping_basis": request["mapping_basis"],
    "orientation_basis": request["orientation_basis"], "reaction_id": reaction.id,
    "bounds": list(reaction.bounds), "participant_mapping": resolved,
    "stoichiometry": actual_stoichiometry, "original_reaction_count": len(before_model["reactions"]),
    "edited_reaction_count": len(model.reactions), "optimization_calls": 0,
    "cobra_version": cobra.__version__, "objective_direction": reopened.objective.direction,
    "qualification": "supplied numerical control; source correspondence is caller-selected, not inferred"}
immutable_json(request["receipt_file"], receipt)
print(json.dumps(receipt, allow_nan=False))
'''


def _native_source(case):
    """Validate the supplied capture's exact source relationships, without lookup."""
    capture_file = Path(case["acquisition_file"])
    capture_pin = file_pin(capture_file)
    assert capture_pin["sha256"] == case["acquisition_sha256"]
    capture = read_json(capture_file)
    assert capture["schema"] == "rhea_live_reaction_acquisition_v1"
    records = [row for row in capture["reaction_records"] if row["id"] == case["reaction_record_ref"]]
    assert len(records) == 1, "select an exact acquired reaction_record, never a first match"
    retained = records[0]
    record = {key: value for key, value in retained.items() if key not in {"id", "record_type", "origin"}}
    validate_schema(record, RECORD_SCHEMAS["reaction_record"])
    assert record["source_ref"] == capture["source_record"]["id"]
    body = capture["native_body"]
    raw = Path(body["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == body["sha256"] and len(raw) == body["size_bytes"]
    assert body["artifact_ref"] == capture["source_record"]["artifact_ref"]
    native_rows = [row for row in rhea_response(raw)["results"]
        if accession(row["id"], "RHEA") == record["accession"]]
    assert len(native_rows) == 1
    parsed = rhea_row(native_rows[0])
    for field in ("accession", "source_equation", "source_arrow", "source_direction", "source_status",
                  "source_balanced", "source_transport", "source_comment"):
        assert record[field] == parsed[field]
    assert len(record["participants"]) == len(parsed["participants"])
    chemical_refs = {row["id"]: row for row in capture["chemical_references"]}
    for participant, native in zip(record["participants"], parsed["participants"], strict=True):
        assert {key: value for key, value in participant.items() if key != "chemical_ref"} == native
        chemical = chemical_refs[participant["chemical_ref"]]
        assert chemical["reference_type"] == "chemical" and chemical["source_ref"] == record["source_ref"]
        # Rhea can retain non-ChEBI participant identities too. Do not coerce them.
        assert chemical["accession"] == participant["source_accession"]
    references = [row for row in capture["reaction_references"] if row["native_record_ref"] == retained["id"]]
    assert len(references) == 1 and references[0]["accession"] == record["accession"]
    return capture_pin, record


def _selected_native(argv, *, lifecycle, software, environment=None):
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode.local_jobs import LocalJobPolicy
    lifecycle.mkdir(parents=True, exist_ok=False)
    env = environment or flux_balance_environment(software,
        attempt_directory=str(lifecycle / ATTEMPT_DIRECTORY_NAME), lifecycle_directory=str(lifecycle))
    handle = native_lifecycle.start_job(argv, cwd=lifecycle, policy=LocalJobPolicy(**POLICY),
        handle_path=lifecycle / "native.json", env=env)
    result = native_lifecycle.wait_job(handle)
    immutable_json(lifecycle / "selected-execution.json", {"returncode": result.returncode, "metadata": result.metadata})
    assert result.returncode == 0, result.metadata
    assert result.metadata["verified_cgroup"] == {"memory_max": 21474836480, "memory_swap_max": 0,
        "kill_mode": "control-group", "oom_policy": "kill"}
    return result


def test_selected_database_reaction_addition_and_serialized_fba(monkeypatch):
    selected_case = os.environ.get("HMMER_NATIVE_ORACLE_METABOLIC_ADDITION_CASE")
    selected_software = os.environ.get("HMMER_NATIVE_ORACLE_FBA716_SOFTWARE")
    if selected_case is None or selected_software is None:
        pytest.skip("requires an actual acquired reaction case and explicit prepared FBA software")
    case_file, software_file = Path(selected_case), Path(selected_software)
    assert case_file.is_absolute() and software_file.is_absolute()
    case_pin, software_pin = file_pin(case_file), file_pin(software_file)
    case = read_json(case_file)
    assert case["schema"] == "metabolic_reaction_addition_case_v1"
    assert case["mapping_basis"] == case["orientation_basis"] == "caller_selected_numerical_control"
    acquisition_pin, record = _native_source(case)
    software = validate_flux_balance_software(read_json(software_file))
    assert len(case["bounds"]) == 2 and all(type(value) in {int, float} and math.isfinite(value) for value in case["bounds"])
    assert case["bounds"][0] <= case["bounds"][1]
    assert set(case["expected"]) == {"baseline", "added", "clamped"}
    expected_stoichiometry = case["expected_stoichiometry"]
    assert expected_stoichiometry and all(type(value) in {int, float} and math.isfinite(value) for value in expected_stoichiometry.values())
    participants = {row["ordinal"]: row for row in record["participants"]}
    assert set(participants) == {row["ordinal"] for row in case["participant_mapping"]}
    for row in case["participant_mapping"]:
        coefficient = Fraction(participants[row["ordinal"]]["coefficient_expression"])
        assert coefficient > 0 and math.isfinite(float(coefficient)), "symbolic coefficients need explicit instantiation"

    root = ATTEMPT / "database-reaction-addition"
    root.mkdir(exist_ok=False)
    original = root / "original-control-model.json"
    raw_original = canonical(case["model"]).encode()
    immutable_bytes(original, raw_original)
    original_pin = file_pin(original)
    assert case["reaction_id"] not in {row["id"] for row in case["model"]["reactions"]}
    assert {row["id"]: row.get("objective_coefficient", 0)
        for row in case["model"]["reactions"] if row.get("objective_coefficient", 0) != 0} == {
            case["endpoint_reaction_id"]: 1}
    preparation = root / "selected-model-preparation"
    edited = preparation / "edited-control-model.json"
    request = {"software_file": str(software_file), "original_model_file": str(original),
        "original_model_pin": original_pin, "edited_model_file": str(edited),
        "receipt_file": str(preparation / "addition-receipt.json"), "reaction_record_ref": case["reaction_record_ref"],
        "reaction_record": record, "participant_mapping": case["participant_mapping"],
        "mapping_basis": case["mapping_basis"], "orientation_basis": case["orientation_basis"],
        "reaction_id": case["reaction_id"], "bounds": case["bounds"],
        "expected_stoichiometry": expected_stoichiometry}
    request_file = root / "selected-addition.json"
    immutable_json(request_file, request)
    _selected_native([software["python"]["path"], "-B", "-S", "-c", _EDIT_PROGRAM, str(request_file)],
        lifecycle=preparation, software=software)
    receipt = read_json(preparation / "addition-receipt.json")
    assert receipt["optimization_calls"] == 0 and receipt["cobra_version"] == "0.32.1"
    assert receipt["source_direction"] == record["source_direction"]
    assert receipt["participant_mapping"] and receipt["stoichiometry"] == expected_stoichiometry
    assert receipt["original_model"] == original_pin and file_pin(original) == original_pin
    raw_edited = edited.read_bytes()
    assert receipt["edited_model"] == file_pin(edited)
    assert raw_edited != raw_original
    edited_document = read_json(edited)
    added = [row for row in edited_document["reactions"] if row["id"] == case["reaction_id"]]
    assert len(added) == 1 and added[0]["metabolites"] == expected_stoichiometry
    assert added[0]["annotation"]["rhea"] == record["accession"]

    summaries = []
    for name, raw, changes in (
        ("baseline", raw_original, None), ("added", raw_edited, None),
        ("clamped", raw_edited, [{"reaction_id": case["reaction_id"],
            "lower": _selected_bound(0), "upper": _selected_bound(0)}]),
    ):
        folder = root / name
        plan = _plan(folder, "cobra_json", raw, software=software, changes=changes,
            operation_key="selected-database-addition-" + name)
        immutable_json(folder / "selected-plan.json", plan)
        lifecycle = Path(plan["identity"]["execution_id"]).parent
        lifecycle.mkdir(parents=True, exist_ok=False)
        immutable_json(lifecycle / RUN_PLAN_FILENAME, plan)
        # The explicit native handle already has its selected working directory.
        from gene_annotation_episode import native_lifecycle
        from gene_annotation_episode.local_jobs import LocalJobPolicy
        handle = native_lifecycle.start_job(flux_balance_driver_argv(plan), cwd=lifecycle,
            policy=LocalJobPolicy(**POLICY), handle_path=plan["identity"]["execution_id"],
            env=plan["requested_job"]["environment"])
        execution = native_lifecycle.wait_job(handle)
        immutable_json(folder / "native-execution.json", {"returncode": execution.returncode, "metadata": execution.metadata})
        assert execution.returncode == 0, execution.metadata
        assert execution.metadata["verified_cgroup"] == {"memory_max": 21474836480, "memory_swap_max": 0,
            "kill_mode": "control-group", "oom_policy": "kill"}
        manifest = read_json(Path(plan["attempt_directory"]) / "outputs/native-manifest.json")
        immutable_json(folder / "selected-result.json", manifest)
        assert manifest["solve_call_count"] == 1 and manifest["execution_outcome"] == "completed", manifest["issues"]
        assert manifest["request_realization"] == "exact"
        assert (Path(plan["attempt_directory"]) / "outputs/original-model.json").read_bytes() == raw
        sheet, calculated = _parsed_calculated(plan)
        immutable_json(folder / "parsed-sheet.json", sheet)
        immutable_json(folder / "calculated.json", calculated)
        observed = {row["reaction_id"]: row["flux"]["value"] for row in sheet["native_solution"]["native"]["reaction_values"]}
        assert observed == case["expected"][name]["fluxes"]
        assert calculated["objective"]["full_calculated"]["value"] == case["expected"][name]["objective"]
        assert calculated["candidate_feasibility"] == "passes_recorded_checks"
        assert observed[case["endpoint_reaction_id"]] == case["expected"][name]["objective"]
        if name != "baseline":
            for phase in ("loaded_original", "effective"):
                model = sheet["models"][phase]
                reaction = next(row for row in model["reactions"] if row["id"] == case["reaction_id"])
                metabolites = {row["position"]: row["id"] for row in model["metabolites"]}
                stoichiometry = {metabolites[row["metabolite_position"]]: row["coefficient"]["value"]
                    for row in model["stoichiometry"] if row["reaction_position"] == reaction["position"]}
                assert stoichiometry == expected_stoichiometry
            effective = next(row for row in sheet["models"]["effective"]["reactions"] if row["id"] == case["reaction_id"])
            assert [effective["lower"]["value"], effective["upper"]["value"]] == ([0, 0] if name == "clamped" else case["bounds"])
        # Recalculate an actually retained sheet without any new optimizer call.
        from gene_annotation_episode.flux_balance_calculations import calculate_flux_balance_sheet
        saved = read_json(folder / "parsed-sheet.json")
        def forbidden(*args, **kwargs):
            raise AssertionError("saved-sheet calculation attempted file access or another native job")
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "open", forbidden)
            patch.setattr(io, "open", forbidden)
            patch.setattr(native_lifecycle, "start_job", forbidden)
            assert calculate_flux_balance_sheet(saved, parameters=deepcopy(calculated["parameters"])) == calculated
        summaries.append({"case": name, "objective": calculated["objective"], "fluxes": observed,
            "sheet_sha256": calculated["sheet_sha256"], "original_model_sha256": plan["requested_job"]["native_flux_balance"]["model_input"]["file"]["sha256"],
            "native_solve_calls": manifest["solve_call_count"]})
    assert case["expected"]["baseline"]["objective"] == case["expected"]["clamped"]["objective"] == 0
    assert case["expected"]["added"]["objective"] > 0
    assert file_pin(original) == original_pin and file_pin(edited) == receipt["edited_model"]
    assert file_pin(case_file) == case_pin and file_pin(software_file) == software_pin
    assert file_pin(Path(case["acquisition_file"])) == acquisition_pin
    immutable_json(root / "verified-addition.json", {"schema": "direct_database_reaction_addition_verification_v1",
        "case_file": case_pin, "acquisition_file": acquisition_pin, "software_file": software_pin,
        "addition_receipt": receipt, "cases": summaries,
        "qualification": "supplied numerical control; conditional model consequences, no annotation verdict or whole episode claim"})
