"""The new preparation reservation retains original lifecycle identity and limits."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest
from gene_annotation_episode.native_infernal_preparation_driver import OWNER_NAME
from gene_annotation_episode.native_infernal_preparation_local import (
    local_infernal_preparation_plan, prepare_local_infernal_preparation,
)
from gene_annotation_episode.practical_execution_state import _immutable
from test_native_infernal_preparation_driver import POLICY, make_plan, native_job, synthetic_plan


def local_state(tmp_path):
    plan = synthetic_plan(tmp_path)
    state = SimpleNamespace(run_id="run251", episode_id="local-child251", assignment={
        "requested_job": plan["requested_job"], "workspace": str(tmp_path),
        "resource_kind": "local", "resource_id": "local251"})
    operation = "selected-preparation"
    root = tmp_path / ".episode-operations" / native_infernal_digest({
        "run": state.run_id, "episode": state.episode_id}) / native_infernal_digest(operation)
    root.mkdir(parents=True)
    return state, operation, root


def test_reservation_does_not_dispatch_and_preserves_original_policy(tmp_path, monkeypatch):
    state, operation, root = local_state(tmp_path)
    for function in ("start_prepared", "start_job", "resume_start", "status", "cancel"):
        monkeypatch.setattr(native, function, lambda *a, **k: pytest.fail("reservation performed native lifecycle work"))
    handle = prepare_local_infernal_preparation(state, operation, root=root, policy=POLICY)
    assert handle.read()["stage"] == "prepared"
    assert handle.read()["metadata"]["policy"] == POLICY.to_dict()
    assert not (root / "infernal-preparation-attempt").exists()
    assert prepare_local_infernal_preparation(state, operation, root=root, policy=POLICY) == handle
    plan = local_infernal_preparation_plan(state.assignment, str(handle.path))
    assert plan["requested_job"] == state.assignment["requested_job"]
    assert plan["identity"]["run_id"] == state.run_id and plan["identity"]["episode_id"] == state.episode_id
    assert plan["policy"] == {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3, "wall_seconds": None}
    invoke = json.loads((root / "invoke.json").read_bytes())
    assert invoke == {"cwd": plan["attempt_directory"], "argv": state.assignment["requested_job"]["argv"],
        "environment": state.assignment["requested_job"]["environment"],
        "native_infernal_preparation_plan": "infernal-preparation-plan.json"}


@pytest.mark.parametrize("fault", ["command", "policy", "resource", "resource_kind", "workspace", "invoke", "request", "request_rehashed", "owner", "paths", "stdout", "attempt", "operation", "job"])
def test_reconstruction_rejects_original_reservation_conflicts(tmp_path, fault):
    state, operation, root = local_state(tmp_path)
    handle = prepare_local_infernal_preparation(state, operation, root=root, policy=POLICY)
    body, assignment = handle.read(), deepcopy(state.assignment)
    if fault == "command":
        body["command"] = ["/bin/true"]
    elif fault == "policy":
        body["metadata"]["policy"]["memory_bytes"] += 1
    elif fault == "resource":
        assignment["resource_id"] = "changed"
    elif fault == "resource_kind":
        assignment["resource_kind"] = "hpc"
    elif fault == "workspace":
        assignment["workspace"] = str(tmp_path / "changed")
    elif fault == "invoke":
        path = root / "invoke.json"
        record = json.loads(path.read_bytes())
        record["argv"] = ["/bin/true"]
        path.unlink()
        _immutable(path, record)
    elif fault.startswith("request"):
        path = Path(body["paths"]["request"])
        request = json.loads(path.read_bytes())
        request["env"]["INFERNAL_NCPU"] = "9"
        path.write_text(json.dumps(request))
        if fault == "request_rehashed":
            body["request_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif fault == "owner":
        attempt = root / "infernal-preparation-attempt"
        attempt.mkdir()
        (attempt / OWNER_NAME).write_text("{}\n")
    elif fault == "paths":
        body["paths"]["result"] = str(tmp_path / "outside-result")
    elif fault == "stdout":
        body["stdout"] = str(root / "changed-stdout")
    elif fault in {"attempt", "operation"}:
        path = root / "infernal-preparation-plan.json"
        plan = json.loads(path.read_bytes())
        if fault == "attempt":
            plan["attempt_directory"] = str(root / "changed-attempt")
        else:
            plan["identity"]["operation_key"] = "other"
            plan["identity"]["attempt_id"] = native_infernal_digest("other")
        path.unlink()
        _immutable(path, plan)
    else:
        assignment["requested_job"]["argv"][0] = "/bin/true"
    handle.path.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        local_infernal_preparation_plan(assignment, str(handle.path))


def test_original_policy_cannot_be_replaced_on_repeated_preparation(tmp_path):
    from gene_annotation_episode.local_jobs import LocalJobPolicy
    state, operation, root = local_state(tmp_path)
    prepare_local_infernal_preparation(state, operation, root=root, policy=POLICY)
    with pytest.raises(ValueError, match="immutable_record_conflict"):
        prepare_local_infernal_preparation(state, operation, root=root,
            policy=LocalJobPolicy(POLICY.memory_bytes // 2, POLICY.scratch_bytes, None))


@pytest.mark.parametrize("attempt_exists", [False, True])
def test_lost_reservation_cannot_create_a_second_identity(tmp_path, monkeypatch, attempt_exists):
    state, operation, root = local_state(tmp_path)
    handle = prepare_local_infernal_preparation(state, operation, root=root, policy=POLICY)
    handle.path.unlink()
    if attempt_exists:
        (root / "infernal-preparation-attempt").mkdir()
    monkeypatch.setattr(native, "prepare_job", lambda *a, **k: pytest.fail("re-reserved uncertain attempt"))
    with pytest.raises(ValueError, match="missing_reservation_execution_uncertain"):
        prepare_local_infernal_preparation(state, operation, root=root, policy=POLICY)


def test_wrong_root_and_missing_resource_are_rejected_without_reservation(tmp_path):
    state, operation, root = local_state(tmp_path)
    with pytest.raises(ValueError, match="attempt_directory_conflict"):
        prepare_local_infernal_preparation(state, operation, root=tmp_path, policy=POLICY)
    state.assignment["resource_id"] = None
    with pytest.raises(ValueError, match="resource_identity_required"):
        prepare_local_infernal_preparation(state, operation, root=root, policy=POLICY)
    assert not (root / "native.json").exists()


@pytest.mark.parametrize("case", ["consensus", "calibrate", "merge_scores", "calibration_failure"])
def test_actual_reservation_dispatch_and_cli_bundle_through_existing_lifecycle(tmp_path, case):
    from gene_annotation_episode.native_infernal_preparation_driver import validate_preparation_bundle_files
    state, operation, root = local_state(tmp_path)
    selected = native_job("cmemit", "consensus") if case == "consensus" else native_job(
        "cmcalibrate", "calibrate" if case == "calibration_failure" else case)
    if case == "calibration_failure":
        selected["options"] = ["-L", "0.01", "--tailp", "0.00000001", "--seed", "181", "--cpu", "1", "--noforecast"]
    state.assignment["requested_job"] = make_plan(tmp_path, selected)["requested_job"]
    handle = prepare_local_infernal_preparation(state, operation, root=root, policy=POLICY)
    native.start_prepared(handle)
    result = native.wait_job(handle)
    (tmp_path / "native-lifecycle-receipt.json").write_text(json.dumps({"returncode": result.returncode,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "metadata": result.metadata}, indent=2) + "\n")
    assert result.returncode == (1 if case == "calibration_failure" else 0), result.stderr_path.read_text()
    assert result.metadata["verified_cgroup"]["memory_max"] == POLICY.memory_bytes
    assert result.metadata["verified_cgroup"]["runtime_max"] == "infinity"
    plan = local_infernal_preparation_plan(state.assignment, str(handle.path))
    (tmp_path / "assignment.json").write_text(json.dumps(state.assignment, indent=2) + "\n")
    identity = plan["identity"]
    target = {"version": "execution_target_v1", "handle": "source_original_handoff_251",
        "run_id": identity["run_id"], "origin_episode_id": identity["episode_id"],
        "resource_kind": "local", "resource_id": identity["resource_id"],
        "execution_id": identity["execution_id"], "request_sha256": identity["requested_job_sha256"],
        "assignment": state.assignment, "scope": {}}
    (tmp_path / "execution-target.json").write_text(json.dumps(target, indent=2) + "\n")
    attempt = Path(plan["attempt_directory"])
    bundle = validate_preparation_bundle_files(json.loads((attempt / "bundle.json").read_bytes()), attempt)
    if case == "calibration_failure":
        assert bundle["returncode"] != 0
        assert any(a["role"] == "calibrated_models" and a["size_bytes"] > 0 for a in bundle["artifacts"])
    else:
        assert bundle["returncode"] == 0 and bundle["failures"] == []
    if case == "consensus":
        assert "GCGCaaAAGCGC" in (attempt / next(a["relative_path"] for a in bundle["artifacts"] if a["role"] == "generated_sequences")).read_text()
    assert native.collect(handle).returncode == result.returncode
