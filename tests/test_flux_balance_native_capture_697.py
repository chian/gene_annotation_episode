"""697 byte custody only: two original688 bundles, otherwise synthetic cases.

Synthetic opaque files and metadata receipts here are never scientific results,
authenticated start/writer evidence, or episode publication authority.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.flux_balance_native_capture_contracts import validate_flux_balance_native_capture
from gene_annotation_episode import native_flux_balance_capture as capture
from gene_annotation_episode.native_file_capture import NativeFileCaptureError, retained_native_file
from gene_annotation_episode.native_flux_balance_contracts import (
    DRIVER_MODULE, ENVIRONMENT_FILENAME, OWNER_FILENAME, POLICY,
    RUN_PLAN_FILENAME, SOURCE_FUNCTION_SHA256, STACK, STARTED_FILENAME,
    bind_flux_balance_environment, flux_balance_environment, flux_balance_output_files,
    validate_flux_balance_run_plan,
)
from gene_annotation_episode.state import Store


ORIGINAL688 = (Path(__file__).resolve().parents[1] / "verification" /
    "tool_graders_hmmer_map_verification_2026-10-28_529" /
    "check151c_producer688/producer-emissions")


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "retained") as value:
        yield value


def artifact(store, data, format_="json"):
    ref = store.artifact(data, "application/octet-stream")
    return {"artifact_ref": ref, "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data), "format": format_}


def metadata(store):
    return {"source_action_receipt_ref": artifact(store, b"synthetic source metadata")['artifact_ref'],
        "writer_closure_receipt_ref": artifact(store, b"synthetic writer metadata")['artifact_ref'],
        "input_binding_file": artifact(store, b"synthetic binding metadata", "flux_balance_input_binding_receipt_v1"),
        "prior_sources": [], "driver_started": True}


def pin(path):
    # Synthetic execution-envelope pins; no software is invoked or verified here.
    return {"path": str(path), "sha256": "c" * 64, "size_bytes": 1}


def synthetic_plan(tmp_path, *, v2=False):
    """Minimal shape-valid selected plan, explicitly no execution authority."""
    module_root, python_home, deps = (tmp_path / x for x in ("modules", "python", "deps"))
    software = {"version": "fba_software_v1", "python": pin(python_home / "bin/python"),
        "python_version": "synthetic", "python_home": str(python_home), "module_root": str(module_root),
        "dependency_roots": [str(deps)], "implementation_files": [pin(module_root / "gene_annotation_episode" / x)
            for x in ("__init__.py", "execution_contracts.py", "flux_balance_contracts.py",
                "native_flux_balance_contracts.py", "native_flux_balance_storage.py",
                "native_flux_balance_cobra_glpk.py", "native_flux_balance_driver.py")],
        "runtime_files": [pin(python_home / "lib/stdlib.py"), pin(deps / "runtime.py")],
        "solver_runtime_files": [pin(deps / "solver.so")],
        "distributions": [{"name": k, "version": v} for k, v in STACK.items()],
        "solver_interface": "optlang.glpk_interface"}
    run, episode, key = "synthetic_capture697", "child", "selected_synthetic_fba"
    lifecycle = tmp_path / "work/.episode-operations" / digest({"run": run, "episode": episode}) / digest(key)
    attempt = lifecycle / "flux-balance-attempt"
    job = {"version": "native_flux_balance_job_v1", "operation": "perform_flux_balance_analysis",
        "mode": "steady_state_linear_fba", "source_alias": "biomni.tool.systems_biology.perform_flux_balance_analysis",
        "model_input": {"file": pin(tmp_path / "input.xml"), "artifact_ref": None, "format": "sbml",
            "original_loader_selection": "sbml_file", "repository_identifier": None, "acquisition_receipt_file": None},
        "constraints": None, "objective": {"kind": "model_default", "reaction_id": None},
        "solver_options": {"feasibility_tolerance": None, "optimality_tolerance": None, "integrality_tolerance": None},
        "software": software, "output_prefix": "outputs", "flux_output_name": "flux.csv",
        "source_function_sha256": SOURCE_FUNCTION_SHA256}
    request = {"argv": [software["python"]["path"], "-B", "-S", "-m", DRIVER_MODULE, RUN_PLAN_FILENAME],
        "environment": flux_balance_environment(software, attempt_directory=str(attempt), lifecycle_directory=str(lifecycle)),
        "native_flux_balance": job}
    plan = {"version": "flux_balance_run_plan_v2" if v2 else "flux_balance_run_plan_v1",
        "identity": {"run_id": run, "episode_id": episode, "resource_id": "synthetic_local",
            "execution_id": str(lifecycle / "native.json"), "attempt_id": digest(key), "operation_key": key,
            "requested_job_sha256": digest(request), "assignment_sha256": "d" * 64},
        "requested_job": request, "attempt_directory": str(attempt), "policy": deepcopy(POLICY),
        "outputs": flux_balance_output_files(job)}
    if v2:
        plan["environment_binding"] = bind_flux_balance_environment(request, execution_id=plan["identity"]["execution_id"],
            attempt_directory=str(attempt), selection={"version": "flux_balance_execution_selection_v1",
                "environment_realization": "operation_scoped_tmp_and_cache_v1"})
    return validate_flux_balance_run_plan(plan)


def update_request_digest(plan):
    plan["identity"]["requested_job_sha256"] = digest(plan["requested_job"])
    return validate_flux_balance_run_plan(plan)


def write_synthetic(plan, *, environment=False):
    root = Path(plan["attempt_directory"])
    for row in plan["outputs"]:
        path = root / row["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("synthetic opaque " + row["role"] + "\0\ufffd").encode())
    (root / OWNER_FILENAME).write_text(canonical(plan))
    (root / STARTED_FILENAME).write_text(canonical({"plan_sha256": digest(plan), "synthetic": True}))
    if environment:
        (root / ENVIRONMENT_FILENAME).write_bytes(b"synthetic opaque environment observation")


def collect(store, plan, kwargs=None):
    return capture.capture_flux_balance_native_files(store, original_plan=plan, **(kwargs or metadata(store)))


def issues(value):
    return {(r["code"], r["field"]) for r in value["failures"]}


def all_native_retained(value):
    assert len(value["files"]) == 8
    assert all(row["retained"] is not None for row in value["files"])


@pytest.mark.parametrize("format_", ["sbml", "cobra_json"])
def test_original688_native_bytes_real_store(store, format_, monkeypatch):
    plan_path = ORIGINAL688 / format_ / "selected-plan.json"
    plan = json.loads(plan_path.read_text())
    before = {row["role"]: (Path(plan["attempt_directory"]) / row["relative_path"]).read_bytes() for row in plan["outputs"]}
    controls_before = {name: (Path(plan["attempt_directory"]) / name).read_bytes() for name in (OWNER_FILENAME, STARTED_FILENAME)}
    forbidden = lambda *a, **k: pytest.fail("capture must not launch, acquire, publish, grant or connect")
    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "Popen", forbidden)
        patch.setattr(socket.socket, "connect", forbidden)
        patch.setattr(store, "put", forbidden)
        value = collect(store, plan)
    all_native_retained(value)
    assert value["failures"] == []
    assert list(value["controls"]) == ["owner", "started", "environment"]
    assert value["controls"]["environment"] is None
    for row, expected in zip(value["files"], plan["outputs"]):
        assert {k: row[k] for k in expected} == expected
        data = before[row["role"]]
        file = row["retained"]["file"]
        assert file == {"artifact_ref": "artifact_" + hashlib.sha256(data).hexdigest(),
            "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), "format": row["format"]}
        assert retained_native_file(store, file).read_bytes() == data
        assert (Path(plan["attempt_directory"]) / row["relative_path"]).read_bytes() == data
    for key, filename in (("owner", OWNER_FILENAME), ("started", STARTED_FILENAME)):
        assert Path(value["controls"][key]["path"]).read_bytes() == controls_before[filename]
    assert store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0
    assert "gene_annotation_episode.native_flux_balance_driver" not in sys.modules
    assert "gene_annotation_episode.native_flux_balance_cobra_glpk" not in sys.modules


@pytest.mark.parametrize("damage", ["missing", "changed", "symlink", "directory", "fifo"])
def test_synthetic_native_damage_preserves_siblings(store, tmp_path, damage):
    plan = synthetic_plan(tmp_path)
    write_synthetic(plan)
    target = Path(plan["attempt_directory"]) / plan["outputs"][2]["relative_path"]
    target.unlink()
    if damage == "changed":
        target.write_bytes(b"changed actual complete bytes despite opaque manifest absence text")
    elif damage == "symlink":
        target.symlink_to(Path(plan["attempt_directory"]) / plan["outputs"][0]["relative_path"])
    elif damage == "directory":
        target.mkdir()
    elif damage == "fifo":
        os.mkfifo(target)
    value = collect(store, plan)
    if damage == "changed":
        all_native_retained(value)
        assert Path(value["files"][2]["retained"]["path"]).read_bytes() == target.read_bytes()
        assert value["failures"] == []
    else:
        assert value["files"][2]["retained"] is None
        assert sum(row["retained"] is not None for row in value["files"]) == 7
        assert issues(value) == {("artifact_missing", "/files/effective_model")}


def test_synthetic_manifest_absence_does_not_suppress_actual_roles(store, tmp_path):
    plan = synthetic_plan(tmp_path)
    write_synthetic(plan)
    manifest = Path(plan["attempt_directory"]) / plan["outputs"][-1]["relative_path"]
    manifest.write_bytes(b'{"files":[{"role":"solution","state":"absent"}]}')
    all_native_retained(collect(store, plan))


@pytest.mark.parametrize("field", ["source_action_receipt_ref", "writer_closure_receipt_ref", "input_binding_file"])
def test_synthetic_missing_control_metadata_keeps_selected_identities(store, tmp_path, field):
    plan = synthetic_plan(tmp_path)
    write_synthetic(plan)
    kwargs = metadata(store)
    reference = "artifact_" + "e" * 64
    if field == "input_binding_file":
        kwargs[field] = {"artifact_ref": reference, "sha256": "e" * 64, "size_bytes": 7,
            "format": "flux_balance_input_binding_receipt_v1"}
    else:
        kwargs[field] = reference
    value = collect(store, plan, kwargs)
    all_native_retained(value)
    assert value[field] == kwargs[field]
    assert issues(value) == {("artifact_missing", "/" + field)}
    assert value["failures"][0]["detail_file"] is None


def test_synthetic_binding_metadata_conflict_keeps_siblings(store, tmp_path):
    plan = synthetic_plan(tmp_path)
    write_synthetic(plan)
    kwargs = metadata(store)
    kwargs["input_binding_file"]["size_bytes"] += 1
    value = collect(store, plan, kwargs)
    all_native_retained(value)
    assert issues(value) == {("artifact_identity_conflict", "/input_binding_file")}
    assert value["failures"][0]["detail_file"] is None


def add_selected_priors(store, plan):
    first = artifact(store, b"synthetic selected acquisition")
    second = artifact(store, b"synthetic selected bound")
    job = plan["requested_job"]["native_flux_balance"]
    job["model_input"]["acquisition_receipt_file"] = first
    bound = {"kind": "finite", "value": 0.0, "native_token": "0", "float_hex": "0x0.0p+0",
        "source": {"file": second, "pointer": "/lower"}}
    job["constraints"] = [{"reaction_id": "SYNTHETIC", "lower": bound, "upper": deepcopy(bound)},
        {"reaction_id": "REPEATED", "lower": {**deepcopy(bound), "source": {"file": first, "pointer": "/bound"}},
         "upper": deepcopy(bound)}]
    plan = update_request_digest(plan)
    rows = [{"file": f, "path": str(retained_native_file(store, f))} for f in (first, second)]
    return plan, rows


def test_synthetic_selected_prior_repeated_use_and_first_use_order(store, tmp_path):
    plan, rows = add_selected_priors(store, synthetic_plan(tmp_path))
    write_synthetic(plan)
    kwargs = {**metadata(store), "prior_sources": list(reversed(rows))}
    value = collect(store, plan, kwargs)
    assert value["prior_sources"] == rows
    assert value["failures"] == []
    assert validate_flux_balance_native_capture(value, original_plan=plan) == value


@pytest.mark.parametrize("damage", ["omitted", "missing", "corrupt", "wrong_store_path"])
def test_synthetic_failed_prior_keeps_native_siblings(store, tmp_path, damage):
    plan, rows = add_selected_priors(store, synthetic_plan(tmp_path))
    write_synthetic(plan)
    selected = deepcopy(rows)
    if damage == "omitted":
        selected.pop(0)
    elif damage == "missing":
        Path(rows[0]["path"]).unlink()
    elif damage == "corrupt":
        Path(rows[0]["path"]).write_bytes(b"corrupt")
    else:
        selected[0]["path"] = str(tmp_path / "other/artifacts" / rows[0]["file"]["sha256"][:2] / rows[0]["file"]["sha256"])
    value = collect(store, plan, {**metadata(store), "prior_sources": selected})
    all_native_retained(value)
    assert value["prior_sources"] == rows[1:]
    code = "artifact_missing" if damage in ("omitted", "missing") else "artifact_identity_conflict"
    assert issues(value) == {(code, "/prior_sources/0")}


@pytest.mark.parametrize("damage", ["duplicate", "unselected", "conflicting", "relative_path"])
def test_synthetic_prior_preflight_before_producer_access(store, tmp_path, damage, monkeypatch):
    plan, rows = add_selected_priors(store, synthetic_plan(tmp_path))
    write_synthetic(plan)
    if damage == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif damage == "unselected":
        f = artifact(store, b"synthetic unselected")
        rows.append({"file": f, "path": str(retained_native_file(store, f))})
    elif damage == "conflicting":
        rows[0]["file"]["size_bytes"] += 1
    else:
        rows[0]["path"] = "relative/artifacts"
    monkeypatch.setattr(capture, "capture_native_file", lambda *a, **k: pytest.fail("producer opened before preflight"))
    with pytest.raises(ValueError, match="^fba_capture_"):
        collect(store, plan, {**metadata(store), "prior_sources": rows})


@pytest.mark.parametrize("v2,environment", [(False, False), (False, True), (True, False), (True, True)])
def test_synthetic_versioned_environment_control(store, tmp_path, v2, environment):
    plan = synthetic_plan(tmp_path, v2=v2)
    write_synthetic(plan, environment=environment)
    value = collect(store, plan)
    all_native_retained(value)
    expected = set()
    if v2 and not environment:
        expected.add(("artifact_missing", "/controls/environment"))
    elif environment and not v2:
        expected.add(("artifact_identity_conflict", "/controls/environment"))
    assert issues(value) == expected
    assert (value["controls"]["environment"] is not None) == environment


@pytest.mark.parametrize("started", [True, False, None])
def test_synthetic_missing_original_controls(store, tmp_path, started):
    plan = synthetic_plan(tmp_path)
    write_synthetic(plan)
    for name in (OWNER_FILENAME, STARTED_FILENAME):
        (Path(plan["attempt_directory"]) / name).unlink()
    value = collect(store, plan, {**metadata(store), "driver_started": started})
    all_native_retained(value)
    assert issues(value) == ({("artifact_missing", "/controls/owner"), ("artifact_missing", "/controls/started")}
        if started is True else set())


@pytest.mark.parametrize("damage", ["extra_key", "digest", "order", "role_format", "bool", "control_keys",
    "retained_path", "missing_qualification", "unverified_issue_file", "scientific_locator", "unlocated_issue"])
def test_synthetic_pure_validator_rejects_malformed_handoff(store, tmp_path, damage):
    plan = synthetic_plan(tmp_path)
    write_synthetic(plan)
    value = collect(store, plan)
    if damage == "extra_key": value["extra"] = None
    elif damage == "digest": value["original_plan_sha256"] = "0" * 64
    elif damage == "order": value["files"].reverse()
    elif damage == "role_format": value["files"][0]["retained"]["file"]["format"] = "other"
    elif damage == "bool": value["driver_started"] = 1
    elif damage == "control_keys": value["controls"]["solve_entered"] = None
    elif damage == "retained_path": value["files"][0]["retained"]["path"] += "/../x"
    elif damage == "missing_qualification": value["files"][0]["retained"] = None
    else:
        issue = {"code": "artifact_missing", "stage": "capture", "field": "/files/original_model", "detail_file": None,
            "source_row_index": None, "reaction_position": None, "metabolite_position": None,
            "variable_position": None, "constraint_position": None}
        if damage == "unverified_issue_file": issue["detail_file"] = value["input_binding_file"]
        elif damage == "unlocated_issue": issue["field"] = None
        else: issue["reaction_position"] = 0
        value["failures"].append(issue)
    with pytest.raises(ValueError, match="^fba_capture_"):
        validate_flux_balance_native_capture(value, original_plan=plan)


def test_synthetic_pure_validator_is_detached_no_store_or_file_read(store, tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path)
    write_synthetic(plan)
    value = collect(store, plan)
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("pure validator opened a path"))
    checked = validate_flux_balance_native_capture(value, original_plan=plan)
    checked["files"][0]["retained"]["file"]["format"] = "mutated copy"
    assert value["files"][0]["retained"]["file"]["format"] == "sbml"


def test_synthetic_programming_error_is_not_native_absence(store, tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path)
    write_synthetic(plan)
    def broken(*a, **k):
        raise RuntimeError("synthetic programming defect")
    monkeypatch.setattr(capture, "capture_native_file", broken)
    with pytest.raises(RuntimeError, match="synthetic programming defect"):
        collect(store, plan)


def test_synthetic_original_plan_error_is_stable_before_producer_access(store, tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path)
    plan["extra"] = None
    monkeypatch.setattr(capture, "capture_native_file", lambda *a, **k: pytest.fail("invalid plan opened producer"))
    with pytest.raises(ValueError, match="^fba_capture_original_plan_invalid$"):
        collect(store, plan)


def test_synthetic_retained_storage_conflict_is_located_and_preserves_siblings(store, tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path)
    write_synthetic(plan)
    original = capture.capture_native_file
    def broken(*a, **k):
        if k["relative_path"] == plan["outputs"][2]["relative_path"]:
            raise NativeFileCaptureError("retained_artifact_mismatch")
        return original(*a, **k)
    monkeypatch.setattr(capture, "capture_native_file", broken)
    value = collect(store, plan)
    assert sum(row["retained"] is not None for row in value["files"]) == 7
    assert issues(value) == {("artifact_identity_conflict", "/files/effective_model")}
