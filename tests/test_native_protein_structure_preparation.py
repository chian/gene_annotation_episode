"""Actual bounded 393 execution, retained custody and one-reservation recovery.

393/395 inputs are unchanged native-format outputs from synthetic engineering
fixtures. Injected terminal/resource/observation failures are labeled as such;
they are not claims of biological measurements or physical resource exhaustion.
"""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import stat

import numpy as np
import pytest

from gene_annotation_episode import native_protein_structure_preparation as preparation
from gene_annotation_episode import native_lifecycle as lifecycle
from gene_annotation_episode import protein_structure_result_worker as worker
from gene_annotation_episode import protein_structure_calculations as calculations
from gene_annotation_episode import protein_structure_sheet as sheets
from gene_annotation_episode import native_protein_structure_worker as native_worker
from gene_annotation_episode import native_protein_structure_acquisition as acquisition
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.state import Store

REPO = Path(__file__).resolve().parents[1]
PACKET = REPO / "verification/tool_graders_protein_structure_preparation_2026-10-27_396"
FIXTURES = REPO / "verification/tool_graders_protein_structure_result_worker_2026-10-27_393/fixtures"
POLICY = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296)


def _bytes(value):
    return canonical(value).encode("utf-8")


def _retain(store, raw, format):
    ref = store.artifact(raw)
    return {"file_identity": {"artifact_ref": ref, "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_length": len(raw), "format": format}, "path": str(artifact_path(store, ref))}


def _native(store, directory, label="held_out"):
    path = PACKET / "fixtures/same_file.json" if label == "same_file" else FIXTURES / (label + ".json")
    raw = path.read_bytes()
    native = json.loads(raw)
    return {"version": "protein_structure_result_worker_plan_v1", "mode": "original_native_result",
        "directory": str(directory / "worker"), "expected_request": deepcopy(native["request"]),
        "expected_software": deepcopy(native["producer"]),
        "native_result": _retain(store, raw, native["version"])}, native


def _saved(store, directory):
    # Select the exact native held-out sheet/baseline from393. Serialize only
    # their unchanged values; the original native envelope stays retained.
    native = json.loads((FIXTURES / "held_out.json").read_bytes())
    sheet = native["sheet"]
    return {"version": "protein_structure_result_worker_plan_v1", "mode": "saved_sheet_recalculation",
        "directory": str(directory / "worker"),
        "sheet": _retain(store, _bytes(sheet), "protein_structure_comparison_sheet_v1"),
        "original_components": _retain(store, _bytes(sheet["native_baseline"]), "protein_structure_components_v1"),
        "parameters": deepcopy(sheet["native_request"])}, sheet


def _run(store, plan):
    prepared = preparation.prepare_protein_structure_worker(store, plan=plan, policy=POLICY)
    return preparation.validate_prepared_protein_structure_worker(store, prepared, plan=plan)


def _output(store, result, field):
    identity = result[field]["file_identity"]
    path = acquisition.retained_protein_structure_file(store, identity)
    raw = path.read_bytes()
    assert raw == _bytes(json.loads(raw)) and len(raw) == identity["byte_length"]
    return json.loads(raw)


def _forbid(*args, **kwargs):
    raise AssertionError("forbidden dispatch, producer read, calculation or acquisition")


def _forbid_science(monkeypatch):
    for owner, names in ((worker, ("run_protein_structure_result_worker", "calculate_protein_structure_components",
                                  "parse_native_protein_comparison", "validate_recorded_protein_structure_components")),
                         (calculations, ("calculate_protein_structure_components", "fit_ca_transform",
                                         "validate_recorded_protein_structure_components")),
                         (sheets, ("parse_native_protein_comparison",)),
                         (native_worker, ("execute_protein_structure_request",)),
                         (acquisition, ("capture_local_protein_structure_bundle",)),
                         (np.linalg, ("svd",)), (socket, ("socket", "create_connection"))):
        for name in names:
            monkeypatch.setattr(owner, name, _forbid)


def _forbid_lifecycle(monkeypatch):
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "status", "collect", "cancel"):
        monkeypatch.setattr(lifecycle, name, _forbid)


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "store") as value:
        yield value


@pytest.mark.parametrize("label", ["inspect", "extract", "extract_unavailable", "held_out", "supplied",
                                    "zero_available", "mixed_partial", "same_file"])
def test_actual_worker_retains_exact_native_and_baseline(store, tmp_path, label):
    plan, native = _native(store, tmp_path / "unicode-δ", label)
    before = deepcopy(plan)
    view = _run(store, plan)
    prepared, result, execution = view["prepared"], view["result"], view["execution"]
    assert plan == before and prepared["issues"] == [] and result is not None
    assert result["state"] == native["state"] and result["issues"] == native["issues"]
    assert _output(store, result, "native_result_file") == native
    assert store.get_artifact(result["native_result_file"]["file_identity"]["artifact_ref"]) == Path(plan["native_result"]["path"]).read_bytes()
    if result["operation"] == "compare":
        assert _output(store, result, "sheet_file") == native["sheet"]
        assert _output(store, result, "components_file") == native["sheet"]["native_baseline"]
    else:
        assert result["sheet_file"] is None and result["components_file"] is None
    assert execution["outcome"] == "returned" and execution["returncode"] == 0 and execution["failure"] is None
    meta = execution["metadata"]
    assert meta["policy"] == POLICY.to_dict()
    assert meta["verified_cgroup"]["memory_swap_max"] == 0
    assert meta["verified_cgroup"]["memory_max"] == POLICY.memory_bytes
    assert 'runtime_max' not in meta["verified_cgroup"]
    directory = Path(plan["directory"])
    for field, name in (("stdout_artifact_ref", "worker.stdout"), ("stderr_artifact_ref", "worker.stderr"),
                        ("handle_artifact_ref", "worker.handle.json")):
        assert store.get_artifact(execution[field]) == (directory / name).read_bytes()
    handle = json.loads(store.get_artifact(execution["handle_artifact_ref"]))
    assert handle["command"][-4:] == ["-B", "-m", "gene_annotation_episode.protein_structure_result_worker", str(directory / "plan.json")]
    request = json.loads(store.get_artifact("artifact_" + handle["request_sha256"]))
    assert request["env"]["PYTHONPATH"] == str(REPO)
    assert request["env"]["TMPDIR"] == str(directory)
    assert request["env"]["XDG_CACHE_HOME"] == str(directory / "cache")
    for path in handle["paths"].values():
        assert Path(path).is_file()
        raw = Path(path).read_bytes()
        assert store.get_artifact("artifact_" + hashlib.sha256(raw).hexdigest()) == raw
    for name in ("plan.json", "intent.json", "prepared.json"):
        raw = (directory / name).read_bytes()
        assert raw == _bytes(json.loads(raw)) and not raw.endswith(b"\n")
        assert stat.S_IMODE((directory / name).stat().st_mode) == 0o444
    assert store.db.execute("SELECT count(*) FROM records").fetchone()[0] == 0


def test_original_and_changed_saved_numerical_examples(store, tmp_path):
    plan, native = _native(store, tmp_path / "original")
    original = _run(store, plan)
    baseline = _output(store, original["result"], "components_file")
    assert baseline["counts"]["fit_used_count"]["value"] == 4
    assert baseline["counts"]["evaluation_used_count"]["value"] == 1
    assert baseline["evaluation"]["evaluation_sse"]["value"] == pytest.approx(4)
    assert baseline["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(2)
    saved, sheet = _saved(store, tmp_path / "changed")
    saved["parameters"]["evaluation_selection"] = {"kind": "all_mapped_pairs"}
    before = Path(saved["sheet"]["path"]).read_bytes()
    after = _run(store, saved)
    changed = _output(store, after["result"], "components_file")
    assert changed["counts"]["evaluation_used_count"]["value"] == 5
    assert changed["evaluation"]["evaluation_sse"]["value"] == pytest.approx(4)
    assert changed["evaluation"]["evaluation_rmsd"]["value"] == pytest.approx(math.sqrt(4 / 5))
    assert after["result"]["native_result_file"] is None
    assert _output(store, after["result"], "sheet_file") == sheet == native["sheet"]
    assert store.get_artifact(after["result"]["sheet_file"]["file_identity"]["artifact_ref"]) == before
    assert Path(saved["sheet"]["path"]).read_bytes() == before
    assert sheet["native_baseline"] == baseline
    (tmp_path / "filled-example.json").write_bytes(_bytes({"original": original, "saved": after}))


@pytest.mark.parametrize("mode", ["native_arithmetic", "saved_baseline"])
def test_008_diagnostic_cases_preserve_worker_state_without_scientific_grants(store, tmp_path, mode):
    if mode == "native_arithmetic":
        plan, native = _native(store, tmp_path)
        native["sheet"]["native_baseline"]["evaluation"]["evaluation_rmsd"]["value"] = 19.0
        plan["native_result"] = _retain(store, _bytes(native), native["version"])
    else:
        plan, sheet = _saved(store, tmp_path)
        sheet["native_baseline"] = None
        plan["sheet"] = _retain(store, _bytes(sheet), "protein_structure_comparison_sheet_v1")
    view = _run(store, plan)
    # The manifest is qualified custody; its unchanged invalid science stays
    # invalid. Root must not infer a descriptor from these diagnostic files.
    assert view["prepared"]["issues"] == [] and view["result"]["state"] == "invalid"
    assert view["result"]["components_file"] is None and view["result"]["issues"]
    if mode == "native_arithmetic":
        assert view["result"]["sheet_file"] is None
        assert _output(store, view["result"], "native_result_file") == native
        assert view["result"]["issues"][-1]["code"] == "numeric_inconsistency"
    else:
        assert view["result"]["native_result_file"] is None
        assert _output(store, view["result"], "sheet_file") == sheet
        assert view["result"]["issues"][-1]["code"] == "conflicting_identity"


def test_null_native_result_is_qualified_unavailable_science(store, tmp_path):
    plan, _ = _native(store, tmp_path, "inspect")
    plan["native_result"] = None
    view = _run(store, plan)
    assert view["result"]["state"] == "unavailable" and view["prepared"]["issues"] == []
    assert view["result"]["issues"][0]["code"] == "native_result_missing"


@pytest.mark.parametrize("case, code", [("external_copy", "invalid_output_path"), ("unknown_artifact", "retained_artifact_missing"),
    ("missing_bytes", "retained_artifact_missing"), ("changed_bytes", "input_digest_mismatch"),
    ("wrong_length", "input_digest_mismatch"), ("input_symlink", "invalid_output_path"),
    ("directory_symlink", "invalid_output_path"), ("parent_symlink", "invalid_output_path"),
    ("overlap", "invalid_output_path"), ("extra_plan", "invalid_schema"),
    ("memory", "resource_budget_exceeded"), ("scratch", "resource_budget_exceeded"), ("wall", "resource_budget_exceeded")])
def test_preflight_rejects_before_reservation(store, tmp_path, monkeypatch, case, code):
    plan, _ = _native(store, tmp_path, "inspect")
    original = Path(plan["native_result"]["path"])
    policy = POLICY
    if case == "external_copy":
        external = tmp_path / "copy.json"
        external.write_bytes(original.read_bytes())
        plan["native_result"]["path"] = str(external)
    elif case == "unknown_artifact":
        store.db.execute("DELETE FROM artifacts WHERE id=?", (plan["native_result"]["file_identity"]["artifact_ref"],))
    elif case == "missing_bytes": original.unlink()
    elif case == "changed_bytes": original.write_bytes(b"changed")
    elif case == "wrong_length": plan["native_result"]["file_identity"]["byte_length"] += 1
    elif case == "input_symlink":
        target = tmp_path / "original.json"
        original.rename(target)
        original.symlink_to(target)
    elif case == "directory_symlink": Path(plan["directory"]).symlink_to(tmp_path, target_is_directory=True)
    elif case == "parent_symlink":
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        plan["directory"] = str(alias / "worker")
    elif case == "overlap": plan["directory"] = str(original.parent)
    elif case == "extra_plan": plan["unapproved"] = True
    else:
        values = POLICY.to_dict()
        values[{"memory": "memory_bytes", "scratch": "scratch_bytes", "wall": "wall_seconds"}[case]] = 1
        policy = LocalJobPolicy(**values)
    _forbid_lifecycle(monkeypatch)
    with pytest.raises(ValueError, match=code):
        preparation.prepare_protein_structure_worker(store, plan=plan, policy=policy)


def test_completed_replay_and_deleted_directories_use_only_retained_data(store, tmp_path, monkeypatch):
    plan, _ = _saved(store, tmp_path)
    plan["parameters"]["evaluation_selection"] = {"kind": "all_mapped_pairs"}
    view = _run(store, plan)
    directory = Path(plan["directory"])
    before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in directory.iterdir() if path.is_file()}
    _forbid_science(monkeypatch)
    _forbid_lifecycle(monkeypatch)
    # Current handles/results can disappear even before operation replay: only
    # intent/prepared controls and retained artifacts are consulted.
    for path in directory.iterdir():
        if path.is_file() and path.name not in ("intent.json", "prepared.json", ".preparation.lock"):
            path.unlink()
    replay = preparation.prepare_protein_structure_worker(store, plan=plan, policy=POLICY)
    assert replay == view["prepared"]
    for name in ("intent.json", "prepared.json"):
        assert ((directory / name).read_bytes(), (directory / name).stat().st_mtime_ns) == before[name]
    shutil.rmtree(directory)
    original_open = Path.open

    def only_retained(path, *args, **kwargs):
        assert path.is_relative_to(store.path), path
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", only_retained)
    replayed = preparation.validate_prepared_protein_structure_worker(store, replay, plan=plan)
    assert replayed == view
    replayed["execution"]["metadata"]["policy"]["memory_bytes"] = 1
    assert preparation.validate_prepared_protein_structure_worker(store, replay, plan=plan) == view


def test_real_completed_reservation_interrupted_before_publication_resumes_same_unit(store, tmp_path, monkeypatch):
    plan, _ = _native(store, tmp_path)
    immutable = preparation._immutable

    def interrupt_publication(fd, name, value):
        if name == "prepared.json":
            raise KeyboardInterrupt()
        return immutable(fd, name, value)

    monkeypatch.setattr(preparation, "_immutable", interrupt_publication)
    with pytest.raises(KeyboardInterrupt):
        preparation.prepare_protein_structure_worker(store, plan=plan, policy=POLICY)
    directory = Path(plan["directory"])
    before = json.loads((directory / "worker.handle.json").read_bytes())
    assert lifecycle.status(lifecycle.NativeJobHandle(directory / "worker.handle.json"))["terminal"]
    retained_result = store.artifact((directory / "worker-result.json").read_bytes())
    assert not (directory / "prepared.json").exists()
    monkeypatch.setattr(preparation, "_immutable", immutable)
    monkeypatch.setattr(lifecycle, "prepare_job", _forbid)
    monkeypatch.setattr(lifecycle, "start_prepared", _forbid)
    _forbid_science(monkeypatch)
    view = _run(store, plan)
    assert view["prepared"]["worker_result_artifact_ref"] == retained_result
    after = json.loads((directory / "worker.handle.json").read_bytes())
    assert after == before
    assert json.loads(store.get_artifact(view["execution"]["handle_artifact_ref"]))["unit"] == before["unit"]


def _reserved_only(store, plan, monkeypatch):
    def interrupted(handle):
        raise AcquisitionError("local_job_not_collectable", phase="local_execution", operational={"state": "prepared"})
    monkeypatch.setattr(lifecycle, "start_prepared", interrupted)
    with pytest.raises(AcquisitionError, match="local_job_not_collectable"):
        preparation.prepare_protein_structure_worker(store, plan=plan, policy=POLICY)
    directory = Path(plan["directory"])
    assert not (directory / "prepared.json").exists()
    return directory, json.loads((directory / "worker.handle.json").read_bytes())


def test_prepared_undispatched_reservation_dispatches_once(store, tmp_path, monkeypatch):
    plan, _ = _native(store, tmp_path, "inspect")
    original_start = lifecycle.start_prepared
    directory, before = _reserved_only(store, plan, monkeypatch)
    assert before["stage"] == "prepared"
    starts = []

    def counted(handle, **kwargs):
        starts.append(handle.read()["unit"])
        return original_start(handle, **kwargs)

    monkeypatch.setattr(lifecycle, "prepare_job", _forbid)
    monkeypatch.setattr(lifecycle, "start_prepared", counted)
    view = _run(store, plan)
    assert starts == [before["unit"]]
    assert view["execution"]["outcome"] == "returned"
    assert json.loads((directory / "worker.handle.json").read_bytes())["unit"] == before["unit"]


def test_concurrent_same_operation_callers_share_one_os_locked_reservation(store, tmp_path, monkeypatch):
    plan, _ = _native(store, tmp_path, "inspect")
    reserve = lifecycle.prepare_job
    reservations = []

    def counted(*args, **kwargs):
        handle = reserve(*args, **kwargs)
        reservations.append(handle.read()["unit"])
        return handle

    def selected_call():
        with Store(store.path) as own_connection:
            return preparation.prepare_protein_structure_worker(own_connection, plan=plan, policy=POLICY)

    monkeypatch.setattr(lifecycle, "prepare_job", counted)
    with ThreadPoolExecutor(max_workers=2) as callers:
        first, second = [future.result() for future in [callers.submit(selected_call), callers.submit(selected_call)]]
    assert first == second and len(reservations) == 1


@pytest.mark.parametrize("name", ["plan.json", "intent.json", "prepared.json", "worker.handle.json",
                                   "worker.stdout", ".preparation.lock", "cache"])
def test_host_control_symlinks_reject_before_native_dispatch(store, tmp_path, monkeypatch, name):
    plan, _ = _native(store, tmp_path, "inspect")
    directory = Path(plan["directory"])
    directory.mkdir()
    target = tmp_path / "unselected"
    if name == "cache": target.mkdir()
    else: target.write_bytes(b"must remain unchanged")
    (directory / name).symlink_to(target, target_is_directory=name == "cache")
    _forbid_lifecycle(monkeypatch)
    with pytest.raises(ValueError, match="invalid_output_path"):
        preparation.prepare_protein_structure_worker(store, plan=plan, policy=POLICY)
    if name != "cache": assert target.read_bytes() == b"must remain unchanged"


@pytest.mark.parametrize("case", ["intent", "command", "cwd", "policy", "environment", "request_digest", "request_path"])
def test_conflicting_original_reservation_is_never_dispatched(store, tmp_path, monkeypatch, case):
    plan, _ = _native(store, tmp_path, "inspect")
    directory, body = _reserved_only(store, plan, monkeypatch)
    if case == "intent":
        plan["expected_request"]["inventory"]["include"] = ["models"]
    elif case == "command": body["command"][0] = "/different/python"
    elif case == "cwd": body["cwd"] = str(tmp_path)
    elif case == "policy": body["metadata"]["policy"]["memory_bytes"] = 1
    elif case == "request_path": body["paths"]["request"] = str(tmp_path / "unselected-secret")
    else:
        request_path = Path(body["paths"]["request"])
        request = json.loads(request_path.read_bytes())
        request["env"]["PYTHONPATH"] = str(tmp_path / "different-source")
        raw = _bytes(request)
        request_path.write_bytes(raw)
        if case == "environment": body["request_sha256"] = hashlib.sha256(raw).hexdigest()
    if case != "intent": (directory / "worker.handle.json").write_bytes(_bytes(body))
    _forbid_lifecycle(monkeypatch)
    with pytest.raises(ValueError, match="original_commission_mismatch|input_digest_mismatch|invalid_output_path"):
        preparation.prepare_protein_structure_worker(store, plan=plan, policy=POLICY)
    assert not (directory / "prepared.json").exists()


@pytest.mark.parametrize("case, expected", [("missing", "capture_incomplete"), ("changed", "input_digest_mismatch"),
    ("length", "input_digest_mismatch"), ("malformed", "invalid_schema"), ("duplicate", "invalid_schema"),
    ("nonfinite", "invalid_schema"), ("newline", "invalid_schema"), ("partial_manifest", "invalid_schema"),
    ("traversal", "invalid_output_path"), ("wrong_mode", "original_commission_mismatch"),
    ("symlink", "invalid_output_path"), ("fifo", "invalid_output_path")])
def test_terminal_output_tampering_preserves_diagnostics_without_qualification(store, tmp_path, monkeypatch, case, expected):
    plan, _ = _native(store, tmp_path)
    original_wait = lifecycle.wait_job
    secret = tmp_path / "unselected-secret"
    secret.write_bytes(b"Never open this unselected content")

    def alter(handle):
        result = original_wait(handle)
        directory = Path(plan["directory"])
        output = directory / "components.json"
        manifest = directory / "worker-result.json"
        value = json.loads(manifest.read_bytes())
        # Deliberately violate the owner-writable integrity convention for the
        # fault fixture; production does not make immutable outputs writable.
        output.chmod(0o600)
        manifest.chmod(0o600)
        if case == "missing": output.unlink()
        elif case == "changed": output.write_bytes(b"original path now contains changed bytes")
        elif case == "length": value["components_file"]["file_identity"]["byte_length"] += 1
        elif case == "malformed": manifest.write_bytes(b"{")
        elif case == "duplicate": manifest.write_bytes(b'{"mode":"duplicate",' + manifest.read_bytes()[1:])
        elif case == "nonfinite": manifest.write_bytes(b'{"x":NaN}')
        elif case == "newline": manifest.write_bytes(manifest.read_bytes() + b"\n")
        elif case == "partial_manifest": del value["components_file"]
        elif case == "traversal": value["components_file"]["relative_path"] = "../unselected-secret"
        elif case == "wrong_mode": value.update(mode="saved_sheet_recalculation", native_result_file=None)
        elif case == "symlink":
            output.unlink()
            output.symlink_to(secret)
        else:
            output.unlink()
            os.mkfifo(output)
        if case in ("length", "partial_manifest", "traversal", "wrong_mode"):
            manifest.write_bytes(_bytes(value))
        return result

    monkeypatch.setattr(lifecycle, "wait_job", alter)
    view = _run(store, plan)
    assert view["result"] is None and view["prepared"]["worker_result_artifact_ref"] is None
    assert expected in [row["code"] for row in view["prepared"]["issues"]]
    diagnostic = {row["filename"]: row["artifact_ref"] for row in view["prepared"]["diagnostic_files"]}
    assert "worker-result.json" in diagnostic and "native-result.json" in diagnostic
    secret_ref = "artifact_" + hashlib.sha256(secret.read_bytes()).hexdigest()
    assert not store.db.execute("SELECT id FROM artifacts WHERE id=?", (secret_ref,)).fetchone()
    if case == "changed": assert store.get_artifact(diagnostic["components.json"]) == b"original path now contains changed bytes"
    if case in ("symlink", "fifo", "missing"): assert "components.json" not in diagnostic


def test_real_nonzero_cli_exit_is_returned_execution_with_unqualified_diagnostics(store, tmp_path):
    plan, _ = _native(store, tmp_path, "inspect")
    directory = Path(plan["directory"])
    directory.mkdir()
    (directory / ".native-result.json.writing").write_bytes(b"prior unfinished publication")
    view = _run(store, plan)
    assert view["execution"]["outcome"] == "returned" and view["execution"]["returncode"] != 0
    assert view["execution"]["failure"] is None and view["result"] is None
    assert b"ValueError" in store.get_artifact(view["execution"]["stderr_artifact_ref"])
    assert view["prepared"]["issues"][-1]["code"] == "native_process_failed"


@pytest.mark.parametrize("code", ["local_job_resource_limit", "local_job_execution_error"])
def test_injected_terminal_acquisition_error_keeps_original_fields_and_no_exit_code(store, tmp_path, monkeypatch, code):
    plan, _ = _native(store, tmp_path, "inspect")
    wait = lifecycle.wait_job
    captured = []

    def terminal_failure(handle):
        result = wait(handle)
        error = AcquisitionError(code, phase="local_execution", diagnostic={"fixture": "terminal error injection"},
            operational={**result.metadata, "resource": "memory_bytes", "limit": POLICY.memory_bytes,
                         "evidence": {"fixture": "not physical memory exhaustion"}})
        captured.append(error)
        raise error

    monkeypatch.setattr(lifecycle, "wait_job", terminal_failure)
    view = _run(store, plan)
    execution = view["execution"]
    assert execution["outcome"] == "failed" and execution["returncode"] is None and execution["metadata"] is None
    assert execution["failure"] == {"code": captured[0].code, "phase": captured[0].phase,
        "diagnostic": captured[0].diagnostic, "operational": captured[0].operational}
    assert view["result"] is None and execution["handle_artifact_ref"] is not None


@pytest.mark.parametrize("code", ["local_job_execution_unknown", "local_job_not_collectable", "local_job_cancelled"])
def test_unfinished_observation_is_not_finalized_and_recovery_keeps_original_handle(store, tmp_path, monkeypatch, code):
    plan, _ = _native(store, tmp_path, "inspect")
    wait = lifecycle.wait_job
    errors = []

    def unknown(handle):
        result = wait(handle)
        error = AcquisitionError(code, phase="local_execution", operational=result.metadata)
        errors.append(error)
        raise error

    monkeypatch.setattr(lifecycle, "wait_job", unknown)
    with pytest.raises(AcquisitionError) as caught:
        preparation.prepare_protein_structure_worker(store, plan=plan, policy=POLICY)
    assert caught.value is errors[0]
    directory = Path(plan["directory"])
    before = (directory / "worker.handle.json").read_bytes()
    assert not (directory / "prepared.json").exists()
    monkeypatch.setattr(lifecycle, "wait_job", wait)
    monkeypatch.setattr(lifecycle, "prepare_job", _forbid)
    monkeypatch.setattr(lifecycle, "start_prepared", _forbid)
    assert _run(store, plan)["result"] is not None
    assert (directory / "worker.handle.json").read_bytes() == before


@pytest.fixture(scope="module")
def completed(tmp_path_factory):
    directory = tmp_path_factory.mktemp("closed-validation")
    with Store(directory / "store") as store:
        plan, _ = _native(store, directory, "inspect")
        yield store, plan, _run(store, plan)


@pytest.mark.parametrize("case", ["extra_prepared", "extra_diagnostic", "extra_execution", "boolean_exit", "float_exit",
    "extra_issue", "wrong_plan", "wrong_result_ref", "null_grant", "duplicate_diagnostic", "diagnostic_order",
    "unexpected_diagnostic", "wrong_diagnostic_ref", "metadata_policy", "changed_request_artifact"])
def test_closed_retained_validation_rejects_mismatch(completed, monkeypatch, case):
    store, plan, original = completed
    prepared = deepcopy(original["prepared"])
    plan = deepcopy(plan)
    if case == "extra_prepared": prepared["extra"] = 1
    elif case == "extra_diagnostic": prepared["diagnostic_files"][0]["extra"] = 1
    elif case == "extra_issue": prepared["issues"] = [{"code": "invalid_schema", "extra": "unapproved"}]
    elif case == "wrong_plan": plan["expected_request"]["inventory"]["include"] = ["models"]
    elif case == "wrong_result_ref": prepared["worker_result_artifact_ref"] = prepared["plan_artifact_ref"]
    elif case == "null_grant": prepared["worker_result_artifact_ref"] = None
    elif case == "duplicate_diagnostic": prepared["diagnostic_files"].append(prepared["diagnostic_files"][0])
    elif case == "diagnostic_order": prepared["diagnostic_files"].reverse()
    elif case == "unexpected_diagnostic": prepared["diagnostic_files"][0]["filename"] = "../../unselected.json"
    elif case == "wrong_diagnostic_ref": prepared["diagnostic_files"][0]["artifact_ref"] = prepared["plan_artifact_ref"]
    else:
        execution = deepcopy(original["execution"])
        if case == "extra_execution": execution["extra"] = 1
        elif case == "boolean_exit": execution["returncode"] = False
        elif case == "float_exit": execution["returncode"] = 0.0
        elif case == "metadata_policy": execution["metadata"]["policy"]["wall_seconds"] = 4
        else:
            handle = json.loads(store.get_artifact(execution["handle_artifact_ref"]))
            request = json.loads(store.get_artifact("artifact_" + handle["request_sha256"]))
            request["env"]["UNAPPROVED"] = "1"
            request_ref = store.artifact(_bytes(request))
            handle["request_sha256"] = request_ref[len("artifact_"):]
            execution["handle_artifact_ref"] = store.artifact(_bytes(handle))
        prepared["execution_receipt_artifact_ref"] = store.artifact(_bytes(execution))
    _forbid_science(monkeypatch)
    _forbid_lifecycle(monkeypatch)
    with pytest.raises(ValueError):
        preparation.validate_prepared_protein_structure_worker(store, prepared, plan=plan)


@pytest.mark.parametrize("case", ["missing_input", "changed_input", "missing_output", "changed_output", "size_metadata"])
def test_lost_or_changed_retained_artifacts_never_reacquire(store, tmp_path, monkeypatch, case):
    plan, _ = _native(store, tmp_path, "inspect")
    view = _run(store, plan)
    output = view["result"]["native_result_file"]["file_identity"]["artifact_ref"]
    # For original inspection input and output bytes are deliberately identical;
    # use the worker manifest as the separately retained output corruption case.
    ref = plan["native_result"]["file_identity"]["artifact_ref"] if case.endswith("input") else view["prepared"]["worker_result_artifact_ref"]
    path = artifact_path(store, ref)
    if case.startswith("missing"): path.unlink()
    elif case.startswith("changed"): path.write_bytes(b"changed retained bytes")
    else: store.db.execute("UPDATE artifacts SET size=size+1 WHERE id=?", (ref,))
    _forbid_science(monkeypatch)
    _forbid_lifecycle(monkeypatch)
    with pytest.raises(ValueError, match="retained_artifact_missing|input_digest_mismatch"):
        preparation.validate_prepared_protein_structure_worker(store, view["prepared"], plan=plan)
    with pytest.raises(ValueError, match="retained_artifact_missing|input_digest_mismatch"):
        preparation.prepare_protein_structure_worker(store, plan=plan, policy=POLICY)

