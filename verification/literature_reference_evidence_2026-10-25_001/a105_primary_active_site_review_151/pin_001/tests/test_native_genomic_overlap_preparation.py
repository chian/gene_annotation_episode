"""434: actual Store custody and real bounded finite-worker reservations.

Native inputs are retained packet427/432 fixtures. Source/action/closure labels
are deliberately synthetic and grant no episode authority. Failure injection is
marked separately; no test executes bedtools or duplicates the huge killed job.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket

import pytest

from gene_annotation_episode import native_genomic_overlap_preparation as preparation
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_file_capture import (
    NativeFileCaptureError, capture_native_file, capture_declared_native_files,
    retained_native_file,
)
from gene_annotation_episode.native_genomic_overlap_contracts import genomic_overlap_output_files
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "verification/tool_graders_genomic_overlap_result_worker_2026-10-27_432/fixtures"
POLICY = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def read(store, identity):
    return json.loads(retained_native_file(store, identity).read_bytes())


def deny(*args, **kwargs):
    pytest.fail("unexpected producer/source/network/calculation/lifecycle access")


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "store") as value:
        yield value


def native_plan(store, tmp_path, case="three"):
    fixture = FIXTURES / case
    original = json.loads((fixture / "plan.json").read_bytes())
    batch_file = capture_native_file(store, directory=str(fixture / "native"), relative_path="bundle.json",
                                     format="genomic_overlap_native_batch_v1")
    batch = read(store, batch_file)
    request = original["requested_job"]["native_genomic_overlap"]["request"]
    captures = capture_declared_native_files(store, directory=str(fixture / "native"),
        declarations=[row["declaration"] for row in batch["files"]])
    files = []
    for spec, capture in zip(genomic_overlap_output_files(request)[:-1], captures):
        observed = capture["observed"]
        files.append({"specification": spec, "declaration_source": "batch", "capture": capture,
            "retained": {"file": observed, "path": str(retained_native_file(store, observed))} if observed else None})
    selector = {"version": "genomic_overlap_result_selector_v1", "mode": "native_result",
        "comparison_keys": [pair["comparison_key"] for pair in request["comparisons"]], "saved_sheet_file": None,
        "parameters": {"version": "genomic_overlap_calculation_parameters_v1", "minimum_overlap_bp": 1,
            "minimum_a_fraction": {"numerator": 0, "denominator": 1},
            "minimum_b_fraction": {"numerator": 0, "denominator": 1}},
        "projection": {"kind": "pair_metrics", "offset": 0, "limit": 100,
            "measurement_fields": ["unfiltered.jaccard_bp", "selected.selected_pair_count"], "occurrence_keys": []}}
    return preparation.build_native_genomic_overlap_worker_plan(directory=str(tmp_path / "worker"),
        original_plan=original, batch={"file": batch_file, "path": str(retained_native_file(store, batch_file))},
        files=files, selector=selector, source_action_receipt_ref="synthetic-test-selected-action",
        writer_closure_receipt_ref="synthetic-test-original-writer-closure", driver_state="sealed_batch", failures=[])


def saved_plan(store, tmp_path, sheet, selector, *, name="saved", minimum=4):
    selector = deepcopy(selector)
    selector.update(mode="saved_sheet_recalculation", saved_sheet_file=sheet)
    selector["parameters"]["minimum_overlap_bp"] = minimum
    return preparation.build_saved_genomic_overlap_worker_plan(directory=str(tmp_path / name),
        sheet={"file": sheet, "path": str(retained_native_file(store, sheet))}, selector=selector)


def completed(store, tmp_path, case="three"):
    plan = native_plan(store, tmp_path, case)
    return plan, preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)


def recapture(store, plan, prepared):
    return preparation.capture_genomic_overlap_worker_outputs(store, directory=plan["directory"],
        plan_file=prepared["plan_file"], execution_receipt_file=prepared["execution_receipt_file"])


def overwrite(path, raw):
    path.chmod(0o600)
    path.write_bytes(raw)


def test_builders_detach_validate_without_io(store, tmp_path, monkeypatch):
    plan = native_plan(store, tmp_path, "empty_c")
    retained = [row["retained"] for row in plan["files"] if row["retained"]]
    assert any(a["path"] == b["path"] and a["file"]["format"] != b["file"]["format"]
               for a in retained for b in retained)
    arguments = {key: value for key, value in plan.items() if key not in ("version", "mode")}
    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", deny)
        patch.setattr(os, "open", deny)
        output = preparation.build_native_genomic_overlap_worker_plan(**arguments)
    assert output == plan and output is not plan and output["files"] is not plan["files"]
    output["selector"]["parameters"]["minimum_overlap_bp"] = 9
    assert plan["selector"]["parameters"]["minimum_overlap_bp"] == 1
    with pytest.raises(ValueError):
        preparation.build_native_genomic_overlap_worker_plan(**{**arguments, "files": plan["files"][::-1]})


def test_actual_native_worker_snapshot_canonical_and_all_hash_joins(store, tmp_path):
    plan, prepared = completed(store, tmp_path)
    assert set(prepared) == set(preparation.WorkerCapture.__annotations__)
    assert prepared["result"]["state"] == "produced" and prepared["failures"] == []
    execution = read(store, prepared["execution_receipt_file"])
    assert set(execution) == set(preparation.WorkerExecution.__annotations__)
    assert execution["outcome"] == "returned" and execution["returncode"] == 0
    assert execution["metadata"]["policy"] == POLICY.to_dict()
    assert execution["metadata"]["verified_cgroup"] == {"memory_max": POLICY.memory_bytes,
        "memory_swap_max": 0, "runtime_max": "infinity", "kill_mode": "control-group", "oom_policy": "kill"}
    handle = read(store, execution["handle_file"])
    request = read(store, execution["request_file"])
    assert execution["stdout_file"]["artifact_ref"] == execution["stderr_file"]["artifact_ref"]
    assert execution["stdout_file"]["format"] != execution["stderr_file"]["format"]
    assert handle["command"] == request["command"] == [execution["interpreter"]["path"], "-B", "-S", "-m",
        "gene_annotation_episode.genomic_overlap_result_worker", plan["directory"] + "/plan.json"]
    assert execution["request_file"]["sha256"] == handle["request_sha256"]
    assert request["env"]["PYTHONPATH"].split(os.pathsep)[0] == plan["directory"] + "/source_snapshot"
    assert request["env"]["PYTHONNOUSERSITE"] == "1" and request["env"]["PYTHONHOME"]
    for pin in [*execution["source_pins"], execution["interpreter"]]:
        path = Path(pin["path"])
        assert path.stat().st_mode & 0o222 == 0
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin["sha256"]
        artifact = store.path / "artifacts" / pin["sha256"][:2] / pin["sha256"]
        assert artifact.stat().st_ino != path.stat().st_ino
        assert artifact.stat().st_mode & 0o777 == 0o600
    sheet, components, projection, diagnostics = [read(store, row["observed"]) for row in prepared["outputs"]]
    assert [pair["unfiltered"]["jaccard_bp"]["value"] for pair in components["pairs"]] == pytest.approx([1/3, 1/4, 2/13])
    assert [pair["unfiltered"]["pairwise_overlap_bp_sum"] for pair in components["pairs"]] == [8, 5, 2]
    assert components["source_sheet_sha256"] == projection["source_sheet_sha256"] == prepared["outputs"][0]["observed"]["sha256"]
    assert diagnostics["mode"] == "native_result" and sheet["request"] == plan["original_plan"]["requested_job"]["native_genomic_overlap"]["request"]
    for identity in [prepared["plan_file"], prepared["execution_receipt_file"], prepared["worker_result_file"],
                     *(row["observed"] for row in prepared["outputs"])]:
        raw = retained_native_file(store, identity).read_bytes()
        assert not raw.endswith(b"\n") and canonical(json.loads(raw)) == raw
    (tmp_path / "ACTUAL_WORKER_EXECUTION.json").write_bytes(canonical({"plan": plan, "capture": prepared,
        "execution": execution, "projection": projection, "source_authority": "synthetic test labels only"}))


def test_saved_recalculation_only_received_sheet_and_changed_parameters(store, tmp_path, monkeypatch):
    native, first = completed(store, tmp_path)
    sheet = first["outputs"][0]["observed"]
    plan = saved_plan(store, tmp_path, sheet, native["selector"])
    # The real subprocess cannot recover through earlier retained native bytes:
    # remove every native operand from this test Store, retaining only the sheet.
    previous = [native["batch"], *(row["retained"] for row in native["files"])]
    paths = {retained_native_file(store, row["file"]) for row in previous if row is not None}
    nonempty_paths = {path for path in paths if path.stat().st_size}
    assert retained_native_file(store, sheet) not in paths
    for path in paths:
        path.unlink()
    with monkeypatch.context() as patch:
        patch.setattr(socket, "create_connection", deny)
        # These native APIs must not participate in a saved-sheet calculation.
        from gene_annotation_episode import native_genomic_overlap_local, native_genomic_overlap_driver
        patch.setattr(native_genomic_overlap_local, "local_genomic_overlap_plan", deny)
        patch.setattr(native_genomic_overlap_driver, "main", deny)
        second = preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    assert second["outputs"][0]["observed"] == sheet
    components = read(store, second["outputs"][1]["observed"])
    assert [pair["selected"]["selected_pair_count"] for pair in components["pairs"]] == [1, 1, 0]
    assert [pair["unfiltered"]["pairwise_overlap_bp_sum"] for pair in components["pairs"]] == [8, 5, 2]
    assert read(store, second["outputs"][3]["observed"])["sets"] == []
    # New empty worker logs legitimately recreate the Store's shared empty-byte
    # artifact; that is not native source reacquisition.
    assert all(not path.exists() for path in nonempty_paths)
    (tmp_path / "SAVED_RECALCULATION.json").write_bytes(canonical(second))


def test_completed_replay_no_current_sources_producers_or_lifecycle(store, tmp_path, monkeypatch):
    plan, prepared = completed(store, tmp_path)
    raw = (Path(plan["directory"]) / "prepared.json").read_bytes()
    for name in ("source_snapshot", "runtime"):
        root = Path(plan["directory"]) / name
        for path in [root, *(p for p in root.rglob("*") if p.is_dir())]:
            path.chmod(0o755)
        shutil.rmtree(root)
    for name in ("_snapshot", "_run", "_inputs", "capture_native_file", "capture_declared_native_files"):
        monkeypatch.setattr(preparation, name, deny)
    monkeypatch.setattr(preparation.native_lifecycle, "status", deny)
    monkeypatch.setattr(preparation.native_lifecycle, "resume_start", deny)
    assert preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY) == prepared
    assert preparation.validate_prepared_genomic_overlap_worker(store, prepared, plan=plan) == prepared
    assert (Path(plan["directory"]) / "prepared.json").read_bytes() == raw
    missing = retained_native_file(store, prepared["outputs"][2]["observed"])
    missing.unlink()
    with pytest.raises(NativeFileCaptureError) as caught:
        preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    assert caught.value.code == "retained_artifact_unavailable"
    assert (Path(plan["directory"]) / "prepared.json").read_bytes() == raw


def test_real_reservation_recovery_after_injected_caller_interruption(store, tmp_path, monkeypatch):
    plan = native_plan(store, tmp_path)
    original = preparation.native_lifecycle.start_prepared
    with monkeypatch.context() as patch:
        patch.setattr(preparation.native_lifecycle, "start_prepared", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
        with pytest.raises(KeyboardInterrupt):
            preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    path = Path(plan["directory"]) / "worker.handle.json"
    before = json.loads(path.read_bytes())
    assert before["stage"] == "prepared" and not (path.parent / "prepared.json").exists()
    monkeypatch.setattr(preparation, "_snapshot", deny)
    monkeypatch.setattr(preparation.native_lifecycle, "prepare_job", deny)
    assert preparation.native_lifecycle.start_prepared is original
    recovered = preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    after = json.loads(path.read_bytes())
    assert before["unit"] == after["unit"] and before["request_sha256"] == after["request_sha256"]
    assert recovered["result"]["state"] == "produced"
    (tmp_path / "RECOVERY.json").write_bytes(canonical({"before": before, "after": after, "capture": recovered,
        "injection": "caller interrupted after real preparation before original start"}))


def test_injected_observation_timeout_keeps_original_live_handle(store, tmp_path, monkeypatch):
    plan = native_plan(store, tmp_path)
    with monkeypatch.context() as patch:
        def timeout(*args, **kwargs):
            raise AcquisitionError("local_job_boundary_unavailable", phase="local_execution",
                                   operational={"reason": "injected_observation_timeout"})
        patch.setattr(preparation.native_lifecycle, "wait_job", timeout)
        with pytest.raises(AcquisitionError) as caught:
            preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    assert caught.value.code in ("local_job_boundary_unavailable", "local_job_execution_unknown")
    directory = Path(plan["directory"])
    before = json.loads((directory / "worker.handle.json").read_bytes())
    assert not (directory / "execution.json").exists() and not (directory / "prepared.json").exists()
    monkeypatch.setattr(preparation.native_lifecycle, "prepare_job", deny)
    monkeypatch.setattr(preparation, "_snapshot", deny)
    recovered = preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    assert read(store, read(store, recovered["execution_receipt_file"])["handle_file"])["unit"] == before["unit"]
    assert recovered["result"]["state"] == "produced"


@pytest.mark.parametrize("kind", ["missing", "malformed", "newline", "wrong_parameters"])
def test_worker_result_diagnostics_never_synthesize_declarations(store, tmp_path, kind):
    plan, prepared = completed(store, tmp_path)
    path = Path(plan["directory"]) / "worker-result.json"
    if kind == "missing":
        path.unlink()
    elif kind == "malformed":
        overwrite(path, b"{malformed")
    elif kind == "newline":
        overwrite(path, path.read_bytes() + b"\n")
    else:
        result = json.loads(path.read_bytes())
        result["parameters"]["minimum_overlap_bp"] += 1
        overwrite(path, canonical(result))
    captured = recapture(store, plan, prepared)
    assert captured["result"] is None and captured["outputs"] == []
    assert (captured["worker_result_file"] is None) == (kind == "missing")
    diagnostics = [row for row in captured["failures"] if row["field_path"].startswith("/outputs/")]
    assert [row["field_path"] for row in diagnostics] == ["/outputs/" + role for role in ("sheet", "components", "projection", "diagnostics")]
    for failure, original in zip(diagnostics, prepared["outputs"]):
        assert failure["observed_value"] == original["observed"]
        assert failure["artifact_ref"] == original["observed"]["artifact_ref"]
        assert failure["partial_artifact_refs"] == [failure["artifact_ref"]]


@pytest.mark.parametrize("change", ["missing", "digest", "parameters", "fields", "page"])
def test_valid_original_result_preserves_partial_captures_and_semantic_failures(store, tmp_path, change):
    plan, prepared = completed(store, tmp_path)
    directory = Path(plan["directory"])
    role_index = 0 if change in ("missing", "digest") else 1 if change == "parameters" else 2
    output = prepared["result"]["outputs"][role_index]
    path = directory / output["declaration"]["relative_path"]
    if change == "missing":
        path.unlink()
    elif change == "digest":
        overwrite(path, b"changed bytes")
    else:
        value = json.loads(path.read_bytes())
        if change == "parameters":
            value["parameters"]["minimum_overlap_bp"] += 1
        elif change == "fields":
            value["measurement_fields"] = ["unfiltered.intersection_union_bp"]
        else:
            value["page"]["offset"] = 9
        raw = canonical(value)
        overwrite(path, raw)
        result = deepcopy(prepared["result"])
        result["outputs"][role_index]["declaration"].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        overwrite(directory / "worker-result.json", canonical(result))
    captured = recapture(store, plan, prepared)
    assert captured["result"] is not None and len(captured["outputs"]) == 4
    outcome = "unavailable" if change == "missing" else "digest_mismatch" if change == "digest" else "verified"
    assert captured["outputs"][role_index]["outcome"] == outcome
    assert any(row["field_path"] == "/outputs/projection" for row in captured["failures"])
    assert any(row["field_path"] == "/outputs/" + output["role"] for row in captured["failures"])
    assert preparation.validate_prepared_genomic_overlap_worker(store, captured, plan=plan) == captured


def test_declared_absence_is_preserved_after_actual_saved_worker_failure_to_parse(store, tmp_path):
    base = native_plan(store, tmp_path)
    source = tmp_path / "invalid-sheet.json"
    source.write_bytes(b"{}")
    sheet = capture_native_file(store, directory=str(tmp_path), relative_path=source.name, format="genomic_region_overlap_sheet_v1")
    plan = saved_plan(store, tmp_path, sheet, base["selector"])
    prepared = preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    assert prepared["result"]["state"] == "unavailable"
    assert [row["outcome"] for row in prepared["outputs"]] == ["declared_absent"] * 3 + ["verified"]
    assert read(store, prepared["execution_receipt_file"])["returncode"] == 0


def test_actual_nonzero_worker_retains_diagnostics_and_never_retries(store, tmp_path, monkeypatch):
    plan = native_plan(store, tmp_path)
    directory = Path(plan["directory"])
    directory.mkdir()
    (directory / "sheet.json").write_bytes(b"preexisting conflicting diagnostic bytes")
    prepared = preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    execution = read(store, prepared["execution_receipt_file"])
    assert execution["outcome"] == "returned" and execution["returncode"] != 0
    assert prepared["result"] is None and prepared["outputs"] == []
    assert any(row["code"] == "native_nonzero_exit" for row in prepared["failures"])
    assert any(row["field_path"] == "/outputs/sheet" and row["artifact_ref"] for row in prepared["failures"])
    monkeypatch.setattr(preparation, "_run", deny)
    assert preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY) == prepared
    (tmp_path / "ACTUAL_NONZERO_WORKER.json").write_bytes(canonical({"execution": execution, "capture": prepared}))


def test_plan_request_allocation_and_failure_join_rejection(store, tmp_path):
    plan, prepared = completed(store, tmp_path)
    wrong_plan = deepcopy(plan)
    wrong_plan["selector"]["parameters"]["minimum_overlap_bp"] += 1
    with pytest.raises(ValueError, match="plan_binding"):
        preparation.validate_prepared_genomic_overlap_worker(store, prepared, plan=wrong_plan)
    with pytest.raises(ValueError, match="allocation_binding"):
        preparation.prepare_genomic_overlap_worker(store, plan=plan,
            policy=LocalJobPolicy(memory_bytes=1, scratch_bytes=POLICY.scratch_bytes))
    execution = read(store, prepared["execution_receipt_file"])
    original = deepcopy(execution)
    execution["metadata"]["policy"]["memory_bytes"] += 1
    path = tmp_path / "wrong-execution.json"
    path.write_bytes(canonical(execution))
    bad = capture_native_file(store, directory=str(tmp_path), relative_path=path.name, format=preparation._EXECUTION)
    with pytest.raises(ValueError):
        preparation.capture_genomic_overlap_worker_outputs(store, directory=plan["directory"],
            plan_file=prepared["plan_file"], execution_receipt_file=bad)
    execution = original
    execution.update(outcome="failed", returncode=None, metadata=None,
        failure={"code": "local_job_boundary_unavailable", "phase": "local_execution", "diagnostic": None,
                 "operational": {"reason": "no actual terminal proof"}})
    path.write_bytes(canonical(execution))
    bad = capture_native_file(store, directory=str(tmp_path), relative_path=path.name, format=preparation._EXECUTION)
    with pytest.raises(AcquisitionError) as caught:
        preparation.capture_genomic_overlap_worker_outputs(store, directory=plan["directory"],
            plan_file=prepared["plan_file"], execution_receipt_file=bad)
    assert caught.value.code == "local_job_execution_unknown"


def test_capture_retention_failure_is_not_producer_absence(store, tmp_path, monkeypatch):
    plan, prepared = completed(store, tmp_path)
    def unavailable(*args, **kwargs):
        raise NativeFileCaptureError("retained_artifact_unavailable")
    monkeypatch.setattr(preparation, "capture_native_file", unavailable)
    with pytest.raises(NativeFileCaptureError) as caught:
        recapture(store, plan, prepared)
    assert caught.value.code == "retained_artifact_unavailable"


def test_injected_terminal_failure_preserves_actual_quiescent_evidence(store, tmp_path, monkeypatch):
    plan = native_plan(store, tmp_path)
    original_wait = preparation.native_lifecycle.wait_job
    observed = {}
    with monkeypatch.context() as patch:
        def terminal_error(handle):
            actual = original_wait(handle)
            observed.update(code="local_job_resource_limit", phase="local_execution", diagnostic={"injected": True},
                operational={**deepcopy(actual.metadata), "resource": "scratch_bytes", "limit": POLICY.scratch_bytes,
                    "evidence": {"injected_terminal_classification": True}})
            raise AcquisitionError(observed["code"], phase=observed["phase"], diagnostic=observed["diagnostic"],
                                   operational=observed["operational"])
        patch.setattr(preparation.native_lifecycle, "wait_job", terminal_error)
        prepared = preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    execution = read(store, prepared["execution_receipt_file"])
    assert execution["outcome"] == "failed" and execution["metadata"] is None and execution["returncode"] is None
    assert execution["failure"] == observed
    # Original valid worker bytes remain recorded; execution qualification is
    # separate. This fixture does not claim an actual exhausted resource.
    assert prepared["result"] is not None and len(prepared["outputs"]) == 4
    assert any(row["code"] == "resource_limit" and row["field_path"] == "/execution" for row in prepared["failures"])
    monkeypatch.setattr(preparation, "_run", deny)
    assert preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY) == prepared
    (tmp_path / "INJECTED_TERMINAL_FAILURE.json").write_bytes(canonical({"injected": True,
        "actual_terminal_metadata": observed["operational"], "capture": prepared}))


def test_pending_original_snapshot_tampering_cannot_dispatch(store, tmp_path, monkeypatch):
    plan = native_plan(store, tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(preparation.native_lifecycle, "start_prepared", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
        with pytest.raises(KeyboardInterrupt):
            preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    directory = Path(plan["directory"])
    intent = json.loads((directory / "intent.json").read_bytes())
    path = Path(intent["source_pins"][0]["path"])
    overwrite(path, path.read_bytes() + b"\n# deliberate pending snapshot mutation\n")
    path.chmod(0o444)
    monkeypatch.setattr(preparation.native_lifecycle, "start_prepared", deny)
    monkeypatch.setattr(preparation.native_lifecycle, "resume_start", deny)
    monkeypatch.setattr(preparation, "_snapshot", deny)
    with pytest.raises(ValueError, match="snapshot_conflict"):
        preparation.prepare_genomic_overlap_worker(store, plan=plan, policy=POLICY)
    assert json.loads((directory / "worker.handle.json").read_bytes())["stage"] == "prepared"
    assert not (directory / "prepared.json").exists()


def test_retained_request_digest_and_added_failure_cannot_change_record(store, tmp_path):
    plan, prepared = completed(store, tmp_path)
    execution = read(store, prepared["execution_receipt_file"])
    request = read(store, execution["request_file"])
    request["env"]["OMP_NUM_THREADS"] = "9"
    path = tmp_path / "foreign-request.json"
    path.write_bytes(canonical(request))
    execution["request_file"] = capture_native_file(store, directory=str(tmp_path), relative_path=path.name,
                                                    format="native_local_job_request")
    path = tmp_path / "foreign-execution.json"
    path.write_bytes(canonical(execution))
    foreign = capture_native_file(store, directory=str(tmp_path), relative_path=path.name, format=preparation._EXECUTION)
    with pytest.raises(ValueError, match="request_digest"):
        preparation.capture_genomic_overlap_worker_outputs(store, directory=plan["directory"],
            plan_file=prepared["plan_file"], execution_receipt_file=foreign)
    changed = deepcopy(prepared)
    changed["failures"].append(preparation._issue("requested_field_unavailable", "projection"))
    with pytest.raises(ValueError, match="failure_binding"):
        preparation.validate_prepared_genomic_overlap_worker(store, changed, plan=plan)
