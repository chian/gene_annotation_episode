"""Reservation, exact reopening, and actual child-selected local dispatch."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest
from gene_annotation_episode.native_hmmer_preparation_contracts import requested_job_from_hmmer_preparation
from gene_annotation_episode.native_hmmer_preparation_driver import OWNER_NAME, validate_preparation_bundle_files
from gene_annotation_episode.native_hmmer_preparation_local import (
    ATTEMPT_NAME, PLAN_NAME, local_hmmer_preparation_plan, prepare_local_hmmer_preparation,
)
from gene_annotation_episode.practical_execution_state import _immutable
from test_native_hmmer_preparation_contracts import job
from test_native_hmmer_preparation_driver import POLICY


def local_state(tmp_path):
    state = SimpleNamespace(run_id="run267", episode_id="local-child267", assignment={
        "requested_job": requested_job_from_hmmer_preparation(job("hmmemit", "consensus_simple")),
        "workspace": str(tmp_path), "resource_kind": "local", "resource_id": "local267"})
    operation = "selected-preparation"
    root = tmp_path / ".episode-operations" / native_infernal_digest({"run": state.run_id, "episode": state.episode_id}) / native_infernal_digest(operation)
    root.mkdir(parents=True)
    return state, operation, root


def test_reservation_only_and_exact_reopening(tmp_path, monkeypatch):
    state, operation, root = local_state(tmp_path)
    for name in ("start_prepared", "start_job", "resume_start", "status", "cancel"):
        monkeypatch.setattr(native, name, lambda *a, **k: pytest.fail("reservation dispatched work"))
    handle = prepare_local_hmmer_preparation(state, operation, root=root, policy=POLICY)
    assert handle.read()["stage"] == "prepared"
    assert handle.read()["metadata"]["policy"] == POLICY.to_dict()
    assert not (root / ATTEMPT_NAME).exists()
    assert prepare_local_hmmer_preparation(state, operation, root=root, policy=POLICY) == handle
    plan = local_hmmer_preparation_plan(state.assignment, str(handle.path))
    assert plan["identity"]["episode_id"] == state.episode_id
    assert plan["requested_job"] == state.assignment["requested_job"]


@pytest.mark.parametrize("fault", ["command", "policy", "resource", "workspace", "invoke", "request", "rehashed_request", "owner", "stdout", "path", "attempt"])
def test_original_reservation_conflicts_reject(tmp_path, fault):
    state, operation, root = local_state(tmp_path)
    handle = prepare_local_hmmer_preparation(state, operation, root=root, policy=POLICY)
    body, assignment = handle.read(), deepcopy(state.assignment)
    if fault == "command":
        body["command"] = ["/bin/true"]
    elif fault == "policy":
        body["metadata"]["policy"]["scratch_bytes"] += 1
    elif fault == "resource":
        assignment["resource_id"] = "other"
    elif fault == "workspace":
        assignment["workspace"] = str(tmp_path / "other")
    elif fault == "invoke":
        path = root / "invoke.json"
        item = json.loads(path.read_bytes())
        item["argv"] = ["/bin/true"]
        path.unlink()
        _immutable(path, item)
    elif fault in {"request", "rehashed_request"}:
        path = Path(body["paths"]["request"])
        item = json.loads(path.read_bytes())
        item["env"]["HMMER_NCPU"] = "9"
        path.write_text(json.dumps(item))
        if fault == "rehashed_request":
            body["request_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif fault == "owner":
        (root / ATTEMPT_NAME).mkdir()
        (root / ATTEMPT_NAME / OWNER_NAME).write_text("{}\n")
    elif fault == "stdout":
        body["stdout"] = str(root / "other-stdout")
    elif fault == "path":
        body["paths"]["result"] = str(tmp_path / "outside")
    else:
        path = root / PLAN_NAME
        item = json.loads(path.read_bytes())
        item["attempt_directory"] = str(root / "other")
        path.unlink()
        _immutable(path, item)
    handle.path.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        local_hmmer_preparation_plan(assignment, str(handle.path))


def test_missing_reservation_never_creates_replacement(tmp_path, monkeypatch):
    state, operation, root = local_state(tmp_path)
    handle = prepare_local_hmmer_preparation(state, operation, root=root, policy=POLICY)
    handle.path.unlink()
    monkeypatch.setattr(native, "prepare_job", lambda *a, **k: pytest.fail("re-reserved uncertain work"))
    with pytest.raises(ValueError, match="missing_reservation_execution_uncertain"):
        prepare_local_hmmer_preparation(state, operation, root=root, policy=POLICY)


def test_actual_reservation_cli_dispatch_and_original_bundle(tmp_path):
    state, operation, root = local_state(tmp_path)
    handle = prepare_local_hmmer_preparation(state, operation, root=root, policy=POLICY)
    native.start_prepared(handle)
    result = native.wait_job(handle)
    (tmp_path / "native-lifecycle-receipt.json").write_text(json.dumps({"returncode": result.returncode,
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path), "metadata": result.metadata}, indent=2) + "\n")
    assert result.returncode == 0, result.stderr_path.read_text()
    plan = local_hmmer_preparation_plan(state.assignment, str(handle.path))
    (tmp_path / "assignment.json").write_text(json.dumps(state.assignment, indent=2) + "\n")
    attempt = Path(plan["attempt_directory"])
    bundle = validate_preparation_bundle_files(json.loads((attempt / "bundle.json").read_bytes()), attempt)
    assert bundle["returncode"] == 0 and bundle["failures"] == []
    assert result.metadata["verified_cgroup"]["memory_max"] == 20 * 1024**3
    assert result.metadata["verified_cgroup"]["runtime_max"] == "infinity"
    assert native.collect(handle).returncode == 0
