"""Bounded host reservation/capture checks, run only by root's bounded suite.

These execute real finite saved-sheet workers, without an original assay or
producer deployment. Full episode/scientific-parent delivery belongs to root.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import native_fluorescence_preparation as preparation
from gene_annotation_episode.fluorescence_execution_common import canonical, identity
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_fluorescence_contracts import POLICY
from gene_annotation_episode.native_fluorescence_storage import read_json
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.state import Store
from test_fluorescence_result_worker import saved_plan


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    root = tmp_path_factory.mktemp("fluorescence-bounded-worker")
    with Store(root / "store") as store:
        plan = saved_plan(store, root / "case")
        captured = preparation.prepare_fluorescence_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY))
        execution = read_json(retained_native_file(store, captured["execution_receipt_file"]))
        yield store, plan, captured, execution


def test_actual_bounded_worker_uses_real_stdlib_closure_and_captured_cells(prepared):
    store, plan, capture, execution = prepared
    assert capture["result"]["analysis_complete"] and capture["failures"] == []
    assert execution["returncode"] == 0 and execution["failure"] is None
    assert execution["intent"]["dependencies"] == []
    assert execution["metadata"]["verified_cgroup"] == dict(memory_max=21474836480, memory_swap_max=0,
        kill_mode="control-group", oom_policy="kill")
    assert [row["declared"]["relative_path"] for row in capture["outputs"]] == [
        "sheet.json", "calculations.json", "projection.json", "context.json", "diagnostics.json"]
    assert all(row["outcome"] == "verified" for row in capture["outputs"])
    for row in capture["outputs"]:
        retained_native_file(store, row["observed"])
    projection = read_json(retained_native_file(store, capture["outputs"][2]["observed"]))
    assert [row["value"] for row in projection["rows"]] == [.625, 62.5, 165, 150]
    request = execution["request_raw"].encode()
    assert identity(request, format="native_local_job_request") == execution["request_file"]
    # The lifecycle's exact JSON writer is not the control canonical writer.
    assert request != canonical(execution["request"]) + b"\n"


@pytest.mark.parametrize("change", ["command", "raw", "quiescent", "policy", "dependency_shape", "path", "plan", "boolean_exit", "swapped_inputs"])
def test_execution_validator_rejects_forged_control_relationships(prepared, change):
    _, plan, capture, original = prepared
    execution = deepcopy(original)
    if change == "command": execution["intent"]["command"][-1] = "/foreign/plan.json"
    elif change == "raw": execution["request_raw"] += " "
    elif change == "quiescent": execution["quiescent"] = False
    elif change == "policy": execution["metadata"]["verified_cgroup"]["memory_swap_max"] = 1
    elif change == "dependency_shape": execution["intent"]["dependencies"] = [{"name": "jsonschema", "version": "unknown", "requires": []}]
    elif change == "path": execution["handle"]["paths"]["result"] = "/outside/result"
    elif change == "plan": execution["plan_file"]["sha256"] = "0" * 64
    elif change == "boolean_exit": execution["returncode"] = False
    elif change == "swapped_inputs": execution["intent"]["plan"]["sheet"]["file"]["size_bytes"] += 1
    with pytest.raises(ValueError):
        preparation.validate_fluorescence_worker_execution(execution, plan=plan, plan_file=capture["plan_file"])


@pytest.mark.parametrize("change", ["declaration", "size", "outcome", "worker_result", "missing_result", "missing_failure"])
def test_prepared_capture_cannot_replace_worker_or_observed_artifacts(prepared, change):
    store, plan, original, _ = prepared
    capture = deepcopy(original)
    if change == "declaration": capture["outputs"][0]["declared"]["relative_path"] = "other.json"
    elif change == "size": capture["outputs"][0]["observed"]["size_bytes"] += 1
    elif change == "outcome": capture["outputs"][0]["outcome"] = "declared_absent"
    elif change == "worker_result": capture["result"]["native_binding"] = True
    elif change == "missing_result": capture.update(result=None, outputs=[])
    elif change == "missing_failure": capture["failures"] = [dict(code="worker_nonzero_exit", stage="worker", input_index=None, role=None)]
    with pytest.raises(ValueError): preparation.validate_prepared_fluorescence_worker(store, capture, plan=plan)


def test_closed_capture_replays_without_todays_runtime_or_resubmission(prepared, monkeypatch):
    store, plan, capture, _ = prepared
    root = Path(plan["directory"])
    for name in ("runtime", "source_snapshot"):
        shutil.rmtree(root / name)
    def forbidden(*args, **kwargs): pytest.fail("closed worker consulted current runtime or dispatched")
    monkeypatch.setattr(preparation, "_snapshot", forbidden)
    monkeypatch.setattr(preparation, "_verify_pins", forbidden)
    monkeypatch.setattr(preparation.native, "prepare_job", forbidden)
    assert preparation.prepare_fluorescence_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY)) == capture


def test_resumption_uses_original_handle_after_execution_before_capture(tmp_path, monkeypatch):
    class Interrupted(BaseException):
        pass
    with Store(tmp_path / "store") as store:
        plan = saved_plan(store, tmp_path / "case")
        wait = preparation.native.wait_job
        original_handle = []
        def interrupted(handle):
            original_handle.append(handle.read()["unit"])
            wait(handle)
            raise Interrupted()
        monkeypatch.setattr(preparation.native, "wait_job", interrupted)
        with pytest.raises(Interrupted):
            preparation.prepare_fluorescence_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY))
        root = Path(plan["directory"])
        before = (root / "worker-result.json").stat().st_mtime_ns
        monkeypatch.setattr(preparation.native, "wait_job", wait)
        monkeypatch.setattr(preparation.native, "prepare_job", lambda *a, **k: pytest.fail("duplicate reservation"))
        monkeypatch.setattr(preparation, "_snapshot", lambda *a, **k: pytest.fail("replacement worker closure"))
        capture = preparation.prepare_fluorescence_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY))
        execution = read_json(retained_native_file(store, capture["execution_receipt_file"]))
        assert execution["handle"]["unit"] == original_handle[0]
        assert (root / "worker-result.json").stat().st_mtime_ns == before


def test_missing_worker_result_keeps_actual_execution_and_logs(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        plan = saved_plan(store, tmp_path / "case")
        wait = preparation.native.wait_job
        def remove_result(handle):
            result = wait(handle)
            (Path(plan["directory"]) / "worker-result.json").unlink()
            return result
        monkeypatch.setattr(preparation.native, "wait_job", remove_result)
        capture = preparation.prepare_fluorescence_result_worker(store, plan=plan, policy=LocalJobPolicy(**POLICY))
        assert capture["result"] is None and capture["outputs"] == [] and capture["worker_result_file"] is None
        assert capture["failures"] == [dict(code="worker_output_unavailable", stage="worker", input_index=None, role="worker_result")]
        execution = read_json(retained_native_file(store, capture["execution_receipt_file"]))
        assert execution["returncode"] == 0
        assert retained_native_file(store, execution["stdout_file"]).is_file()
        assert retained_native_file(store, execution["stderr_file"]).is_file()


def test_dependency_discovery_does_not_invent_scientific_packages(tmp_path):
    path = tmp_path / "pure.py"
    path.write_text("import json\nfrom pathlib import Path\n")
    assert preparation._dependencies({"pure": path}) == []
    path.write_text("import scipy\n")
    with pytest.raises(ValueError, match="dependency_unbound"):
        preparation._dependencies({"not_pure": path})
