"""Real host/state admission over explicitly engineered run-local controls.

The requested job and control templates come from retained SR fixtures. The
new assignment, two-field policy, paths and reservation below are test records,
not an actual saved native success. No original fixture is changed or reopened.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.local_job_policy import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.library import native_lumpy_execution as worker
from gene_annotation_episode.episodic_workflow.root.library import native_lumpy_host as host
from gene_annotation_episode.episodic_workflow.root.execution_job_submission.local_job_execution.resource_state_records import PracticalState


FIXTURES = Path(__file__).parent / "fixtures" / "lumpy_saved_driver_identity"


def retained(name):
    return json.loads((FIXTURES / name).read_bytes())


def real_pending_state(tmp_path):
    requested = deepcopy(retained("plan.json")["requested_job"])
    assignment = dict(version="practical_assignment_v1", assignment_id="engineered-lumpy-host",
        resource_kind="local", resource_id="local", workspace=str(tmp_path),
        endpoint="usable_handoff", requested_job=requested,
        progress_requirements=[dict(key="handoff", credit=1,
            predicate=dict(kind="requested_job_handoff"))], completion_keys=["handoff"],
        initial_context=dict(revision=0, cwd=str(tmp_path), environment={}),
        inventory_snapshot={}, constraints=deepcopy(worker.POLICY))
    state = PracticalState(tmp_path / "state", "engineered-lumpy-host-run", "local-child", assignment)
    operation = "selected-start"
    state.begin(operation, "practical.job.start", {})
    root = tmp_path / ".episode-operations" / worker.digest(
        dict(run=state.run_id, episode=state.episode_id)) / worker.digest(operation)
    return state, operation, root


def forbidden(*_args, **_kwargs):
    pytest.fail("host identity control reached a new control write or native reservation")


def test_fresh_legacy_reservation_rejects_before_controls_or_native_port(tmp_path, monkeypatch):
    state, operation, root = real_pending_state(tmp_path)
    monkeypatch.setattr(host.native, "prepare_job", forbidden)
    monkeypatch.setattr(host, "_immutable", forbidden)
    with pytest.raises(ValueError, match="^selected_worker_identity_conflict$"):
        host.prepare_local_lumpy(state, operation, root=root, policy=LocalJobPolicy(**worker.POLICY))
    assert list(root.iterdir()) == []
    assert state._load()[4]["operation_key"] == operation


def test_existing_legacy_handle_uses_real_readback_without_new_reservation(tmp_path, monkeypatch):
    state, operation, root = real_pending_state(tmp_path)
    requested = state.assignment["requested_job"]
    identity = dict(run_id=state.run_id, episode_id=state.episode_id, resource_id="local",
        execution_id=str(root / "native.json"), attempt_id=worker.digest(operation),
        operation_key=operation, requested_job_sha256=worker.digest(requested),
        assignment_sha256=worker.digest(state.assignment))
    plan = host.lumpy_plan(state.assignment, identity, policy=deepcopy(worker.POLICY))
    original_plan = retained("plan.json")
    old_root = str(Path(original_plan["identity"]["execution_id"]).parent)

    def relocate(value):
        if isinstance(value, dict):
            return {key: relocate(item) for key, item in value.items()}
        if isinstance(value, list):
            return [relocate(item) for item in value]
        if isinstance(value, str) and (value == old_root or value.startswith(old_root + "/")):
            return str(root) + value[len(old_root):]
        return value

    # These are derived, unexecuted control records. Preserve the original
    # supplied job/runtime identity while giving the test a real owned path.
    handle = relocate(retained("handle.json"))
    handle["metadata"]["policy"] = deepcopy(worker.POLICY)
    handle["metadata"].pop("verified_cgroup", None)
    handle["stage"] = "prepared"
    for name in ("started_at", "started_monotonic_ns", "boot_id"):
        handle.pop(name, None)
    request = relocate(retained("request.json"))
    request_raw = worker.canonical(request)
    handle["request_sha256"] = hashlib.sha256(request_raw).hexdigest()
    assert host.validate_lumpy_original_controls(plan, handle, request_raw) == plan
    root.mkdir(parents=True)
    files = {
        root / "native.json": worker.canonical(handle),
        root / worker.RUN_PLAN_FILENAME: worker.canonical(plan),
        root / "invoke.json": worker.canonical(dict(cwd=str(root), argv=requested["argv"],
            environment=requested["environment"], native_lumpy_plan=worker.RUN_PLAN_FILENAME)),
        Path(handle["paths"]["request"]): request_raw,
    }
    for path, raw in files.items():
        path.write_bytes(raw)
    monkeypatch.setattr(host.native, "prepare_job", forbidden)
    monkeypatch.setattr(host, "_immutable", forbidden)
    monkeypatch.setattr(host, "_no_dispatch", forbidden)
    assert host.read_local_lumpy_plan(state.assignment, str(root / "native.json")) == plan
    selected = host.prepare_local_lumpy(state, operation, root=root,
        policy=LocalJobPolicy(**worker.POLICY))
    assert selected.path == root / "native.json"
    assert {path: path.read_bytes() for path in files} == files
    assert not Path(plan["attempt_directory"]).exists()
