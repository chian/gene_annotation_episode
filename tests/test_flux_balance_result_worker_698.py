"""Finite worker checks on retained688 bytes; mutations are synthetic only.

No solve, acquisition, installation or episode-authority claim is made here.
"""
from copy import deepcopy
import builtins
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode import flux_balance_result_worker as worker
from gene_annotation_episode.flux_balance_worker_contracts import (
    build_native_flux_balance_worker_plan, build_saved_flux_balance_worker_plan,
    validate_flux_balance_worker_plan, validate_flux_balance_worker_result,
)
from gene_annotation_episode.flux_balance_readers import parse_fba_capture
from gene_annotation_episode.flux_balance_sheet import populate_flux_balance_sheet
from gene_annotation_episode.flux_balance_calculations import calculate_flux_balance_sheet
from gene_annotation_episode.flux_balance_result_views import project_fba_result
from gene_annotation_episode.native_flux_balance_capture import capture_flux_balance_native_files
from gene_annotation_episode.native_flux_balance_contracts import bind_flux_balance_environment
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.state import Store

ROOT = Path(__file__).resolve().parents[1]
EMISSIONS = ROOT / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions"
BASE = ROOT / "verification/tool_graders_flux_balance_core_2026-10-29_679/VERIFIED_NUMERICAL_EXAMPLE_001.json"
pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "retained") as value:
        yield value


def retained(store, data, format_):
    ref = store.artifact(data, "application/octet-stream")
    file = {"artifact_ref": ref, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), "format": format_}
    return {"file": file, "path": str(retained_native_file(store, file))}


def record(store, data, format_):
    return retained(store, (canonical(data) + "\n").encode(), format_)


def capture(store, profile="sbml"):
    plan = json.loads((EMISSIONS / profile / "selected-plan.json").read_text())
    # Metadata fixtures satisfy capture's metadata lookup only; they authenticate
    # neither an episode start nor writer closure.
    source = retained(store, b"698 synthetic source receipt", "json")
    writer = retained(store, b"698 synthetic closure receipt", "json")
    binding = retained(store, b"698 synthetic binding receipt", "flux_balance_input_binding_receipt_v1")
    value = capture_flux_balance_native_files(store, original_plan=plan,
        source_action_receipt_ref=source["file"]["artifact_ref"], writer_closure_receipt_ref=writer["file"]["artifact_ref"],
        input_binding_file=binding["file"], prior_sources=[], driver_started=True)
    return plan, value


def projection(view="reaction_fluxes"):
    if view == "run_diagnostics":
        return {"version": "flux_balance_projection_selector_v1", "view": view,
            "fields": ["native_run", "objective", "variable_population", "variable_bound_counts", "candidate_feasibility"],
            "row_window": {"offset": 0, "limit": 99}}
    return {"version": "flux_balance_projection_selector_v1", "view": view, "snapshot_phase": "effective",
        "fields": ["flux", "bound_check"], "reaction_positions": [2, 0, 1], "row_window": {"offset": 0, "limit": 99}}


def selector(parameters=None, *, saved=None, view="reaction_fluxes"):
    if parameters is None:
        parameters = json.loads((EMISSIONS / "sbml/calculated.json").read_text())["parameters"]
    return {"version": "flux_balance_result_selector_v1", "mode": "native_result" if saved is None else "saved_sheet_recalculation",
        "saved_sheet_file": saved, "calculation_parameters": deepcopy(parameters), "projection": projection(view)}


def empty_parameters():
    result = selector()["calculation_parameters"]
    return {k: [] if type(v) is list else v for k, v in result.items()}


def native_plan(tmp_path, original, captured, selected=None):
    return build_native_flux_balance_worker_plan(directory=str(tmp_path / "worker"), original_plan=original,
        capture=captured, selector=selected or selector())


def output(plan, name):
    return json.loads((Path(plan["directory"]) / (name + ".json")).read_text())


def replace_role(store, captured, role, data):
    row = next(r for r in captured["files"] if r["role"] == role)
    row["retained"] = retained(store, data, row["format"])


def manifest(store, captured, change):
    row = next(r for r in captured["files"] if r["role"] == "manifest")
    value = json.loads(Path(row["retained"]["path"]).read_text())
    change(value)
    row["retained"] = record(store, value, row["format"])


def qualify_missing(captured, role):
    next(r for r in captured["files"] if r["role"] == role)["retained"] = None
    captured["failures"].append(worker._issue("artifact_missing", "/files/" + role))


def forbid_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("finite worker attempted native execution/acquisition")
    original_import = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert name.split(".")[0] not in {"cobra", "optlang", "swiglpk"}
        assert name not in {"gene_annotation_episode.native_flux_balance_driver", "gene_annotation_episode.native_flux_balance_cobra_glpk"}
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    return forbidden


@pytest.mark.parametrize("profile", ["sbml", "cobra_json"])
def test_actual688_store_capture_shared_numbers_projection_and_replay(store, tmp_path, monkeypatch, profile):
    original, captured = capture(store, profile)
    plan = native_plan(tmp_path, original, captured)
    forbidden = forbid_execution(monkeypatch)
    monkeypatch.setattr(store, "put", forbidden)
    result = worker.execute_flux_balance_worker(plan)
    assert result["failures"] == []
    assert result["native_association"] == "verified"
    assert result["new_attempt_evidence_roles"] == ["effective_model", "effective_problem", "solution", "native_log", "manifest"]
    assert result["requested_projection_valid"] is True
    payloads = {r["role"]: {"file": r["retained"]["file"], "bytes": Path(r["retained"]["path"]).read_bytes(), "state": "present"} for r in captured["files"]}
    expected_sheet = populate_flux_balance_sheet(bundle=parse_fba_capture(payloads, expected=original["identity"]))
    expected = calculate_flux_balance_sheet(expected_sheet, parameters=plan["selector"]["calculation_parameters"])
    assert output(plan, "sheet") == expected_sheet
    assert output(plan, "calculations") == expected
    assert output(plan, "projection") == project_fba_result(expected_sheet, expected, selector=plan["selector"]["projection"])
    historical = json.loads((EMISSIONS / profile / "calculated.json").read_text())
    for key in ("objective", "expected_variable_count", "expected_reaction_count", "evaluated_variable_bound_count", "violated_variable_bound_count"):
        # Native source File addresses differ between old fixture normalization
        # and actual Store custody. Numerical values remain identical.
        if key == "objective":
            assert expected[key]["full_calculated"]["value"] == historical[key]["full_calculated"]["value"] == 10
        else:
            assert expected[key] == historical[key]
    assert [r["flux"]["value"] for r in expected["reaction_checks"]] == [10, 10, 10]
    assert expected["expected_variable_count"] == 6
    assert expected["evaluated_variable_bound_count"] == 12
    assert expected["violated_variable_bound_count"] == 0
    # Sealed replay cannot reacquire inputs, parse or recalculate.
    for name in ("_native", "parse_fba_capture", "populate_flux_balance_sheet", "calculate_flux_balance_sheet", "project_fba_result"):
        monkeypatch.setattr(worker, name, forbidden)
    allowed = {str(Path(plan["directory"]) / name) for name in ("worker-result.json", ".flux-balance-worker-plan.json", "sheet.json", "calculations.json", "projection.json", "diagnostics.json")}
    reader = worker.read_bytes
    def replay_read(path):
        assert str(path) in allowed
        return reader(path)
    monkeypatch.setattr(worker, "read_bytes", replay_read)
    assert worker.execute_flux_balance_worker(plan) == result
    assert store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0
    evidence = Path(os.environ["HMMER529_ATTEMPT"]) / ("worker698-actual-" + profile + ".json")
    evidence.write_text(json.dumps({"result": result, "objective": expected["objective"],
        "reaction_fluxes": [r["flux"]["value"] for r in expected["reaction_checks"]],
        "variables": expected["expected_variable_count"], "finite_variable_bound_sides": expected["evaluated_variable_bound_count"],
        "violated_variable_bound_sides": expected["violated_variable_bound_count"], "new_solves": 0}, allow_nan=False))


def test_saved_only_changed_parameters_exact_sheet_and_no_native_reads(store, tmp_path, monkeypatch):
    value = json.loads(BASE.read_text())
    sheet = record(store, value["sheet"], "flux_balance_sheet_v1")
    params = deepcopy(value["calculations"]["parameters"])
    for threshold in params["active_flux_thresholds"]:
        threshold["value"] = 6.5
    plan = build_saved_flux_balance_worker_plan(directory=str(tmp_path / "worker"), sheet=sheet,
        selector=selector(params, saved=sheet["file"], view="run_diagnostics"))
    forbidden = forbid_execution(monkeypatch)
    for name in ("_native", "parse_fba_capture", "populate_flux_balance_sheet"):
        monkeypatch.setattr(worker, name, forbidden)
    reader = worker.read_bytes
    def saved_read(path):
        assert str(path) == sheet["path"] or Path(path).parent == Path(plan["directory"])
        return reader(path)
    monkeypatch.setattr(worker, "read_bytes", saved_read)
    result = worker.execute_flux_balance_worker(plan)
    calculated = output(plan, "calculations")
    assert output(plan, "sheet") == value["sheet"]
    assert calculated == calculate_flux_balance_sheet(value["sheet"], parameters=params)
    assert calculated["active_count"] == 1
    assert calculated["objective"]["native_basis_calculated"]["value"] == -4.25
    assert calculated["objective"]["full_calculated"]["value"] == -2.75
    assert result["native_association"] == "not_applicable" and result["new_attempt_evidence_roles"] == []
    assert result["failures"] == [] and result["requested_projection_valid"]
    for name in ("calculate_flux_balance_sheet", "project_fba_result"):
        monkeypatch.setattr(worker, name, forbidden)
    assert worker.execute_flux_balance_worker(plan) == result


@pytest.mark.parametrize("control,damage,association", [("owner", "missing", "unavailable"), ("started", "missing", "unavailable"),
    ("owner", "wrong", "conflict"), ("started", "wrong", "conflict"), ("started", "malformed", "unavailable")])
def test_synthetic_control_damage_preserves_science(store, tmp_path, control, damage, association):
    original, captured = capture(store)
    item = captured["controls"][control]
    if damage == "missing":
        captured["controls"][control] = None
        captured["failures"].append(worker._issue("artifact_missing", "/controls/" + control))
    elif damage == "malformed":
        captured["controls"][control] = retained(store, b'{"plan_sha256":', item["file"]["format"])
    else:
        value = json.loads(Path(item["path"]).read_text())
        if control == "owner":
            value["policy"]["memory_bytes"] = 1
        else:
            value["plan_sha256"] = "0" * 64
        captured["controls"][control] = record(store, value, item["file"]["format"])
    plan = native_plan(tmp_path, original, captured)
    result = worker.execute_flux_balance_worker(plan)
    assert result["native_association"] == association
    assert result["new_attempt_evidence_roles"] == []
    assert result["requested_projection_valid"]
    assert output(plan, "calculations")["objective"]["full_calculated"]["value"] == 10


@pytest.mark.parametrize("damage", ["missing", "bad_json", "wrong_attempt", "wrong_software", "duplicate", "wrong_path", "absent_claim", "wrong_hash"])
def test_synthetic_manifest_damage_and_independent_sources(store, tmp_path, damage):
    original, captured = capture(store)
    if damage == "missing":
        qualify_missing(captured, "manifest")
    elif damage == "bad_json":
        replace_role(store, captured, "manifest", b'{"version":')
    else:
        def change(value):
            if damage == "wrong_attempt": value["attempt"]["assignment_sha256"] = "0" * 64
            elif damage == "wrong_software": value["software_sha256"] = "0" * 64
            elif damage == "duplicate": value["files"].append(deepcopy(value["files"][2]))
            elif damage == "wrong_path": value["files"][2]["relative_path"] = "wrong.json"
            elif damage == "absent_claim": value["files"][2]["state"] = "absent"
            elif damage == "wrong_hash": value["files"][2]["identity"]["sha256"] = "0" * 64
        manifest(store, captured, change)
    plan = native_plan(tmp_path, original, captured, selector(empty_parameters(), view="run_diagnostics"))
    result = worker.execute_flux_balance_worker(plan)
    assert result["native_association"] == ("unavailable" if damage in {"missing", "bad_json"} else "conflict")
    assert result["requested_projection_valid"]
    assert "original_model" not in result["new_attempt_evidence_roles"]
    assert "selected_request" not in result["new_attempt_evidence_roles"]
    if damage in {"missing", "bad_json"}:
        assert result["new_attempt_evidence_roles"] == ["effective_model", "effective_problem", "solution", "native_log"]
        assert output(plan, "sheet")["native"]["execution_outcome"] == "unknown"
        assert output(plan, "calculations")["objective"]["full_calculated"]["value"] == 10
    else:
        assert any(i["code"] == "artifact_identity_conflict" for i in result["failures"])


@pytest.mark.parametrize("state", ["present", "absent", "truncated", "incompatible"])
def test_synthetic_four_native_states_keep_actual_bytes_and_siblings(store, tmp_path, state):
    original, captured = capture(store)
    model = next(r for r in captured["files"] if r["role"] == "effective_model")
    file = model["retained"]["file"]
    if state == "absent":
        qualify_missing(captured, "effective_model")
    def change(value):
        row = next(r for r in value["files"] if r["role"] == "effective_model")
        row["state"] = state
        if state == "absent": row["identity"] = None
    manifest(store, captured, change)
    plan = native_plan(tmp_path, original, captured, selector(empty_parameters(), view="run_diagnostics"))
    result = worker.execute_flux_balance_worker(plan)
    sheet = output(plan, "sheet")
    assert result["requested_projection_valid"]
    assert sheet["native_solution"]["native"] is not None
    assert (sheet["models"]["effective"] is not None) == (state == "present")
    assert (file in sheet["retained_files"]) == (state != "absent")
    assert ("effective_model" in result["new_attempt_evidence_roles"]) == (state == "present")


@pytest.mark.parametrize("damage", ["missing", "corrupt", "symlink", "directory", "fifo"])
def test_retained_role_read_damage_is_independent(store, tmp_path, damage):
    original, captured = capture(store)
    row = next(r for r in captured["files"] if r["role"] == "solution")
    path = Path(row["retained"]["path"])
    path.chmod(0o644)
    path.unlink()
    if damage == "corrupt": path.write_bytes(b"changed retained bytes")
    elif damage == "symlink": path.symlink_to(captured["files"][0]["retained"]["path"])
    elif damage == "directory": path.mkdir()
    elif damage == "fifo": os.mkfifo(path)
    plan = native_plan(tmp_path, original, captured, selector(empty_parameters(), view="run_diagnostics"))
    result = worker.execute_flux_balance_worker(plan)
    assert result["requested_projection_valid"]
    assert output(plan, "sheet")["models"]["effective"] is not None
    assert output(plan, "sheet")["native_solution"]["native"] is None
    assert any(i["field"] == "/files/solution" for i in result["failures"])


@pytest.mark.parametrize("damage", ["agree", "observed_mismatch", "wrong_plan", "wrong_digest", "wrong_keys", "missing"])
def test_synthetic_v2_environment_exact_control(store, tmp_path, damage):
    original, captured = capture(store)
    original["version"] = "flux_balance_run_plan_v2"
    original["environment_binding"] = bind_flux_balance_environment(original["requested_job"], execution_id=original["identity"]["execution_id"],
        attempt_directory=original["attempt_directory"], selection={"version": "flux_balance_execution_selection_v1", "environment_realization": "operation_scoped_tmp_and_cache_v1"})
    captured["original_plan_sha256"] = digest(original)
    captured["controls"]["owner"] = record(store, original, "flux_balance_owner_plan_v1")
    expected = original["environment_binding"]["realized_environment"]
    observation = {"version": "flux_balance_environment_observation_v1", "plan_sha256": digest(original),
        "expected_environment": expected, "observed_environment": deepcopy(expected)}
    if damage == "wrong_plan": observation["plan_sha256"] = "0" * 64
    if damage == "wrong_keys": observation["observed_environment"]["UNDECLARED"] = "bad"
    if damage == "observed_mismatch": observation["observed_environment"]["TMPDIR"] = None
    captured["controls"]["environment"] = record(store, observation, "flux_balance_environment_observation_v1")
    captured["controls"]["started"] = record(store, {"plan_sha256": digest(original), "started_at": "synthetic-698",
        "environment_observation_sha256": "0" * 64 if damage == "wrong_digest" else digest(observation)}, "flux_balance_started_control_v1")
    if damage == "missing":
        captured["controls"]["environment"] = None
        captured["failures"].append(worker._issue("artifact_missing", "/controls/environment"))
    plan = native_plan(tmp_path, original, captured)
    result = worker.execute_flux_balance_worker(plan)
    assert result["requested_projection_valid"]
    expected_state = "conflict" if damage in {"wrong_plan", "wrong_digest"} else "unavailable" if damage in {"wrong_keys", "missing"} else "verified"
    assert result["native_association"] == expected_state
    if damage == "observed_mismatch":
        assert any(i["field"] == "/controls/environment/observed_environment" and i["code"] == "binding_unavailable" for i in result["failures"])


def test_partial_csv_rows_survive_without_complete_json_padding(store, tmp_path):
    original, captured = capture(store)
    data = b'reaction_id,reaction_name,flux,lower_bound,upper_bound\nIN,in,10,0,10\nAB,"unfinished'
    replace_role(store, captured, "flux_csv", data)
    def change(value):
        row = next(r for r in value["files"] if r["role"] == "flux_csv")
        row["identity"] = {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
        row["state"] = "truncated"
    manifest(store, captured, change)
    selected = selector()
    selected["projection"] = {"version": "flux_balance_projection_selector_v1", "view": "csv_flux_rows",
        "source_row_indices": [0, 1], "fields": ["flux"], "row_window": {"offset": 0, "limit": 2}}
    plan = native_plan(tmp_path, original, captured, selected)
    result = worker.execute_flux_balance_worker(plan)
    assert result["requested_projection_valid"]
    assert len(output(plan, "sheet")["native"]["flux_rows"]) == 1
    assert output(plan, "projection")["rows"][0]["values"]["flux"]["flux"]["value"] == 10
    assert output(plan, "projection")["rows"][1]["availability"] == "unavailable"


@pytest.mark.parametrize("damage", ["sheet", "calculations", "projection", "diagnostics", "plan"])
def test_replay_tampering_never_reexecutes(store, tmp_path, monkeypatch, damage):
    value = json.loads(BASE.read_text())
    sheet = record(store, value["sheet"], "flux_balance_sheet_v1")
    plan = build_saved_flux_balance_worker_plan(directory=str(tmp_path / "worker"), sheet=sheet,
        selector=selector(value["calculations"]["parameters"], saved=sheet["file"]))
    worker.execute_flux_balance_worker(plan)
    if damage == "plan":
        plan["selector"]["calculation_parameters"]["objective_absolute_tolerance"] = 123
    else:
        target = Path(plan["directory"]) / (damage + ".json")
        target.chmod(0o644)
        target.write_bytes(b"tampered")
    monkeypatch.setattr(worker, "calculate_flux_balance_sheet", lambda *a, **k: pytest.fail("replay recalculated"))
    with pytest.raises(ValueError, match="replay_invalid"):
        worker.execute_flux_balance_worker(plan)


def test_unsealed_preserves_partial_files_and_invalid_projection_keeps_calculations(store, tmp_path):
    original, captured = capture(store)
    selected = selector()
    selected["projection"]["reaction_positions"] = [100]
    plan = native_plan(tmp_path, original, captured, selected)
    result = worker.execute_flux_balance_worker(plan)
    assert result["requested_projection_valid"] is False
    assert result["outputs"][2]["declaration"]["state"] == "absent"
    assert output(plan, "calculations")["objective"]["full_calculated"]["value"] == 10
    assert result["failures"][-1]["code"] == "projection_invalid"
    assert worker.execute_flux_balance_worker(plan) == result
    (Path(plan["directory"]) / "worker-result.json").unlink()
    before = {p.name: p.read_bytes() for p in Path(plan["directory"]).iterdir()}
    with pytest.raises(ValueError, match="unsealed_directory"):
        worker.execute_flux_balance_worker(plan)
    assert before == {p.name: p.read_bytes() for p in Path(plan["directory"]).iterdir()}


def test_strict_closed_plans_results_and_cli(store, tmp_path):
    original, captured = capture(store)
    plan = native_plan(tmp_path, original, captured)
    for change in (lambda p: p.update(extra=1), lambda p: p.update(directory="/tmp/../bad"),
            lambda p: p.update(directory=original["attempt_directory"]),
            lambda p: p["selector"]["projection"]["reaction_positions"].append(True),
            lambda p: p["selector"]["calculation_parameters"].pop("objective_absolute_tolerance")):
        value = deepcopy(plan)
        change(value)
        with pytest.raises((ValueError, TypeError)):
            validate_flux_balance_worker_plan(value)
    result = worker.execute_flux_balance_worker(plan)
    for change in (lambda r: r.update(extra=1), lambda r: r.update(requested_projection_valid=1),
            lambda r: r["new_attempt_evidence_roles"].append("original_model"),
            lambda r: r["outputs"][0]["declaration"].update(size_bytes=True)):
        value = deepcopy(result)
        change(value)
        with pytest.raises((ValueError, TypeError)):
            validate_flux_balance_worker_result(value)
    for args in ([], ["relative.json"], ["/one", "/two"]):
        with pytest.raises(ValueError): worker.main(args)
    assert "gene_annotation_episode.native_flux_balance_driver" not in sys.modules
    assert "gene_annotation_episode.native_flux_balance_cobra_glpk" not in sys.modules


@pytest.mark.parametrize("damage", ["none", "missing", "corrupt", "non_json"])
def test_synthetic_selected_prior_read_and_missing_preserve_native_siblings(store, tmp_path, damage):
    original, captured = capture(store)
    prior = retained(store, b'{"receipt":"698 synthetic selected prior"}', "synthetic_receipt_v1")
    original["requested_job"]["native_flux_balance"]["model_input"]["acquisition_receipt_file"] = prior["file"]
    original["identity"]["requested_job_sha256"] = digest(original["requested_job"])
    captured["original_plan_sha256"] = digest(original)
    captured["controls"]["owner"] = record(store, original, "flux_balance_owner_plan_v1")
    captured["controls"]["started"] = record(store, {"plan_sha256": digest(original), "started_at": "698 synthetic prior"}, "flux_balance_started_control_v1")
    selected = record(store, {"version": "flux_balance_selected_request_v1", "attempt": original["identity"],
        "requested_job": original["requested_job"]}, "flux_balance_selected_request_v1")
    next(r for r in captured["files"] if r["role"] == "selected_request")["retained"] = selected
    def change(value):
        value["attempt"] = original["identity"]
        row = next(r for r in value["files"] if r["role"] == "selected_request")
        row["identity"] = {k: selected["file"][k] for k in ("sha256", "size_bytes")}
    manifest(store, captured, change)
    captured["prior_sources"] = [prior]
    if damage == "missing":
        captured["prior_sources"] = []
        captured["failures"].append(worker._issue("artifact_missing", "/prior_sources/0"))
    elif damage == "corrupt":
        path = Path(prior["path"])
        path.chmod(0o644)
        path.write_bytes(b"corrupt selected retained prior")
    elif damage == "non_json":
        # Whole-file receipt use permits opaque bytes, without invented pointers.
        opaque = retained(store, b"opaque 698 receipt\xff\x00", "synthetic_receipt_v1")
        return _selected_prior_opaque(store, tmp_path, original, captured, prior, opaque)
    plan = native_plan(tmp_path, original, captured)
    result = worker.execute_flux_balance_worker(plan)
    assert result["requested_projection_valid"]
    assert len(plan["capture"]["files"]) == 8
    assert output(plan, "calculations")["objective"]["full_calculated"]["value"] == 10
    assert (prior["file"] in output(plan, "sheet")["retained_files"]) == (damage == "none")
    if damage in {"missing", "corrupt"}:
        assert any(i["field"] == "/prior_sources/0" for i in result["failures"])


def _selected_prior_opaque(store, tmp_path, original, captured, prior, opaque):
    original["requested_job"]["native_flux_balance"]["model_input"]["acquisition_receipt_file"] = opaque["file"]
    original["identity"]["requested_job_sha256"] = digest(original["requested_job"])
    captured["original_plan_sha256"] = digest(original)
    captured["controls"]["owner"] = record(store, original, "flux_balance_owner_plan_v1")
    captured["controls"]["started"] = record(store, {"plan_sha256": digest(original), "started_at": "698 synthetic opaque prior"}, "flux_balance_started_control_v1")
    selected = record(store, {"version": "flux_balance_selected_request_v1", "attempt": original["identity"], "requested_job": original["requested_job"]}, "flux_balance_selected_request_v1")
    next(r for r in captured["files"] if r["role"] == "selected_request")["retained"] = selected
    def change(value):
        value["attempt"] = original["identity"]
        next(r for r in value["files"] if r["role"] == "selected_request")["identity"] = {k: selected["file"][k] for k in ("sha256", "size_bytes")}
    manifest(store, captured, change)
    captured["prior_sources"] = [opaque]
    plan = native_plan(tmp_path, original, captured)
    result = worker.execute_flux_balance_worker(plan)
    assert result["requested_projection_valid"]
    assert opaque["file"] in output(plan, "sheet")["retained_files"]
    assert prior["file"] not in output(plan, "sheet")["retained_files"]


@pytest.mark.parametrize("damage", ["missing", "bad_json", "wrong_sheet_version"])
def test_saved_missing_and_incompatible_sheet_have_specific_diagnostics(store, tmp_path, damage):
    value = json.loads(BASE.read_text())
    data = (canonical(value["sheet"]) + "\n").encode()
    if damage == "bad_json": data = b'{"version":'
    elif damage == "wrong_sheet_version":
        value["sheet"]["version"] = "wrong_sheet_v1"
        data = canonical(value["sheet"]).encode()
    sheet = retained(store, data, "flux_balance_sheet_v1")
    if damage == "missing": Path(sheet["path"]).unlink()
    plan = build_saved_flux_balance_worker_plan(directory=str(tmp_path / "worker"), sheet=sheet,
        selector=selector(value["calculations"]["parameters"], saved=sheet["file"]))
    result = worker.execute_flux_balance_worker(plan)
    assert not result["requested_projection_valid"]
    assert all(r["declaration"]["state"] == "absent" for r in result["outputs"][:3])
    assert result["failures"][0]["code"] == ("artifact_missing" if damage == "missing" else "schema_invalid")
    assert worker.execute_flux_balance_worker(plan) == result


@pytest.mark.parametrize("driver_started", [False, None])
def test_no_confirmed_start_preserves_measurements_without_new_work(store, tmp_path, driver_started):
    original, captured = capture(store)
    captured["driver_started"] = driver_started
    plan = native_plan(tmp_path, original, captured)
    result = worker.execute_flux_balance_worker(plan)
    assert result["native_association"] == "unavailable"
    assert result["new_attempt_evidence_roles"] == []
    assert result["requested_projection_valid"]


def test_synthetic_infeasible_status_is_data_without_success_gate(store, tmp_path):
    value = json.loads(BASE.read_text())
    value["sheet"]["native"]["solver"]["status"] = "infeasible"
    value["sheet"]["native"]["solver"]["raw_status"] = "infeasible"
    sheet = record(store, value["sheet"], "flux_balance_sheet_v1")
    plan = build_saved_flux_balance_worker_plan(directory=str(tmp_path / "worker"), sheet=sheet,
        selector=selector(value["calculations"]["parameters"], saved=sheet["file"], view="run_diagnostics"))
    result = worker.execute_flux_balance_worker(plan)
    assert result["requested_projection_valid"] and result["failures"] == []
    assert output(plan, "calculations")["native_solver_status"] == "infeasible"
    assert output(plan, "sheet")["native"]["solver"]["raw_status"] == "infeasible"


def test_wrong_selected_request_and_unexpected_v1_environment_preserve_independent_records(store, tmp_path):
    original, captured = capture(store)
    selected_row = next(r for r in captured["files"] if r["role"] == "selected_request")
    value = json.loads(Path(selected_row["retained"]["path"]).read_text())
    value["requested_job"]["native_flux_balance"]["objective"] = {"kind": "single_reaction", "reaction_id": "IN"}
    selected_row["retained"] = record(store, value, selected_row["format"])
    environment = record(store, {"synthetic": "unexpected v1 observation"}, "flux_balance_environment_observation_v1")
    captured["controls"]["environment"] = environment
    captured["failures"].append(worker._issue("artifact_identity_conflict", "/controls/environment", source=environment["file"]))
    plan = native_plan(tmp_path, original, captured)
    result = worker.execute_flux_balance_worker(plan)
    assert result["native_association"] == "conflict" and result["requested_projection_valid"]
    assert output(plan, "sheet")["original_request_file"] is None
    assert output(plan, "calculations")["objective"]["full_calculated"]["value"] == 10
    assert any(i["field"] == "/files/selected_request" for i in result["failures"])


def test_duplicate_nonfinite_manifest_never_supplies_outcome_or_solve_count(store, tmp_path):
    original, captured = capture(store)
    replace_role(store, captured, "manifest", b'{"version":"flux_balance_native_manifest_v1","version":"flux_balance_native_manifest_v1","solve_call_count":1e999}')
    qualify_missing(captured, "solution")
    plan = native_plan(tmp_path, original, captured, selector(empty_parameters(), view="run_diagnostics"))
    result = worker.execute_flux_balance_worker(plan)
    native = output(plan, "sheet")["native"]
    assert native["solve_call_count"] is None and native["execution_outcome"] == "unknown"
    assert result["requested_projection_valid"] and result["native_association"] == "unavailable"
    assert output(plan, "sheet")["models"]["effective"] is not None


def test_partial_output_write_is_unsealed_and_not_retried(store, tmp_path, monkeypatch):
    value = json.loads(BASE.read_text())
    sheet = record(store, value["sheet"], "flux_balance_sheet_v1")
    plan = build_saved_flux_balance_worker_plan(directory=str(tmp_path / "worker"), sheet=sheet,
        selector=selector(value["calculations"]["parameters"], saved=sheet["file"]))
    original_write = worker.immutable_json
    def stop_at_calculations(path, data):
        if Path(path).name == "calculations.json":
            raise OSError("synthetic interrupted output write")
        return original_write(path, data)
    monkeypatch.setattr(worker, "immutable_json", stop_at_calculations)
    with pytest.raises(OSError): worker.execute_flux_balance_worker(plan)
    assert (Path(plan["directory"]) / "sheet.json").exists()
    assert not (Path(plan["directory"]) / "worker-result.json").exists()
    monkeypatch.setattr(worker, "calculate_flux_balance_sheet", lambda *a, **k: pytest.fail("partial attempt was recalculated"))
    with pytest.raises(ValueError, match="unsealed_directory"):
        worker.execute_flux_balance_worker(plan)
