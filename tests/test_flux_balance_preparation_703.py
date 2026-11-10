"""Production worker custody with two real finite calculations, no FBA solve.

Fault cases explicitly construct synthetic closure records or alter test-only
controls. They reuse retained bytes, never claim new scientific measurements.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import native_flux_balance_preparation as prep
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.flux_balance_worker_contracts import (
    OUTPUTS, build_native_flux_balance_worker_plan, build_saved_flux_balance_worker_plan,
)
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.native_flux_balance_capture import capture_flux_balance_native_files
from gene_annotation_episode.native_flux_balance_contracts import POLICY
from gene_annotation_episode.state import Store

pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
ROOT = Path(__file__).resolve().parents[1]
EMISSIONS = ROOT / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions/sbml"
EXAMPLE = ROOT / "verification/tool_graders_flux_balance_core_2026-10-29_679/VERIFIED_NUMERICAL_EXAMPLE_001.json"


def retain(store, raw, format_):
    reference = store.artifact(raw, "application/octet-stream")
    file = {"artifact_ref": reference, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "format": format_}
    return {"file": file, "path": str(retained_native_file(store, file))}


def record(store, value, format_):
    return retain(store, (canonical(value) + "\n").encode("utf-8"), format_)


def selector(parameters, *, saved=None):
    return {"version": "flux_balance_result_selector_v1", "mode": "native_result" if saved is None else "saved_sheet_recalculation",
        "saved_sheet_file": saved, "calculation_parameters": deepcopy(parameters), "projection": {
            "version": "flux_balance_projection_selector_v1", "view": "run_diagnostics",
            "fields": ["objective", "variable_population", "variable_bound_counts", "candidate_feasibility"],
            "row_window": {"offset": 0, "limit": 99}}}


def load_file(store, file):
    return json.loads(retained_native_file(store, file).read_bytes())


def outputs(prepared):
    return {spec[0]: row["observed"] for spec, row in zip(OUTPUTS, prepared["outputs"])}


def forbidden(*args, **kwargs):
    raise AssertionError("historical validation attempted dispatch, native observation or scientific work")


@pytest.fixture(scope="module")
def actual_saved(tmp_path_factory):
    base = tmp_path_factory.mktemp("preparation703-saved")
    with Store(base / "retained") as store:
        example = json.loads(EXAMPLE.read_text())
        # Pretty input bytes differ from the canonical emitted sheet. Removing
        # this input therefore does not remove an identically addressed output.
        supplied = retain(store, json.dumps(example["sheet"], indent=2, allow_nan=False).encode(), "flux_balance_sheet_v1")
        parameters = deepcopy(example["calculations"]["parameters"])
        for item in parameters["active_flux_thresholds"]:
            item["value"] = 6.5
        plan = build_saved_flux_balance_worker_plan(directory=str(base / "action/worker"), sheet=supplied,
            selector=selector(parameters, saved=supplied["file"]))
        prepared = prep.prepare_flux_balance_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY))
        execution = load_file(store, prepared["execution_receipt_file"])
        yield {"base": base, "store": store, "plan": plan, "prepared": prepared,
            "execution": execution, "input": supplied}


def test_real_saved_worker_common_scratch_root_parameters_and_native_receipt(actual_saved):
    case = actual_saved
    store, plan, prepared, execution = (case[k] for k in ("store", "plan", "prepared", "execution"))
    assert prepared["failures"] == []
    assert prepared["result"]["native_association"] == "not_applicable"
    assert prepared["result"]["new_attempt_evidence_roles"] == []
    assert prepared["result"]["requested_projection_valid"]
    files = outputs(prepared)
    sheet = load_file(store, files["sheet"])
    calculations = load_file(store, files["calculations"])
    projection = load_file(store, files["projection"])
    assert sheet == json.loads(EXAMPLE.read_text())["sheet"]
    assert calculations["parameters"] == plan["selector"]["calculation_parameters"]
    assert calculations["active_count"] == 1
    assert calculations["objective"]["native_basis_calculated"]["value"] == -4.25
    assert calculations["objective"]["full_calculated"]["value"] == -2.75
    assert projection["selector"] == plan["selector"]["projection"]
    assert prepared["result"]["plan_sha256"] == digest(plan)
    assert execution["terminal"] and execution["quiescent"] and execution["returncode"] == 0
    assert execution["failure"] is None
    common, adapter, out = Path(plan["directory"]).parent, Path(plan["directory"] + ".execution"), Path(plan["directory"])
    assert execution["handle"]["cwd"] == execution["request"]["cwd"] == str(common)
    assert adapter.parent == out.parent == common
    assert all(Path(p).parent == common for p in execution["handle"]["paths"].values())
    assert all(execution["request"]["env"][k] == str(common) for k in ("TMPDIR", "TMP", "TEMP"))
    assert execution["handle"]["stdout"] == str(adapter / "worker.stdout")
    assert execution["intent"]["execution_directory"] == str(adapter)
    assert execution["metadata"]["policy"] == POLICY
    assert execution["metadata"]["verified_cgroup"] == {"memory_max": 21474836480, "memory_swap_max": 0,
        "kill_mode": "control-group", "oom_policy": "kill"}
    assert execution["metadata"]["enforcement"]["scratch"] == "monitored_visible_allocated_bytes_with_possible_overshoot"
    source_names = {Path(p["path"]).name for p in execution["intent"]["source_pins"]}
    assert "flux_balance_result_worker.py" in source_names
    assert "native_flux_balance_driver.py" not in source_names and "native_flux_balance_cobra_glpk.py" not in source_names
    assert prep.validate_prepared_flux_balance_worker(store, prepared, plan=plan) == prepared
    Path(os.environ["HMMER529_ATTEMPT"]).joinpath("preparation703-saved-result.json").write_text(json.dumps({
        "prepared": prepared, "execution": execution, "active_count": 1, "native_basis_objective": -4.25,
        "full_objective": -2.75, "native_solves": 0}, allow_nan=False))


def test_real_retained688_native_worker_same_numbers_and_replay(tmp_path, monkeypatch):
    with Store(tmp_path / "retained") as store:
        original = json.loads((EMISSIONS / "selected-plan.json").read_text())
        source = retain(store, b"703 synthetic metadata-only source receipt", "json")
        closure = retain(store, b"703 synthetic metadata-only closure receipt", "json")
        binding = retain(store, b"703 synthetic metadata-only binding", "flux_balance_input_binding_receipt_v1")
        captured = capture_flux_balance_native_files(store, original_plan=original,
            source_action_receipt_ref=source["file"]["artifact_ref"], writer_closure_receipt_ref=closure["file"]["artifact_ref"],
            input_binding_file=binding["file"], prior_sources=[], driver_started=True)
        parameters = json.loads((EMISSIONS / "calculated.json").read_text())["parameters"]
        plan = build_native_flux_balance_worker_plan(directory=str(tmp_path / "action/worker"), original_plan=original,
            capture=captured, selector=selector(parameters))
        prepared = prep.prepare_flux_balance_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY))
        assert prepared["failures"] == [] and prepared["result"]["failures"] == []
        assert prepared["result"]["native_association"] == "verified"
        files = outputs(prepared)
        calculated = load_file(store, files["calculations"])
        assert calculated["objective"]["full_calculated"]["value"] == 10
        assert [r["flux"]["value"] for r in calculated["reaction_checks"]] == [10, 10, 10]
        assert calculated["expected_variable_count"] == 6
        assert calculated["evaluated_variable_bound_count"] == 12
        assert calculated["violated_variable_bound_count"] == 0
        execution = load_file(store, prepared["execution_receipt_file"])
        assert execution["returncode"] == 0 and execution["metadata"]["policy"] == POLICY
        Path(os.environ["HMMER529_ATTEMPT"]).joinpath("preparation703-native-result.json").write_text(json.dumps({
            "prepared": prepared, "execution": execution, "objective": 10, "fluxes": [10, 10, 10],
            "variables": 6, "finite_variable_bound_sides": 12, "violations": 0, "native_solves": 0}, allow_nan=False))
        # Remove only this test's retained input copies, never original688 files.
        protected = {file["artifact_ref"] for file in files.values() if file is not None}
        for row in captured["files"]:
            file = row["retained"]["file"]
            if file["artifact_ref"] not in protected:
                Path(row["retained"]["path"]).unlink(missing_ok=True)
        Path(execution["intent"]["interpreter"]["path"]).unlink()
        shutil.rmtree(Path(plan["directory"] + ".execution") / "source_snapshot")
        for name in ("resume_start", "prepare_job", "status", "wait_job", "start_prepared"):
            monkeypatch.setattr(native, name, forbidden)
        monkeypatch.setattr(prep, "_snapshot", forbidden)
        monkeypatch.setattr(prep, "_verify_pins", forbidden)
        assert prep.prepare_flux_balance_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY)) == prepared


def test_saved_closed_replay_without_input_or_current_runtime(actual_saved, monkeypatch):
    case = actual_saved
    assert case["input"]["file"]["artifact_ref"] != outputs(case["prepared"])["sheet"]["artifact_ref"]
    Path(case["input"]["path"]).unlink()
    Path(case["execution"]["intent"]["interpreter"]["path"]).unlink()
    shutil.rmtree(Path(case["plan"]["directory"] + ".execution") / "source_snapshot")
    for name in ("resume_start", "prepare_job", "status", "wait_job", "start_prepared"):
        monkeypatch.setattr(native, name, forbidden)
    monkeypatch.setattr(prep, "_snapshot", forbidden)
    monkeypatch.setattr(prep, "_verify_pins", forbidden)
    assert prep.prepare_flux_balance_result_worker(case["store"], plan=case["plan"], policy=LocalJobPolicy(**POLICY)) == case["prepared"]


@pytest.mark.parametrize("fault", ["swap", "cwd", "request_env", "request_raw", "outside_path", "duplicate_path",
    "terminal", "returncode_bool", "intent_directory", "duplicate_pin", "source_outside", "file_format", "failure_shape"])
def test_frozen_execution_contradictions_reject_without_live_work(actual_saved, monkeypatch, fault):
    execution = deepcopy(actual_saved["execution"])
    if fault == "swap": execution["metadata"]["verified_cgroup"]["memory_swap_max"] = False
    elif fault == "cwd": execution["handle"]["cwd"] = execution["intent"]["execution_directory"]
    elif fault == "request_env": execution["request"]["env"]["OMP_NUM_THREADS"] = "8"
    elif fault == "request_raw": execution["request_raw"] += " "
    elif fault == "outside_path": execution["handle"]["paths"]["status"] = "/elsewhere/status"
    elif fault == "duplicate_path": execution["handle"]["paths"]["result"] = execution["handle"]["paths"]["request"]
    elif fault == "terminal": execution["terminal"] = False
    elif fault == "returncode_bool": execution["returncode"] = False
    elif fault == "intent_directory": execution["intent"]["execution_directory"] += "-other"
    elif fault == "duplicate_pin": execution["intent"]["source_pins"].append(execution["intent"]["source_pins"][0])
    elif fault == "source_outside": execution["intent"]["source_pins"][0]["path"] = "/outside/source.py"
    elif fault == "file_format": execution["request_file"]["format"] = "wrong"
    else: execution["failure"] = {"code": "synthetic"}
    monkeypatch.setattr(native, "status", forbidden)
    monkeypatch.setattr(prep, "_verify_pins", forbidden)
    with pytest.raises(ValueError):
        prep.validate_flux_balance_worker_execution(execution, plan=actual_saved["plan"],
            plan_file=actual_saved["prepared"]["plan_file"])


@pytest.mark.parametrize("fault", ["result_selector", "output_order", "output_missing", "output_format", "failure_locator"])
def test_prepared_record_contradictions_reject(actual_saved, fault):
    value = deepcopy(actual_saved["prepared"])
    if fault == "result_selector": value["result"]["selector"]["calculation_parameters"]["objective_absolute_tolerance"] = 99
    elif fault == "output_order": value["outputs"].reverse()
    elif fault == "output_missing": value["outputs"][0]["observed"] = None
    elif fault == "output_format": value["outputs"][0]["observed"]["format"] = "opaque"
    else:
        issue = prep._issue("artifact_missing", "/worker/result")
        issue["reaction_position"] = 1
        value["failures"] = [issue]
    with pytest.raises(ValueError):
        prep.validate_prepared_flux_balance_worker(actual_saved["store"], value, plan=actual_saved["plan"])


def original_execution(request):
    # Follow-up checks select original completed evidence, avoiding another
    # actual finite calculation just to exercise malformed control metadata.
    evidence_path = os.environ.get("HMMER_NATIVE_ORACLE_PREPARATION703_EVIDENCE")
    return (json.loads(Path(evidence_path).read_text())["execution"] if evidence_path else
        deepcopy(request.getfixturevalue("actual_saved")["execution"]))


@pytest.mark.parametrize("file_value", [None, {}, []])
def test_malformed_request_File_retains_structured_failure(request, monkeypatch, file_value):
    execution = original_execution(request)
    plan, plan_file = execution["intent"]["plan"], execution["plan_file"]
    execution["request_file"] = file_value
    for name in ("prepare_job", "resume_start", "status", "wait_job"):
        monkeypatch.setattr(native, name, forbidden)
    monkeypatch.setattr(prep, "_verify_pins", forbidden)
    with pytest.raises(ValueError):
        prep.validate_flux_balance_worker_execution(execution, plan=plan, plan_file=plan_file)


def _replace_prefix(value, previous, current):
    if type(value) is str:
        return current + value[len(previous):] if value.startswith(previous) else value
    if type(value) is list:
        return [_replace_prefix(v, previous, current) for v in value]
    if type(value) is dict:
        return {k: _replace_prefix(v, previous, current) for k, v in value.items()}
    return value


def test_lost_handle_with_owned_intent_and_partial_output_cannot_reserve_again(request, tmp_path, monkeypatch):
    original = original_execution(request)
    previous = str(Path(original["intent"]["plan"]["directory"]).parent)
    common = tmp_path / "action"
    root, out = common / "worker.execution", common / "worker"
    root.mkdir(parents=True);out.mkdir()
    plan = _replace_prefix(original["intent"]["plan"], previous, str(common))
    intent = _replace_prefix(original["intent"], previous, str(common))
    intent["plan"] = plan
    (root / "plan.json").write_text(canonical(plan) + "\n")
    (root / "intent.json").write_text(canonical(intent) + "\n")
    (out / "partial.json").write_bytes(b'preserved original partial work')
    for name in ("prepare_job", "resume_start", "wait_job", "status"):
        monkeypatch.setattr(native, name, forbidden)
    monkeypatch.setattr(prep, "_verify_pins", forbidden)
    with Store(tmp_path / "store") as store:
        with pytest.raises(ValueError, match="fba_preparation_unsealed_output"):
            prep.prepare_flux_balance_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY))
    assert (out / "partial.json").read_bytes() == b'preserved original partial work'
    assert not (root / "worker.handle.json").exists()


def test_lost_handle_with_native_controls_and_empty_output_cannot_reserve_again(request, tmp_path, monkeypatch):
    original = original_execution(request)
    previous = str(Path(original["intent"]["plan"]["directory"]).parent)
    common = tmp_path / "action"
    root, out = common / "worker.execution", common / "worker"
    root.mkdir(parents=True);out.mkdir()
    plan = _replace_prefix(original["intent"]["plan"], previous, str(common))
    intent = _replace_prefix(original["intent"], previous, str(common));intent["plan"] = plan
    (root / "plan.json").write_text(canonical(plan) + "\n")
    (root / "intent.json").write_text(canonical(intent) + "\n")
    previous_request = common / (".local-job-" + "a" * 32 + ".request")
    previous_request.write_bytes(b'preserved ambiguous native reservation')
    for name in ("prepare_job", "resume_start", "wait_job", "status"):
        monkeypatch.setattr(native, name, forbidden)
    monkeypatch.setattr(prep, "_verify_pins", forbidden)
    with Store(tmp_path / "store") as store:
        with pytest.raises(ValueError, match="fba_preparation_unsealed_native_controls"):
            prep.prepare_flux_balance_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY))
    assert previous_request.read_bytes() == b'preserved ambiguous native reservation'
    assert list(out.iterdir()) == [] and not (root / "worker.handle.json").exists()


@pytest.mark.parametrize("fault", ["missing_request", "extra_path", "null_request"])
def test_live_handle_path_shape_fails_before_request_indexing(request, tmp_path, fault, monkeypatch):
    original = original_execution(request)
    previous = str(Path(original["intent"]["plan"]["directory"]).parent)
    common = tmp_path / "action"
    root = common / "worker.execution";root.mkdir(parents=True)
    intent = _replace_prefix(original["intent"], previous, str(common))
    body = _replace_prefix(original["handle"], previous, str(common))
    if fault == "missing_request": del body["paths"]["request"]
    elif fault == "extra_path": body["paths"]["extra"] = str(common / "extra")
    else: body["paths"]["request"] = None
    (root / "worker.handle.json").write_text(canonical(body) + "\n")
    for name in ("prepare_job", "resume_start", "wait_job", "status"):
        monkeypatch.setattr(native, name, forbidden)
    with pytest.raises(ValueError, match="fba_preparation_handle_paths_invalid"):
        prep._validate_live_controls(native.NativeJobHandle(root / "worker.handle.json"), intent)


def synthetic_closed(actual_saved, tmp_path, *, variant):
    """Synthetic interrupted-capture fixture, NOT a native execution receipt.

    Shapes/pins and valid scientific output bytes are reused to test adapter
    failure handling. No new calculation or scientific contribution is claimed.
    """
    store = actual_saved["store"]
    previous = str(Path(actual_saved["plan"]["directory"]).parent)
    common = tmp_path / "synthetic-action"
    root, out = common / "worker.execution", common / "worker"
    root.mkdir(parents=True);out.mkdir()
    plan = _replace_prefix(actual_saved["plan"], previous, str(common))
    execution = _replace_prefix(actual_saved["execution"], previous, str(common))
    intent = execution["intent"]
    intent["plan"] = plan
    execution["handle"]["unit"] = "synthetic703-not-a-real-execution.service"
    execution["request_raw"] = canonical(execution["request"])
    execution["handle"]["request_sha256"] = hashlib.sha256(execution["request_raw"].encode()).hexdigest()
    execution["plan_file"] = record(store, plan, "flux_balance_worker_plan_v1")["file"]
    execution["request_file"] = retain(store, execution["request_raw"].encode(), "native_local_job_request")["file"]
    execution["handle_file"] = record(store, execution["handle"], native.VERSION)["file"]
    if variant == "nonzero":
        execution["returncode"] = execution["metadata"]["native_returncode"] = 5
    if variant == "resource":
        execution["returncode"] = None
        execution["failure"] = {"code": "local_job_resource_limit", "phase": "local_execution",
            "diagnostic": None, "operational": {"resource": "scratch_bytes", "fixture": "synthetic703"}}
    for name, value in (("plan.json", plan), ("intent.json", intent), ("execution.json", execution)):
        (root / name).write_text(canonical(value) + "\n")
    result = deepcopy(actual_saved["prepared"]["result"])
    result["plan_sha256"] = digest(plan)
    for spec, captured in zip(OUTPUTS, actual_saved["prepared"]["outputs"]):
        if captured["observed"] is not None:
            (out / spec[1]).write_bytes(retained_native_file(store, captured["observed"]).read_bytes())
    if variant == "missing_result":
        pass
    elif variant == "malformed_result":
        (out / "worker-result.json").write_bytes(b'{"interrupted":')
    else:
        if variant == "wrong_join": result["plan_sha256"] = "f" * 64
        (out / "worker-result.json").write_text(canonical(result) + "\n")
    if variant == "missing_output": (out / "calculations.json").unlink()
    if variant == "changed_output": (out / "calculations.json").write_bytes(b'opaque changed synthetic bytes')
    return plan


@pytest.mark.parametrize("variant", ["nonzero", "resource", "missing_result", "malformed_result", "wrong_join", "missing_output", "changed_output"])
def test_synthetic_closed_partial_collection_preserves_valid_siblings(actual_saved, tmp_path, monkeypatch, variant):
    plan = synthetic_closed(actual_saved, tmp_path, variant=variant)
    for name in ("resume_start", "prepare_job", "wait_job", "status"):
        monkeypatch.setattr(native, name, forbidden)
    monkeypatch.setattr(prep, "_verify_pins", forbidden)
    prepared = prep.prepare_flux_balance_result_worker(actual_saved["store"], plan=plan, policy=LocalJobPolicy(**POLICY))
    codes = {(r["code"], r["field"]) for r in prepared["failures"]}
    if variant in ("nonzero", "resource"):
        assert ("binding_unavailable", "/worker/execution") in codes
        assert all(r["outcome"] == "verified" for r in prepared["outputs"])
    elif variant in ("missing_result", "malformed_result", "wrong_join"):
        expected = {"missing_result": "artifact_missing", "malformed_result": "schema_invalid", "wrong_join": "artifact_identity_conflict"}[variant]
        assert (expected, "/worker/result") in codes and prepared["result"] is None and prepared["outputs"] == []
        assert (prepared["worker_result_file"] is None) == (variant == "missing_result")
    else:
        expected = "artifact_missing" if variant == "missing_output" else "artifact_identity_conflict"
        assert (expected, "/worker/outputs/calculations") in codes
        assert prepared["outputs"][0]["outcome"] == prepared["outputs"][2]["outcome"] == "verified"
        assert prepared["outputs"][1]["outcome"] == ("unavailable" if variant == "missing_output" else "digest_mismatch")
    assert prep.prepare_flux_balance_result_worker(actual_saved["store"], plan=plan, policy=LocalJobPolicy(**POLICY)) == prepared


@pytest.mark.parametrize("fault", ["memory", "scratch", "wall", "common_overlap", "unsealed", "execution_symlink", "output_symlink", "null_control"])
def test_preflight_does_not_dispatch_or_repair_wrong_boundary(actual_saved, tmp_path, monkeypatch, fault):
    plan = deepcopy(actual_saved["plan"])
    plan["directory"] = str(tmp_path / "action/worker")
    policy = deepcopy(POLICY)
    if fault in ("memory", "scratch", "wall"):
        policy[{"memory": "memory_bytes", "scratch": "scratch_bytes", "wall": "wall_seconds"}[fault]] = 1
    elif fault == "common_overlap":
        plan["directory"] = str(actual_saved["store"].path / "worker")
    else:
        common = Path(plan["directory"]).parent;common.mkdir()
        if fault == "unsealed":
            Path(plan["directory"]).mkdir();Path(plan["directory"], "partial").write_bytes(b'preserved')
        elif fault == "execution_symlink":
            destination = tmp_path / "elsewhere";destination.mkdir()
            Path(plan["directory"] + ".execution").symlink_to(destination, target_is_directory=True)
        elif fault == "output_symlink":
            destination = tmp_path / "elsewhere";destination.mkdir()
            Path(plan["directory"]).symlink_to(destination, target_is_directory=True)
        else:
            root = Path(plan["directory"] + ".execution");root.mkdir()
            (root / "capture.json").write_bytes(b'null')
    monkeypatch.setattr(native, "prepare_job", forbidden)
    monkeypatch.setattr(prep, "_snapshot", forbidden)
    with pytest.raises((ValueError, OSError)):
        prep.prepare_flux_balance_result_worker(actual_saved["store"], plan=plan, policy=LocalJobPolicy(**policy))
