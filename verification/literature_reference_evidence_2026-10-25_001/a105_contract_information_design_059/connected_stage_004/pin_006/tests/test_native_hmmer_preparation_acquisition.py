"""Original HMMER result custody; these tests do not execute HMMER.

The complete native producer outputs are retained evidence. Relocated cases
explicitly build synthetic custody envelopes around copied native bytes; the
original reservation test separately opens a real producer reservation.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from gene_annotation_episode import native_hmmer_preparation_acquisition as capture
from gene_annotation_episode.native_hmmer_preparation_contracts import (
    PROGRAM_MODES, compile_native_hmmer_preparation_job,
)
from gene_annotation_episode.native_hmmer_preparation_local import PLAN_NAME
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest as digest
from gene_annotation_episode.practical_execution_state import canonical
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "verification/tool_graders_hmmer_preparation_producer_2026-10-26_267"
RETAINED = PRODUCER / "check002/temporary"
NATIVE_PLANS = sorted(p for p in RETAINED.glob("test_actual_all_selected_modes*/plan.json")
                      if not p.parent.is_symlink())
PREFIX = "native_hmmer_preparation_"


def forbidden(*args, **kwargs):
    raise AssertionError("capture must not run native work, grade, or reacquire on replay")


def read_native(plan_path):
    plan = json.loads(plan_path.read_bytes())
    bundle = json.loads((Path(plan["attempt_directory"]) / "bundle.json").read_bytes())
    return plan, bundle


def target_for(plan, assignment):
    identity = plan["identity"]
    return {"version": "execution_target_v1", "handle": "source_hmmer_handoff270",
        "run_id": identity["run_id"], "origin_episode_id": identity["episode_id"],
        "resource_kind": "local", "resource_id": identity["resource_id"],
        "execution_id": identity["execution_id"], "request_sha256": identity["requested_job_sha256"],
        "assignment": deepcopy(assignment), "scope": {}}


def selected_native(program="hmmconvert", mode="binary"):
    for path in NATIVE_PLANS:
        plan, bundle = read_native(path)
        if (bundle["program"], bundle["mode"]) == (program, mode):
            return plan, bundle
    raise AssertionError("required retained native example missing")


def synthetic_custody(tmp_path, monkeypatch, program="hmmconvert", mode="binary", retained_plan=None):
    """Same native bytes, explicitly synthetic relocated owner/path envelope."""
    plan, bundle = selected_native(program, mode) if retained_plan is None else read_native(retained_plan)
    original = Path(plan["attempt_directory"])
    workspace = tmp_path / "workspace"
    identity = {**plan["identity"], "run_id": "capture270-synthetic", "episode_id": "local-child270"}
    action = workspace / ".episode-operations" / digest({"run": identity["run_id"],
        "episode": identity["episode_id"]}) / identity["attempt_id"]
    root = action / "hmmer-preparation-attempt"
    shutil.copytree(original, root)
    identity["execution_id"] = str(action / "native.json")
    plan.update(identity=identity, attempt_directory=str(root))
    bundle["identity"] = deepcopy(identity)
    paths = {}
    for row in bundle["inputs"]:
        paths.setdefault(row["role"], []).append(str(root / row["relative_path"]))
    job = plan["requested_job"]["native_hmmer_preparation"]
    compiled = compile_native_hmmer_preparation_job(job, input_paths=paths, output_directory=str(root))
    bundle["realized_argv"] = compiled["argv"]
    bundle["environment"] = {**compiled["environment"],
        **{k: str(root / "tmp") for k in ("TMPDIR", "TMP", "TEMP")}, "XDG_CACHE_HOME": str(root / "cache")}
    (root / "bundle.json").write_text(canonical(bundle) + "\n")
    target = target_for(plan, {"workspace": str(workspace), "resource_id": identity["resource_id"],
        "resource_kind": "local", "requested_job": deepcopy(plan["requested_job"])})
    monkeypatch.setattr(capture, "local_hmmer_preparation_plan", lambda *a: deepcopy(plan))
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    return root, plan, bundle, target


@pytest.mark.parametrize("value", [None, [], {}, {"resource_kind": []}, {"resource_kind": "api"},
    {"resource_kind": "local", "assignment": {"requested_job": {"native_infernal_preparation": {}}}}])
def test_recognizer_requires_exact_branch(value):
    assert capture.is_native_hmmer_preparation_target(value) is False


def test_retained_population_is_exactly_all_26_modes():
    assert len(NATIVE_PLANS) == 26
    actual = {(b["program"], b["mode"]) for _, b in map(read_native, NATIVE_PLANS)}
    assert actual == {(p, m) for p, modes in PROGRAM_MODES.items() for m in modes}


@pytest.mark.parametrize("path", NATIVE_PLANS, ids=lambda p: p.parent.name)
def test_all_retained_native_modes_have_pure_original_validation(path, monkeypatch):
    plan, bundle = read_native(path)
    from gene_annotation_episode import native_hmmer_preparation_driver as driver
    monkeypatch.setattr(driver, "native_abi", forbidden)
    for name in ("open", "stat", "resolve", "read_bytes"):
        monkeypatch.setattr(Path, name, forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    assert capture.validate_original_bundle(bundle, plan) == bundle


@pytest.mark.parametrize("program,mode", [("hmmconvert", "binary"), ("hmmpress", "index"),
    ("hmmfetch", "index"), ("hmmsim", "viterbi"), ("hmmerfm-exactmatch", "locations")])
def test_ordered_occurrences_full_bytes_aliases_and_saved_replay(tmp_path, monkeypatch, program, mode):
    root, _, bundle, target = synthetic_custody(tmp_path, monkeypatch, program, mode)
    calls, actual = [], capture._capture_file
    def counted(*args):
        calls.append(args[2])
        return actual(*args)
    monkeypatch.setattr(capture, "_capture_file", counted)
    with Store(tmp_path / "store") as store:
        result = capture.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert result["complete"] and result["bundle_validated"] and not result["failures"]
        assert len(result["artifacts"]) == sum(len(bundle[k]) for k in ("inputs", "working_copies", "artifacts"))
        assert len(calls) == len(set(calls))
        for row in result["artifacts"]:
            assert store.get_artifact(row["artifact_ref"]) == (root / row["relative_path"]).read_bytes()
        if program == "hmmconvert":
            rows = [r for r in result["artifacts"] if r["role"] in {"stdout", "converted_models"}]
            assert len(rows) == 2 and rows[0]["artifact_ref"] == rows[1]["artifact_ref"]
            assert store.get_artifact(rows[0]["artifact_ref"])[:4] == bytes.fromhex("baedede8")
        source = capture.publish_original_source(store, bundle=bundle, capture=result)
        assert store.get(source)["version"] == PREFIX + "bundle_v1"
        shutil.rmtree(root.parent)
        monkeypatch.setattr(capture, "local_hmmer_preparation_plan", forbidden)
        monkeypatch.setattr(capture, "_capture_file", forbidden)
        assert capture.capture_local_bundle(store, target=target, directory=tmp_path / "capture") == result


@pytest.mark.parametrize("fault", ["changed", "missing", "symlink", "directory"])
def test_fault_preserves_other_complete_files_and_original_receipt(tmp_path, monkeypatch, fault):
    root, _, bundle, target = synthetic_custody(tmp_path, monkeypatch)
    relative = next(r["relative_path"] for r in bundle["artifacts"] if r["role"] == "converted_models")
    path = root / relative
    original = path.read_bytes()
    path.unlink()
    if fault == "changed":
        path.write_bytes(original + b"extra")
    elif fault == "symlink":
        outside = tmp_path / "outside"
        outside.write_bytes(original)
        path.symlink_to(outside)
    elif fault == "directory":
        path.mkdir()
    with Store(tmp_path / "store") as store:
        result = capture.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert result["bundle_validated"] and not result["complete"] and result["artifacts"]
        assert len([f for f in result["failures"] if f["code"].endswith(relative)]) == 2
        assert bool(result["invalid_artifacts"]) == (fault == "changed")
        shutil.rmtree(root.parent)
        monkeypatch.setattr(capture, "local_hmmer_preparation_plan", forbidden)
        assert capture.capture_local_bundle(store, target=target, directory=tmp_path / "capture") == result


@pytest.mark.parametrize("raw", [b"{", b"null", b"[]", b"\xff", b'{"version":1,"version":2}', b'{"a":NaN}'])
def test_malformed_bundle_is_retained_as_failed_capture(tmp_path, monkeypatch, raw):
    root, _, _, target = synthetic_custody(tmp_path, monkeypatch)
    (root / "bundle.json").write_bytes(raw)
    with Store(tmp_path / "store") as store:
        result = capture.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert not result["complete"] and not result["bundle_validated"]
        assert store.get_artifact(result["bundle_artifact_ref"]) == raw
        shutil.rmtree(root.parent)
        monkeypatch.setattr(capture, "local_hmmer_preparation_plan", forbidden)
        assert capture.capture_local_bundle(store, target=target, directory=tmp_path / "capture") == result


@pytest.mark.parametrize("fault", ["run_id", "origin_episode_id", "resource_id", "execution_id", "request_sha256", "workspace"])
def test_wrong_selected_target_rejected_before_artifact_read(tmp_path, monkeypatch, fault):
    _, _, _, target = synthetic_custody(tmp_path, monkeypatch)
    if fault == "workspace":
        target["assignment"]["workspace"] = str(tmp_path / "other")
    elif fault == "execution_id":
        target[fault] = str(tmp_path / "other/native.json")
    elif fault == "request_sha256":
        target[fault] = "a" * 64
    else:
        target[fault] = "other"
    monkeypatch.setattr(capture, "_capture_file", forbidden)
    with Store(tmp_path / "store") as store, pytest.raises(ValueError):
        capture.capture_local_bundle(store, target=target, directory=tmp_path / "capture")


@pytest.mark.parametrize("fault", ["byte_order", "float_format", "bytes_per_float", "uint32_bytes", "extra", "missing"])
def test_invalid_native_abi_shape_rejected(fault):
    plan, bundle = selected_native()
    if fault == "extra":
        bundle["native_abi"]["invented"] = 4
    elif fault == "missing":
        del bundle["native_abi"]["c_float_bytes"]
    else:
        bundle["native_abi"][fault] = {"byte_order": [], "float_format": "guessed", "bytes_per_float": 4, "uint32_bytes": True}[fault]
    with pytest.raises(ValueError, match="bundle_native_abi_invalid"):
        capture.validate_original_bundle(bundle, plan)


def test_valid_recorded_abi_does_not_use_current_host(monkeypatch):
    plan, bundle = selected_native()
    bundle["native_abi"]["byte_order"] = "big"  # synthetic original producer ABI
    from gene_annotation_episode import native_hmmer_preparation_driver as driver
    monkeypatch.setattr(driver, "native_abi", forbidden)
    assert capture.validate_original_bundle(bundle, plan)["native_abi"]["byte_order"] == "big"


def preflight_bundle(plan, bundle, code, role, **detail):
    result = deepcopy(bundle)
    result["returncode"] = None
    result["failures"] = [{"stage": "preflight", "code": PREFIX + code, "role": role, "detail": detail}]
    result["artifacts"] = []
    result["failures"] += [{"stage": "outputs", "code": PREFIX + "missing_output", "role": r["role"],
                            "detail": {"relative_path": r["relative_path"]}}
                           for r in plan["requested_job"]["native_hmmer_preparation"]["outputs"]]
    return result


def test_query_line_ordinal_is_not_file_operand_ordinal():
    plan, bundle = selected_native("hmmerfm-exactmatch", "locations")
    result = preflight_bundle(plan, bundle, "invalid_exactmatch_queries", "queries", ordinal=7, reason="query_empty")
    assert capture.validate_original_bundle(result, plan) == result
    result["returncode"] = 0
    with pytest.raises(ValueError, match="execution_after_preexecution_failure"):
        capture.validate_original_bundle(result, plan)


@pytest.mark.parametrize("fault", ["role", "reason", "abi", "binding"])
def test_preflight_relationships_are_not_accepted_from_code_alone(fault):
    plan, bundle = selected_native("hmmerfm-exactmatch", "locations")
    result = preflight_bundle(plan, bundle, "invalid_exactmatch_queries", "queries", ordinal=2, reason="query_empty")
    if fault == "role":
        result["failures"][0]["role"] = "source_sequences"
    elif fault == "reason":
        result["failures"][0]["detail"]["reason"] = "malformed_stockholm"
    elif fault == "abi":
        result = preflight_bundle(plan, bundle, "incompatible_fm_abi", "fm_database", reason="producer_byte_order_mismatch")
    else:
        result = preflight_bundle(plan, bundle, "source_binding_digest_mismatch", "source_sequences", reason="source_sha256_order_mismatch")
    with pytest.raises(ValueError, match="bundle_preflight_"):
        capture.validate_original_bundle(result, plan)


def test_actual_native_nonzero_prefix_can_be_captured_as_complete_custody(tmp_path, monkeypatch):
    # Retained producer test actually ran native conversion and exited1 after a valid first model.
    path = RETAINED / "test_actual_conversion_failure0/plan.json"
    root, plan, bundle, target = synthetic_custody(tmp_path, monkeypatch, retained_plan=path)
    assert bundle["returncode"] == 1
    assert capture.validate_original_bundle(bundle, plan) == bundle
    with Store(tmp_path / "store") as store:
        result = capture.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert result["complete"] and result["bundle_validated"]
        output = next(r for r in result["artifacts"] if r["role"] == "converted_models")
        raw = store.get_artifact(output["artifact_ref"])
        assert raw == (root / output["relative_path"]).read_bytes()
        assert raw.count(b"HMMER3/f") == 1 and raw.endswith(b"//\n")
        retained_bundle = json.loads(store.get_artifact(result["bundle_artifact_ref"]))
        assert retained_bundle["returncode"] == 1 and retained_bundle["failures"]


def test_original_real_reservation_capture_and_replay(tmp_path, monkeypatch):
    paths = [p for p in RETAINED.glob("test_actual_reservation_cli_di*/assignment.json") if not p.parent.is_symlink()]
    assert len(paths) == 1
    assignment = json.loads(paths[0].read_bytes())
    plans = list(Path(assignment["workspace"]).glob(".episode-operations/*/*/" + PLAN_NAME))
    assert len(plans) == 1
    plan = json.loads(plans[0].read_bytes())
    target = target_for(plan, assignment)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    with Store(tmp_path / "store") as store:
        result = capture.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert result["complete"] and result["bundle_validated"]
        sequence = next(r for r in result["artifacts"] if r["role"] == "generated_sequences")
        assert store.get_artifact(sequence["artifact_ref"]).splitlines()[1] == b"ACDEFGHIKLMN"
        monkeypatch.setattr(capture, "local_hmmer_preparation_plan", forbidden)
        monkeypatch.setattr(capture, "_capture_file", forbidden)
        assert capture.capture_local_bundle(store, target=target, directory=tmp_path / "capture") == result


@pytest.mark.parametrize("fault", ["identity", "abi", "row", "failure", "completion", "retained_bytes"])
def test_changed_saved_capture_cannot_be_replayed(tmp_path, monkeypatch, fault):
    _, _, _, target = synthetic_custody(tmp_path, monkeypatch)
    with Store(tmp_path / "store") as store:
        directory = tmp_path / "capture"
        result = capture.capture_local_bundle(store, target=target, directory=directory)
        if fault == "identity":
            target["handle"] = "source_other_handoff"
        elif fault == "abi":
            reference = result["bundle_artifact_ref"]
            metadata = store._require(reference, {"artifact"})
            path = store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]
            body = json.loads(path.read_bytes())
            body["native_abi"]["byte_order"] = "big"
            path.write_text(canonical(body))
        elif fault == "retained_bytes":
            reference = result["artifacts"][0]["artifact_ref"]
            metadata = store._require(reference, {"artifact"})
            path = store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]
            path.write_bytes(b"changed")
        else:
            if fault == "row":
                result["artifacts"][0]["ordinal"] += 1
            elif fault == "completion":
                result["complete"] = False
            else:
                result["failures"].append({"stage": "capture", "code": "unrelated_failure", "record_key": None})
            path = directory / "capture.json"
            path.unlink()
            path.write_text(canonical(result) + "\n")
        monkeypatch.setattr(capture, "local_hmmer_preparation_plan", forbidden)
        monkeypatch.setattr(capture, "_capture_file", forbidden)
        with pytest.raises(ValueError):
            capture.capture_local_bundle(store, target=target, directory=directory)
