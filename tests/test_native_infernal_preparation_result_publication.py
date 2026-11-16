"""Preparation custody, real bounded grading, typed projection and offline replay.

Four original252 captures are reused unchanged. Additional tiny native jobs use
the actual251 reservation/driver and existing native_lifecycle under local_jobs.
Malformed cases are explicitly synthetic mutations, never native measurements.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.library import native_infernal_preparation_acquisition as acquisition
from gene_annotation_episode.episodic_workflow.root.library import native_infernal_preparation_result_publication as publication
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest as digest
from gene_annotation_episode.episodic_workflow.root.library.native_infernal_preparation_contracts import requested_job_from_infernal_preparation
from gene_annotation_episode.episodic_workflow.root.library.native_infernal_preparation_local import prepare_local_infernal_preparation
from gene_annotation_episode.episodic_workflow.root.a101.practical_execution_state import _immutable
from gene_annotation_episode.state import Store

from test_native_infernal_preparation_result_worker import ROOT, forbidden, selector


POLICY = LocalJobPolicy(5 * 1024 ** 3, 4 * 1024 ** 3)
COMPILED_INDEX = json.loads((ROOT / "gene_annotation_episode/episodic_workflow/root/a107/tests/fixtures/infernal_preparation/compiled/NATIVE_COMPILED_INDEX_001.json").read_bytes())


def source(store, bundle, capture, prepared):
    return acquisition.publish_original_source(store, bundle=bundle, capture=capture, prepared=prepared)


def selected(store, tmp_path, bundle, capture, prepared, selection=None):
    ref = source(store, bundle, capture, prepared)
    result = publication.publish_selected_preparation_result(store, source_ref=ref, prepared=prepared,
        selector=selection or selector(), directory=tmp_path / "selection", policy=POLICY)
    return ref, result


def full(store, prepared):
    return json.loads(store.get_artifact(prepared["grading_artifact_ref"]))


def native_case(tmp_path, program, mode, *, change=None):
    indexed = next(r for r in COMPILED_INDEX["cases"] if (r["program"], r["mode"]) == (program, mode))
    raw = (ROOT / indexed["request_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == indexed["request_sha256"]
    job = json.loads(raw)
    if change:
        change(job)
    request = requested_job_from_infernal_preparation(job)
    assignment = {"workspace": str(tmp_path), "resource_kind": "local", "resource_id": "local",
                  "requested_job": request}
    state = SimpleNamespace(assignment=assignment, run_id="publication254", episode_id="selected-local-child")
    operation = "actual-" + program + "-" + mode
    root = tmp_path / ".episode-operations" / digest({"run": state.run_id, "episode": state.episode_id}) / digest(operation)
    root.mkdir(parents=True)
    handle = prepare_local_infernal_preparation(state, operation, root=root, policy=POLICY)
    native_lifecycle.start_prepared(handle)
    actual = native_lifecycle.wait_job(handle)
    _immutable(tmp_path / "native-receipt.json", {"returncode": actual.returncode, "metadata": actual.metadata})
    plan = json.loads((root / "infernal-preparation-plan.json").read_bytes())
    bundle = json.loads((Path(plan["attempt_directory"]) / "bundle.json").read_bytes())
    target = {"version": "execution_target_v1", "handle": "source_original_handoff254", "run_id": state.run_id,
        "origin_episode_id": state.episode_id, "resource_kind": "local", "resource_id": "local",
        "execution_id": str(handle.path), "request_sha256": digest(request), "assignment": assignment, "scope": {}}
    _immutable(tmp_path / "execution-target.json", target)
    return target, plan, bundle


def capture_and_grade(store, tmp_path, target):
    capture_directory = tmp_path / "capture"
    capture = acquisition.capture_local_bundle(store, target=target, directory=capture_directory)
    assert capture["bundle_validated"], capture
    prepared = publication.prepare_native_infernal_preparation_grading(store, target=target, capture=capture,
        capture_directory=capture_directory, directory=tmp_path / "grading", policy=POLICY)
    return capture, prepared


def test_missing_capture_is_structured_prerequisite_and_never_acquires(tmp_path, monkeypatch):
    monkeypatch.setattr(publication, "capture_local_bundle", forbidden)
    monkeypatch.setattr(publication, "run_local_job", forbidden)
    with Store(tmp_path / "store") as store:
        result = publication.prepare_native_infernal_preparation_grading(store, target={}, capture={},
            capture_directory=tmp_path / "missing", directory=tmp_path / "grading", policy=POLICY)
        assert not result["graded"] and result["bundle_artifact_ref"] is None
        assert result["failures"] == [{"stage": "prerequisite", "code": "native_infernal_preparation_completed_capture_required", "record_key": None}]
        assert publication.prepare_native_infernal_preparation_grading(store, target={}, capture={},
            capture_directory=tmp_path / "missing", directory=tmp_path / "grading", policy=POLICY) == result
