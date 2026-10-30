"""Controlled stored values, not original producing-attempt custody.

Exact234/239 controls are opt-in retained supplied data. No native call, fit or
historical numerical migration is performed by the original selection tests.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import molecular_sequence_result_contracts as contracts
from gene_annotation_episode import molecular_sequence_result_worker as worker
from gene_annotation_episode.execution_contracts import canonical, digest
from tests.test_molecular_sequence_execution import software_fixture, _environment


ROOT = Path(__file__).resolve().parents[1]
POLICY = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}


def file_identity(path):
    raw = Path(path).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + sha, sha256=sha, size_bytes=len(raw), format="json")


def source(path):
    identity = file_identity(path)
    return dict(state="retained", file=identity, declared={"relative_path": Path(path).name, "format": "json", "state": "present",
        "sha256": identity["sha256"], "size_bytes": identity["size_bytes"]},
        observed_identity={k: identity[k] for k in ("sha256", "size_bytes")}, failure=None)


def selector(operation, *, mode="original_attempt", saved=None, row=None, fields=None, files=()):
    row = {"kind": "summary"} if row is None else row
    fields = [next(iter(contracts.field_table(operation, row)))] if fields is None else fields
    return dict(version=contracts.SELECTOR_VERSION, mode=mode, operation=operation, saved_sheet_ref=saved,
        rows=[{"row_id": row, "fields": fields}], return_files=list(files))


def engineered(tmp_path, *, operation=contracts.OPERATIONS[0]):
    """Explicit literal cells; no native result/provenance is being simulated."""
    sheet = {"schema": contracts.SCHEMAS[operation][0]}
    components = {"schema": contracts.SCHEMAS[operation][1][-1], "summary": {}, "status": "partial", "native_outcome": "partial"}
    if operation == contracts.OPERATIONS[0]:
        components["summary"] = dict(input_length_nt=12, reported_row_count=3, usable_saved_row_count=2,
            retained_length_sum_nt=18, retained_length_denominator_rows=2, mean_retained_orf_length_nt=9.0)
        components["rows"] = [{"row_index": 0, "interval_length_nt": 9, "nucleotide_symbol_count": 9,
            "protein_symbol_count": 2, "source_definition": "compatible", "translation": {"state": "compatible", "early_ambiguity_termination": False}}]
    elif operation == contracts.OPERATIONS[1]:
        components["summary"] = dict(target_length_symbols=8, native_group_count=2, known_native_hit_list_count=1,
            mismatch_count_sum=0, mismatch_count_denominator_hits=0)
        components["groups"] = [{"hits": [{"target_interval": [1, 4], "mismatch_count": 0, "interpretation": "canonical_dna_window",
            "source_acceptance": "incompatible", "mismatch_list_matches_full_operands": False,
            "mismatch_fraction": {"numerator": 0, "denominator": 3, "value": 0.0}}]}]
    elif operation in contracts.OPERATIONS[2:4]:
        components["summary"] = dict(original_symbol_count=3, native_log_complete=True, native_report_complete=True, scan_exhaustiveness_verified=False)
        components["parameters"] = {"compatible": True}
        components["rows"] = [{"row_ordinal": 0, "native_values": {"position_1based": 1, "st_fraction": .667}, "source_compatible": True,
            "cells": {"processed_interval": [0, 1], "printed_symbols_match_operand": True, "st_count": 2, "window_denominator_symbols": 3,
                "calculated_st_fraction": 2/3, "source_rounded_st_fraction": .667}}]
    else:
        components.update(population={"time_point_count": 10, "complete_supplied_curve_population": True, "negative_substrate_ordinals": []},
            fit_components={"state": "qualified", "qualifications": ["native_source_returned_error_string"],
                "complete_population_eligible": True, "vmax": {"value": 12., "unit": "RFU/s", "unit_state": "declared_or_derived", "state": "present", "reason": None},
                "km": {"value": 3., "unit": "uM", "unit_state": "declared_or_derived", "state": "present", "reason": None},
                "covariance": [[1., .2], [.3, 2.]], "covariance_state": "qualified", "covariance_reason": None,
                "covariance_assessment": {"native_symmetry": "asymmetric", "symmetric_part_positive_semidefinite": True, "statistical_covariance_validity": "unestablished"}},
            native_return={"outcome": "source_error"}, physical_components={"kcat": {"value": None, "unit": "s^-1", "unit_state": "declared_or_derived", "state": "unavailable", "reason": "active_site_concentration_basis_unestablished", "uncertainty": {"state": "unavailable", "reason": "not_supplied_or_estimated"}}})
    paths = {}
    for role, value in (("sheet", sheet), ("components", components)):
        path = tmp_path / (role + ".json"); path.write_text(json.dumps(value)); paths[role] = path
    sources = {role: source(paths[role]) if role in paths else contracts.empty_file_state() for role in contracts.FILE_ROLES}
    return sheet, components, sources, paths


def project(selection, sheet, components, sources):
    return contracts.select_stored_molecular_sequence_values(operation=selection["operation"], sheet=sheet, components=components,
        selection=selection, source_files=sources, association={"state": "unavailable", "reason": "scientific_binding_unavailable", "proof_file": None, "original_identity": None})


@pytest.mark.parametrize("operation", contracts.OPERATIONS)
def test_five_profiles_have_closed_semantic_rows_without_control_fields(tmp_path, operation):
    sheet, components, sources, _ = engineered(tmp_path, operation=operation)
    selected = selector(operation)
    value = project(selected, sheet, components, sources)
    contracts.validate_molecular_sequence_projection(value)
    definitions = contracts.molecular_sequence_fact_sources()
    Draft202012Validator(definitions[contracts.PROJECTION_SOURCE]["report_schema"]).validate([value["public"]])
    forbidden = {"sha256", "size_bytes", "original_identity", "proof_file", "selected_payload_sha256", "path", "directory", "request_sha256"}
    def check(item):
        if type(item) is dict:
            assert not forbidden.intersection(item)
            for child in item.values(): check(child)
        elif type(item) is list:
            for child in item: check(child)
    check(value["public"])
    invalid = deepcopy(selected); invalid["original_payload_sha256"] = "0"*64
    with pytest.raises(ValueError): contracts.validate_molecular_sequence_result_selector(invalid)
    bad_fact = deepcopy(value["public"]); bad_fact["sha256"] = "0"*64
    with pytest.raises(ValueError): contracts.validate_molecular_sequence_fact_values(contracts.PROJECTION_SOURCE, [bad_fact])


def test_original_zero_null_missing_and_boolean_are_distinct(tmp_path):
    sheet, components, sources, _ = engineered(tmp_path)
    components["summary"].update(reported_row_count=0, retained_length_sum_nt=None)
    del components["summary"]["mean_retained_orf_length_nt"]
    selected = selector(contracts.OPERATIONS[0], fields=["reported_row_count", "retained_length_sum_nt", "mean_retained_orf_length_nt"])
    rows = project(selected, sheet, components, sources)["public"]["rows"]
    assert [(row["value_state"], row["value"]) for row in rows] == [("stored_value", 0), ("stored_null", None), ("path_missing", None)]
    components["summary"]["reported_row_count"] = False
    assert project(selected, sheet, components, sources)["public"]["rows"][0]["value_state"] == "invalid_type"


def test_mean_and_placement_denominators_are_stored_not_recomputed(tmp_path):
    sheet, components, sources, _ = engineered(tmp_path)
    components["summary"]["mean_retained_orf_length_nt"] = 901.25
    value = project(selector(contracts.OPERATIONS[0], fields=["mean_retained_orf_length_nt"]), sheet, components, sources)
    row, = value["public"]["rows"]
    assert row["value"] == 901.25
    assert [(r["kind"], r["value"], r["unit"]) for r in row["denominators"]] == [("numerator", 18, "nt_symbols"), ("denominator", 2, "rows")]
    assert row["scientific_qualifiers"]["states"]["reported_row_count"]["value"] == 3
    assert row["scientific_qualifiers"]["states"]["usable_saved_row_count"]["value"] == 2


@pytest.mark.parametrize("interval,expected_state", [([5, 2], "invalid_type"), ([5, 5], "stored_value"), ([2, 5], "stored_value")])
def test_interval_order_is_structural_without_rewriting_source(tmp_path, interval, expected_state):
    sheet, components, sources, paths = engineered(tmp_path)
    components["rows"][0]["interval"] = interval
    paths["components"].write_text(canonical(components))
    raw = paths["components"].read_bytes(); sources["components"] = source(paths["components"])
    selected = selector(contracts.OPERATIONS[0], row={"kind": "orf", "row_index": 0}, fields=["interval"])
    value = project(selected, sheet, components, sources)
    row, = value["public"]["rows"]
    assert row["value_state"] == expected_state
    assert row["value"] == (interval if expected_state == "stored_value" else None)
    assert paths["components"].read_bytes() == raw and components["rows"][0]["interval"] == interval


@pytest.mark.parametrize("failed_role", ["sheet", "components"])
def test_independent_retention_failure_does_not_erase_other_source(tmp_path, failed_role):
    sheet, components, sources, _ = engineered(tmp_path)
    sources[failed_role] = contracts.empty_file_state("retention_failed", issue=contracts.failure("retention_failed", "capture", role=failed_role))
    value = project(selector(contracts.OPERATIONS[0]), sheet, components, sources)["public"]
    row, = value["rows"]
    assert value["source_states"][failed_role] == "retention_failed"
    if failed_role == "sheet": assert row["value"] == 12 and row["source_ref"] == sources["components"]["file"]["artifact_ref"]
    else: assert row["value_state"] == "source_unavailable" and row["source_ref"] is None and value["source_sheet_ref"] is not None


def test_glyco_qualifiers_do_not_turn_source_rule_into_occupancy(tmp_path):
    operation = contracts.OPERATIONS[3]
    sheet, components, sources, _ = engineered(tmp_path, operation=operation)
    selected = selector(operation, row={"kind": "glycosylation_site", "row_ordinal": 0},
        fields=["native_st_fraction", "calculated_st_fraction", "source_rounded_st_fraction"])
    values = project(selected, sheet, components, sources)["public"]
    assert [row["value"] for row in values["rows"]] == [.667, 2/3, .667]
    assert all(row["scientific_qualifiers"]["states"]["scan_exhaustiveness_verified"]["value"] is False for row in values["rows"])
    assert all("not_occupancy" in row["scientific_qualifiers"]["interpretation"] for row in values["rows"])


def test_native_source_error_and_raw_matrix_qualification_remain_scientific_states(tmp_path):
    operation = contracts.OPERATIONS[4]
    sheet, components, sources, _ = engineered(tmp_path, operation=operation)
    selected = selector(operation, row={"kind": "protease_covariance", "parameter_i": 1, "parameter_j": 0}, fields=["reported_matrix_entry"])
    row, = project(selected, sheet, components, sources)["public"]["rows"]
    assert row["value"] == .3
    qualifiers = row["scientific_qualifiers"]["states"]
    assert qualifiers["native_return_outcome"]["value"] == "source_error"
    assert qualifiers["native_matrix_symmetry"]["value"] == "asymmetric"
    assert qualifiers["statistical_covariance_validity"]["value"] == "unestablished"
    selected = selector(operation, row={"kind": "protease_quantity", "quantity": "kcat"}, fields=["value"])
    row, = project(selected, sheet, components, sources)["public"]["rows"]
    assert row["value_state"] == "stored_null"
    assert row["scientific_qualifiers"]["states"]["quantity_reason"]["value"] == "active_site_concentration_basis_unestablished"


def worker_plan(tmp_path, selection, sources, paths, *, software=None):
    receipt = None
    if selection["mode"] == contracts.MODES[1]:
        receipt_path = tmp_path / "controlled-received-sheet.json"
        receipt_path.write_text(canonical({"version": "molecular_sequence_received_sheet_v1", "engineering_fixture_not_custody": True,
            "file": sources["sheet"]["file"]}))
        receipt = {**file_identity(receipt_path), "format": "molecular_sequence_received_sheet_v1"}
    return dict(version=contracts.PLAN_VERSION, directory=str(tmp_path / "worker-output"), selector=selection, source_files=sources,
        inputs=[dict(role=role, file=sources[role]["file"], path=str(path)) for role, path in paths.items() if sources[role]["file"] is not None],
        association={"state": "unavailable", "reason": "scientific_binding_unavailable", "proof_file": None, "original_identity": None},
        received_sheet_receipt_file=receipt, software=software, selected_environment={} if software is None else _environment(software), policy=POLICY)


def run_worker(tmp_path, plan):
    path = tmp_path / "worker-plan.json"; path.write_text(canonical(plan) + "\n")
    raw = path.read_bytes()
    return worker.run_molecular_sequence_result_worker(plan_file={"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}, output_directory=plan["directory"])


@pytest.mark.parametrize("profile,expected,expected_components", [(0, "888ebdc6ba3e229b7b224c41b78e1fc38ecb2a0ce594127501175ee7fba751ea", "11becb439f1e9f2becd7e69ae41630b357a5d9a479c2de51186a91431503200c"),
    (1, "436ba7e78ac0821f8e7ed8d939c3e392880ce39a33ef73a23465cd3da3881f1f", "b51bbaae7a80f9238a7735b777031f34413f28dc3dd92a54852da1c56e473442"),
    (2, "9b11ec1f0e9d2808807f67eb07a52a5a0f9b8765651bef4e51f26d2799739730", "1c8e4031b3569ce21bb80adabf6a0c93c57a31ea229db68bef2dc0c30fca9b3e"),
    (3, "e996ce8d00492baa5effc52199cac3085ca76e5d971db9b6ad83f69f93a2e0db", "6d7a1d77bf218b576978f6c8c3f49bc7fd1b5771283649c0b8d59723fb94fb95")])
def test_exact234_original_stored_cells_need_no_calculator_or_source(tmp_path, monkeypatch, profile, expected, expected_components):
    selected = os.environ.get("HMMER_NATIVE_ORACLE_MOLECULAR_RETAINED234")
    if selected is None: pytest.skip("requires root-selected retained234 supplied outputs")
    directory = Path(selected) / ("test_genuine_selected_driver_j" + str(profile)) / "output"
    sheet_path, component_path = directory / "sheet.json", directory / "components.json"
    assert hashlib.sha256(sheet_path.read_bytes()).hexdigest() == expected
    assert hashlib.sha256(component_path.read_bytes()).hexdigest() == expected_components
    from gene_annotation_episode import molecular_sequence_driver, molecular_sequence_native
    monkeypatch.setattr(molecular_sequence_driver, "_calculate", lambda *args: pytest.fail("original path calculated"))
    monkeypatch.setattr(molecular_sequence_native, "execute_molecular_sequence_request", lambda *args: pytest.fail("original path called source"))
    sources = {role: contracts.empty_file_state() for role in contracts.FILE_ROLES}
    sources.update(sheet=source(sheet_path), components=source(component_path))
    selected = selector(contracts.OPERATIONS[profile])
    plan = worker_plan(tmp_path, selected, sources, {"sheet": sheet_path, "components": component_path})
    result = run_worker(tmp_path, plan)
    assert result["failures"] == []
    projection = json.loads((Path(plan["directory"]) / "projection.json").read_bytes())
    assert projection["public"]["original_attempt_association"] == "unavailable"
    assert projection["public"]["rows"][0]["value_state"] == "stored_value"


def retained239():
    selected = os.environ.get("HMMER_NATIVE_ORACLE_PROTEASE_RETAINED_OUTPUT")
    if selected is None: pytest.skip("requires root-selected exact retained239 sheet and original v1 components")
    directory = Path(selected)
    assert hashlib.sha256((directory / "sheet.json").read_bytes()).hexdigest() == "5ce86df48853601e7d05472f30fcfef148116ad9031f5c4035d5f10f114a5765"
    assert hashlib.sha256((directory / "components.json").read_bytes()).hexdigest() == "5bdacd46a9105c07e9d855ce993332e4a8eef2838dbd7f2526036db916f589c4"
    return directory


def test_exact239_original_v1_and_missing_legacy_assessment_are_never_migrated(tmp_path, monkeypatch):
    directory = retained239()
    sources = {role: contracts.empty_file_state() for role in contracts.FILE_ROLES}
    sources.update(sheet=source(directory / "sheet.json"), components=source(directory / "components.json"))
    selected = selector(contracts.OPERATIONS[4], row={"kind": "protease_quantity", "quantity": "apparent_catalytic_efficiency"}, fields=["value", "variance"])
    from gene_annotation_episode import molecular_sequence_driver, molecular_sequence_native
    monkeypatch.setattr(molecular_sequence_driver, "_calculate", lambda *args: pytest.fail("original239 recalculated"))
    monkeypatch.setattr(molecular_sequence_native, "execute_molecular_sequence_request", lambda *args: pytest.fail("source invoked"))
    raw = (directory / "components.json").read_bytes()
    plan = worker_plan(tmp_path, selected, sources, {role: directory / (role + ".json") for role in ("sheet", "components")})
    run_worker(tmp_path, plan)
    projection = json.loads((Path(plan["directory"]) / "projection.json").read_bytes())["public"]
    assert projection["components_schema"] == "protease_kinetics_components_v1"
    assert projection["rows"][1]["value_state"] == "path_missing"
    assert projection["rows"][0]["scientific_qualifiers"]["states"]["quantity_uncertainty_reason"]["value"] == "native_covariance_asymmetric"
    assert projection["rows"][0]["scientific_qualifiers"]["states"]["native_matrix_symmetry"]["value_state"] == "path_missing"
    assert (directory / "components.json").read_bytes() == raw


def test_explicit_saved239_calculates_current_v2_exactly_once_and_replays_without_inputs(tmp_path, monkeypatch):
    directory = retained239()
    sheet = tmp_path / "received-sheet.json"; sheet.write_bytes((directory / "sheet.json").read_bytes())
    sources = {role: contracts.empty_file_state() for role in contracts.FILE_ROLES}; sources["sheet"] = source(sheet)
    selected = selector(contracts.OPERATIONS[4], mode=contracts.MODES[1], saved=sources["sheet"]["file"]["artifact_ref"],
        row={"kind": "protease_quantity", "quantity": "apparent_catalytic_efficiency"}, fields=["value", "variance"])
    software = software_fixture(tmp_path / "selected-worker-software")
    plan = worker_plan(tmp_path, selected, sources, {"sheet": sheet}, software=software)
    path = tmp_path / "worker-plan.json"; path.write_text(canonical(plan) + "\n")
    raw = path.read_bytes()
    completed = subprocess.run([software["python"]["path"], "-B", "-m", "gene_annotation_episode.molecular_sequence_result_worker",
        "--plan-file", str(path), "--sha256", hashlib.sha256(raw).hexdigest(), "--size-bytes", str(len(raw)),
        "--output-directory", plan["directory"]], cwd=tmp_path, env=_environment(software),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (tmp_path / "worker.stdout").write_bytes(completed.stdout); (tmp_path / "worker.stderr").write_bytes(completed.stderr)
    assert completed.returncode == 0, completed.stderr.decode()
    result = json.loads((Path(plan["directory"]) / "result.json").read_bytes())
    diagnostics = json.loads((Path(plan["directory"]) / "diagnostics.json").read_bytes())
    assert diagnostics["calculation_call_count"] == 1 and diagnostics["native_invocation"] == "not_requested"
    assert diagnostics["software_before"]["state"] == diagnostics["software_after"]["state"] == "verified"
    components = json.loads((Path(plan["directory"]) / "calculated_components.json").read_bytes())
    assert components["schema"] == "protease_kinetics_components_v2"
    assert components["physical_components"]["apparent_catalytic_efficiency"]["uncertainty"]["variance"] == 0.0006287504487556328
    draft = json.loads((Path(plan["directory"]) / "projection.json").read_bytes())
    assert draft["public"]["source_states"]["components"] == "produced_unretained"
    with pytest.raises(ValueError): contracts.validate_molecular_sequence_fact_values(contracts.PROJECTION_SOURCE, [draft["public"]])
    sheet.unlink()
    Path(software["software_files_file"]["path"]).unlink()
    Path(software["python"]["path"]).unlink()
    monkeypatch.setattr(worker, "_calculate", lambda *args: pytest.fail("sealed replay recalculated"))
    assert run_worker(tmp_path, plan) == result


def test_saved_calculation_failure_keeps_received_sheet_and_distinguishes_absent_component(tmp_path, monkeypatch):
    sheet, components, sources, paths = engineered(tmp_path)
    sources["components"] = contracts.empty_file_state(); paths.pop("components")
    selected = selector(contracts.OPERATIONS[0], mode=contracts.MODES[1], saved=sources["sheet"]["file"]["artifact_ref"])
    monkeypatch.setattr(worker, "_calculate", lambda *args: (_ for _ in ()).throw(ValueError("controlled_calculation_failure")))
    plan = worker_plan(tmp_path, selected, sources, paths)
    result = run_worker(tmp_path, plan)
    assert [f["code"] for f in result["failures"]] == ["calculation_failed"]
    assert next(row["declaration"] for row in result["outputs"] if row["role"] == "calculated_components")["state"] == "absent"
    assert sources["sheet"]["file"] == file_identity(paths["sheet"])


def supplied_sheet_and_selection():
    from tests.test_calibrated_signal_inputs import sheet
    value = sheet()
    # An explicit engineering selection, not a production default population.
    selected = dict(version="calibrated_signal_selection_v1",
        sample_ids=[row["sample_id"] for row in value["samples"]],
        species_ids=[row["species_id"] for row in value["species"]],
        calibration_ids=[row["calibration_id"] for row in value["calibrations"]])
    return value, selected


def supplied_selector(reference, *, namespace="artifact", action="calculate", stored=None):
    _sheet, selected = supplied_sheet_and_selection()
    return dict(version=contracts.SUPPLIED_SELECTOR_VERSION, operation=contracts.SUPPLIED_OPERATION,
        mode="supplied_measurements", action=action,
        input=dict(reference=reference, namespace=namespace) if action == "calculate" else None,
        stored=stored, calculation_selection=selected if action == "calculate" else None,
        return_files=["sheet", "components"])


def supplied_worker_plan(tmp_path, *, software=None):
    """Byte-bound protocol fixture; host authority is tested in owner cases."""
    sheet, _selection = supplied_sheet_and_selection()
    path = tmp_path / "input.json"; path.write_text(json.dumps(sheet, indent=3) + "\n")
    evidence = tmp_path / "engineering-input-evidence.json"
    evidence.write_text('{"version":"molecular_sequence_supplied_input_evidence_v1","engineering_protocol_only":true}')
    return dict(version=contracts.SUPPLIED_PLAN_VERSION, directory=str(tmp_path / "supplied-worker"),
        selector=supplied_selector(file_identity(path)["artifact_ref"]), input_file=file_identity(path), input_path=str(path),
        input_evidence_file={**file_identity(evidence), "format": "molecular_sequence_supplied_input_evidence_v1"},
        software=software, selected_environment={} if software is None else _environment(software), policy=POLICY)


@pytest.mark.parametrize("change", ["native", "extra", "missing_selection", "fake_handoff", "unselected_stored"])
def test_supplied_selector_is_explicit_and_does_not_widen_legacy_profiles(change):
    value = supplied_selector("artifact_" + "1"*64)
    if change == "native": value["mode"] = "native"
    elif change == "extra": value["findings"] = {"invented": 1}
    elif change == "missing_selection": value["calculation_selection"] = None
    elif change == "fake_handoff": value["handoff_ref"] = "source_fake"
    else: value["stored"] = {"sheet": None, "components": None}
    with pytest.raises(ValueError): contracts.validate_molecular_sequence_supplied_selector(value)
    assert contracts.OPERATIONS == ("annotate_open_reading_frames", "align_sequences", "find_n_glycosylation_motifs",
        "predict_o_glycosylation_hotspots", "analyze_protease_kinetics")
    assert contracts.molecular_sequence_fact_sources()[contracts.SAVED_SOURCE]["report_schema"]["items"]["properties"]["operation"]["enum"] == list(contracts.OPERATIONS)


def test_supplied_worker_calls_existing_authority_once_and_replays_without_historical_input(tmp_path, monkeypatch):
    from gene_annotation_episode import calibrated_signal_calculations as calculations
    plan = supplied_worker_plan(tmp_path)
    original_bytes = Path(plan["input_path"]).read_bytes()
    calls, authority = [], calculations.calculate_calibrated_signal_components
    def count(sheet, *, selection):
        calls.append(deepcopy(selection)); return authority(sheet, selection=selection)
    monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", count)
    result = run_worker(tmp_path, plan)
    root = Path(plan["directory"])
    assert len(calls) == 1 and result["failures"] == []
    assert (root / "sheet.json").read_bytes() == original_bytes
    components = json.loads((root / "calculated_components.json").read_bytes())
    assert components["version"] == "calibrated_signal_components_v1"
    assert components["sheet"] == json.loads(original_bytes) and components["selection"] == calls[0]
    assert components["population"]["association_species_ids"] == components["sheet"]["association"]["analysis_species_ids"]
    assert "exact_value" in components["rows"][0]["linear_estimate"]
    diagnostic = json.loads((root / "diagnostics.json").read_bytes())
    assert diagnostic["calculation_call_count"] == 1 and diagnostic["native_invocation"] == "not_requested"
    Path(plan["input_path"]).unlink()
    monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", lambda *args, **kwargs: pytest.fail("sealed supplied replay calculated"))
    assert run_worker(tmp_path, plan) == result


def test_supplied_worker_unsealed_after_actual_call_never_recalculates_or_infers_completion(tmp_path, monkeypatch):
    from gene_annotation_episode import calibrated_signal_calculations as calculations
    plan = supplied_worker_plan(tmp_path)
    calls, authority, write = [], calculations.calculate_calibrated_signal_components, worker._write
    def count(sheet, *, selection):
        calls.append(1); return authority(sheet, selection=selection)
    def crash(path, value):
        if Path(path).name == "diagnostics.json": raise OSError("engineering_post_call_worker_death")
        return write(path, value)
    monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", count)
    monkeypatch.setattr(worker, "_write", crash)
    with pytest.raises(OSError): run_worker(tmp_path, plan)
    assert calls == [1] and not (Path(plan["directory"]) / "result.json").exists()
    assert (Path(plan["directory"]) / "calculated_components.json").is_file()
    with pytest.raises(ValueError, match="worker_uncertain"): run_worker(tmp_path, plan)
    assert calls == [1]


def test_supplied_file_and_failure_forms_use_ordinary_grammar_without_rich_numeric_registration():
    from gene_annotation_episode.communication import validate_closed_schema
    definitions = contracts.supplied_file_fact_sources()
    schema = dict(type="object", properties={"files": definitions[contracts.SAVED_SOURCE]["report_schema"],
        "failures": definitions[contracts.FAILURE_SOURCE]["report_schema"]}, required=["files", "failures"], additionalProperties=False)
    assert validate_closed_schema(schema) == schema
    assert contracts.PROJECTION_SOURCE not in definitions


def test_supplied_public_failure_location_preserves_exact_private_pointer_and_source_identity():
    mapping = {"": "document_root", "/sheet": "embedded_sheet", "/selection": "calculation_selection",
        "/samples": "samples", "/species": "species", "/calibrations": "calibrations", "/association": "association", None: None}
    reference = "artifact_" + "1"*64
    for pointer, location in mapping.items():
        private = contracts.supplied_failure("schema_invalid", "load", role="components", source_ref=reference, source_pointer=pointer)
        public = contracts.supplied_failure_view(private)
        assert private["source_pointer"] == pointer and public["source_location"] == location
        assert "source_pointer" not in public and public["source_ref"] == reference
        assert all(public[name] == private[name] for name in ("operation", "code", "stage", "role", "source_ref"))
        contracts.validate_molecular_sequence_fact_values(contracts.FAILURE_SOURCE, [public])
        with pytest.raises(ValueError): contracts.validate_molecular_sequence_fact_values(contracts.FAILURE_SOURCE, [private])
    with pytest.raises(ValueError): contracts.supplied_failure("schema_invalid", "load", source_pointer="/not-mapped")


def test_supplied_failure_versions_do_not_widen_legacy_worker_or_projection_containers(tmp_path):
    private = contracts.supplied_failure("schema_invalid", "load", role="sheet", source_pointer="/sheet")
    public = contracts.supplied_failure_view(private)
    sheet, components, sources, _paths = engineered(tmp_path)
    selected = selector(contracts.OPERATIONS[0])
    original_projection = project(selected, sheet, components, sources)["public"]
    def outputs(roles):
        return [dict(role=role, declaration=dict(relative_path=role + ".json", format="json", state="absent", sha256=None, size_bytes=None)) for role in roles]
    for issue in (private, public):
        legacy_result = dict(version=contracts.RESULT_VERSION, plan_sha256="0"*64, selector=selected,
            outputs=outputs(contracts.OUTPUTS), failures=[issue])
        with pytest.raises(ValueError): contracts.validate_molecular_sequence_result_worker_result(legacy_result)
        projection = deepcopy(original_projection); projection["failures"] = [issue]
        with pytest.raises(ValueError): contracts.validate_molecular_sequence_fact_values(contracts.PROJECTION_SOURCE, [projection])
    supplied_result = dict(version=contracts.SUPPLIED_RESULT_VERSION, plan_sha256="0"*64,
        selector=supplied_selector("artifact_" + "1"*64), outputs=outputs(contracts.SUPPLIED_OUTPUTS), failures=[private])
    assert contracts.validate_supplied_worker_result(supplied_result)["failures"] == [private]
    contracts.validate_molecular_sequence_fact_values(contracts.FAILURE_SOURCE, [public])
    _sheet, selection = supplied_sheet_and_selection()
    record = dict(version=contracts.CALCULATION_RECORD_VERSION, operation=contracts.SUPPLIED_OPERATION,
        kind="selected_supplied_calculation", input_evidence_files={}, input_sheet_file=None, selection=selection,
        software=None, selected_environment={}, policy=POLICY, worker_plan_file=None, worker_result_file=None,
        worker_diagnostics_file=None, source_files={role: contracts.empty_file_state("not_requested") for role in contracts.FILE_ROLES},
        worker_outputs={role: contracts.empty_file_state("not_requested") for role in ("sheet", "components")},
        calculation_state="input_unavailable", calculation_call_count=0, origin_state="selected_action_only", linkage_state="not_assessed",
        validation_states={role: "unavailable" for role in ("sheet", "components")}, native_invocation="not_requested",
        acquired_population=None, failures=[private])
    assert contracts.validate_molecular_sequence_calculation_record(record)["failures"] == [private]
    record["failures"] = [public]
    with pytest.raises(ValueError): contracts.validate_molecular_sequence_calculation_record(record)
