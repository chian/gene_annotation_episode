"""Capture custody tests; synthetic faults are distinct from retained native runs.

This suite never executes Infernal. Real producer251 bundles are read unchanged;
synthetic cases construct explicit envelopes and deliberately malformed bytes.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from gene_annotation_episode import native_infernal_preparation_acquisition as acquisition
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest as digest
from gene_annotation_episode.native_infernal_preparation_contracts import (
    compile_native_infernal_preparation_job, requested_job_from_infernal_preparation,
)
from gene_annotation_episode.practical_execution_state import canonical
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "verification/tool_graders_infernal_preparation_producer_2026-10-26_251"
PREFIX = "native_infernal_preparation_"


def forbidden(*args, **kwargs):
    raise AssertionError("native execution, scientific parsing, network or reacquisition is forbidden")


@pytest.mark.parametrize("target", [None, [], {}, {"resource_kind": []}, {"resource_kind": "api"},
    {"resource_kind": "local", "assignment": {"requested_job": {"native_infernal": {}}}}])
def test_recognizer_requires_explicit_preparation_branch(target):
    assert acquisition.is_native_infernal_preparation_target(target) is False


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def pair(data):
    return len(data), hashlib.sha256(data).hexdigest()


def failure(stage, code, role=None, **detail):
    return {"stage": stage, "code": PREFIX + code, "role": role, "detail": detail}


def target_for(plan, assignment):
    identity = plan["identity"]
    return {"version": "execution_target_v1", "handle": "source_original_handoff252",
        "run_id": identity["run_id"], "origin_episode_id": identity["episode_id"],
        "resource_kind": "local", "resource_id": identity["resource_id"],
        "execution_id": identity["execution_id"], "request_sha256": identity["requested_job_sha256"],
        "assignment": deepcopy(assignment), "scope": {}}


def sealed_case(tmp_path, monkeypatch, mode="merge_scores"):
    workspace = tmp_path / "workspace"
    identity = {"run_id": "capture252-synthetic", "episode_id": "selected-local-child",
        "resource_id": "local", "operation_key": "original-selected-operation"}
    action = workspace / ".episode-operations" / digest({"run": identity["run_id"],
        "episode": identity["episode_id"]}) / digest(identity["operation_key"])
    root = action / "infernal-preparation-attempt"
    root.mkdir(parents=True)
    identity.update(execution_id=str(action / "native.json"), attempt_id=digest(identity["operation_key"]))
    originals = [("models", 0, "infernal_cm_legacy_ascii", b"synthetic original model\n")]
    if mode == "merge_scores":
        originals += [("partition_scores", i, "infernal_partition_scores", b"synthetic partition " + str(i).encode())
                      for i in range(2)]
    outputs = [{"role": r, "format": "infernal_" + r, "relative_path": "outputs/" + r}
               for r in ("stdout", "stderr")]
    outputs += [{"role": "calibrated_models", "format": "infernal_cm_ascii",
                 "relative_path": "outputs/calibrated_models"}]
    operands = [{"role": role, "ordinal": ordinal, "path": "/original/" + role + "/" + str(ordinal),
        "format": fmt, "sha256": pair(data)[1], "size_bytes": len(data), "artifact_ref": None}
        for role, ordinal, fmt, data in originals]
    job = {"version": PREFIX + "job_v1", "program": "cmcalibrate", "mode": mode,
        "software": {"executable": "/original/bin/cmcalibrate", "sha256": "a" * 64, "engine_version": "synthetic"},
        "environment": {"LC_ALL": "C"}, "operands": operands,
        "options": ["-L", "0.01", "--ptot", "2"] if mode == "merge_scores" else ["-L", "0.01"],
        "outputs": outputs, "key": None, "grading_parameters": {}}
    request = requested_job_from_infernal_preparation(job)
    identity["requested_job_sha256"] = digest(request)
    plan = {"version": PREFIX + "run_plan_v1", "identity": identity, "requested_job": request,
        "attempt_directory": str(root), "policy": {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}}
    inputs, staged, contents = [], {}, {}
    for operand, (_, _, _, data) in zip(operands, originals):
        relative = acquisition._staged_relative(operand)
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        staged.setdefault(operand["role"], []).append(str(path))
        contents[operand["role"], operand["ordinal"]] = data
        inputs.append({"role": operand["role"], "ordinal": operand["ordinal"], "format": operand["format"],
            "original_path": operand["path"], "relative_path": relative, "artifact_ref": operand["artifact_ref"],
            **{prefix + "_sha256": operand["sha256"] for prefix in ("expected", "staged", "final")},
            **{prefix + "_size_bytes": operand["size_bytes"] for prefix in ("expected", "staged", "final")}})
    compiled = compile_native_infernal_preparation_job(job, input_paths=staged, output_directory=str(root))
    copies = []
    for row in compiled["working_copies"]:
        data = contents[row["operand_role"], row["operand_ordinal"]]
        final = b"synthetic calibrated output\n" if row["mutable"] else data
        path = Path(row["destination"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(final)
        copies.append({"operand_role": row["operand_role"], "operand_ordinal": row["operand_ordinal"],
            "relative_path": str(path.relative_to(root)), "mutable": row["mutable"],
            "source_sha256": pair(data)[1], "initial_sha256": pair(data)[1], "initial_size_bytes": len(data),
            "final_sha256": pair(final)[1], "final_size_bytes": len(final)})
    artifacts = []
    for row in outputs:
        path = root / row["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if row["role"] in {"stdout", "stderr"}:
            path.write_bytes(b"synthetic native stdout\n" if row["role"] == "stdout" else b"")
        size, sha = pair(path.read_bytes())
        artifacts.append({**row, "sha256": sha, "size_bytes": size})
    bundle = {"version": PREFIX + "bundle_v1", "identity": deepcopy(identity), "requested_job": deepcopy(request),
        "program": job["program"], "mode": job["mode"], "operation": compiled["operation"],
        "software": {"executable": job["software"]["executable"], "expected_sha256": "a" * 64,
            "actual_sha256": "a" * 64, "declared_engine_version": "synthetic"},
        "realized_argv": compiled["argv"], "environment": {**job["environment"],
            **{k: str(root / "tmp") for k in ("TMPDIR", "TMP", "TEMP")}, "XDG_CACHE_HOME": str(root / "cache")},
        "inputs": inputs, "working_copies": copies, "returncode": 0, "artifacts": artifacts, "failures": [],
        "started_at": "2026-10-26T00:00:00+00:00", "finished_at": "2026-10-26T00:00:01+00:00"}
    write_json(root / "bundle.json", bundle)
    target = target_for(plan, {"workspace": str(workspace), "resource_id": "local", "resource_kind": "local",
        "requested_job": request})
    monkeypatch.setattr(acquisition, "local_infernal_preparation_plan", lambda *a: deepcopy(plan))
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    from gene_annotation_episode import native_infernal_preparation_worker as worker
    monkeypatch.setattr(worker, "grade_infernal_preparation", forbidden)
    return root, plan, bundle, target


@pytest.mark.parametrize("mode", ["calibrate", "merge_scores"])
def test_ordered_roles_shared_bytes_and_replay_without_originals(tmp_path, monkeypatch, mode):
    root, plan, bundle, target = sealed_case(tmp_path, monkeypatch, mode)
    with Store(tmp_path / "store") as store:
        calls, actual = [], acquisition._capture_file
        def observed(store, directory, relative, *args):
            calls.append(relative)
            return actual(store, directory, relative, *args)
        monkeypatch.setattr(acquisition, "_capture_file", observed)
        captured = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert captured["complete"] and captured["bundle_validated"] and not captured["failures"]
        assert len(captured["artifacts"]) == len(bundle["inputs"]) + len(bundle["working_copies"]) + len(bundle["artifacts"])
        assert len(calls) == len(set(calls))
        working = next(r for r in captured["artifacts"] if r["direction"] == "working_copy" and r["role"] == "models")
        output = next(r for r in captured["artifacts"] if r["role"] == "calibrated_models")
        assert working["artifact_ref"] == output["artifact_ref"]
        assert working["format"] == "infernal_cm_legacy_ascii" and output["format"] == "infernal_cm_ascii"
        if mode == "merge_scores":
            for direction in ("input", "working_copy"):
                rows = [r for r in captured["artifacts"] if r["role"] == "partition_scores" and r["direction"] == direction]
                assert [r["ordinal"] for r in rows] == [0, 1]
                assert [store.get_artifact(r["artifact_ref"]) for r in rows] == [b"synthetic partition 0", b"synthetic partition 1"]
        assert store.get_artifact(captured["bundle_artifact_ref"]) == (root / "bundle.json").read_bytes()
        shutil.rmtree(root.parent)
        monkeypatch.setattr(acquisition, "local_infernal_preparation_plan", forbidden)
        monkeypatch.setattr(acquisition, "_capture_file", forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture") == captured
        assert json.loads((tmp_path / "capture/capture-plan.json").read_bytes()) == plan


def test_pure_bundle_validation_never_reads_paths(tmp_path, monkeypatch):
    _, plan, bundle, _ = sealed_case(tmp_path, monkeypatch)
    for name in ("open", "stat", "resolve", "read_bytes"):
        monkeypatch.setattr(Path, name, forbidden)
    result = acquisition.validate_original_bundle(bundle, plan)
    result["inputs"][0]["artifact_ref"] = "changed"
    assert bundle["inputs"][0]["artifact_ref"] is None


@pytest.mark.parametrize("field", ["run_id", "episode_id", "resource_id", "execution_id", "operation_key",
    "attempt_id", "requested_job_sha256"])
def test_original_bundle_identity_is_immutable(tmp_path, monkeypatch, field):
    _, plan, bundle, _ = sealed_case(tmp_path, monkeypatch)
    bundle["identity"][field] = "forged"
    with pytest.raises(ValueError):
        acquisition.validate_original_bundle(bundle, plan)


@pytest.mark.parametrize("fault", ["argv", "request", "mode", "operation", "env", "software", "time", "rc_bool",
    "input_path", "input_ordinal", "input_expected", "input_final_pair", "input_final_unreported",
    "input_order", "copy_path", "copy_ordinal", "copy_source", "copy_initial", "copy_final_shared", "copy_mutable",
    "output_path", "output_format", "output_digest", "missing_output", "unknown_failure", "failure_role",
    "failure_ordinal", "failure_copy_path", "failure_detail", "wrong_nonzero", "unknown_field"])
def test_pure_manifest_rejects_forged_relationships(tmp_path, monkeypatch, fault):
    _, plan, bundle, _ = sealed_case(tmp_path, monkeypatch)
    if fault == "argv": bundle["realized_argv"].append("--forged")
    elif fault == "request": bundle["requested_job"]["argv"].append("--forged")
    elif fault == "mode": bundle["mode"] = "calibrate"
    elif fault == "operation": bundle["operation"]["settings"]["-L"] = 1.0
    elif fault == "env": bundle["environment"]["INFERNAL_NCPU"] = "999"
    elif fault == "software": bundle["software"]["actual_sha256"] = "0" * 64
    elif fault == "time": bundle["finished_at"] = "2026-10-25T00:00:00+00:00"
    elif fault == "rc_bool": bundle["returncode"] = True
    elif fault == "input_path": bundle["inputs"][0]["relative_path"] = "../escape"
    elif fault == "input_ordinal": bundle["inputs"][1]["ordinal"] = True
    elif fault == "input_expected": bundle["inputs"][0]["expected_sha256"] = "0" * 64
    elif fault == "input_final_pair": bundle["inputs"][0]["final_sha256"] = None
    elif fault == "input_final_unreported": bundle["inputs"][0]["final_sha256"] = "0" * 64
    elif fault == "input_order": bundle["inputs"][1:] = reversed(bundle["inputs"][1:])
    elif fault == "copy_path": bundle["working_copies"][0]["relative_path"] = "other.cm"
    elif fault == "copy_ordinal": bundle["working_copies"][1]["operand_ordinal"] = 1
    elif fault == "copy_source": bundle["working_copies"][0]["source_sha256"] = "0" * 64
    elif fault == "copy_initial": bundle["working_copies"][0]["initial_sha256"] = "0" * 64
    elif fault == "copy_final_shared": bundle["working_copies"][0]["final_sha256"] = "0" * 64
    elif fault == "copy_mutable": bundle["working_copies"][0]["mutable"] = 1
    elif fault == "output_path": bundle["artifacts"][0]["relative_path"] = "other"
    elif fault == "output_format": bundle["artifacts"][0]["format"] = "fasta"
    elif fault == "output_digest": bundle["artifacts"][0]["sha256"] = "bad"
    elif fault == "missing_output": bundle["artifacts"].pop()
    elif fault == "unknown_failure": bundle["failures"] = [failure("execution", "fabricated")]
    elif fault == "failure_role": bundle["failures"] = [failure("software", "software_not_executable", "models")]
    elif fault == "failure_ordinal": bundle["failures"] = [failure("execution", "immutable_input_changed", "partition_scores", ordinal=99)]
    elif fault == "failure_copy_path": bundle["failures"] = [failure("execution", "immutable_working_copy_changed", "partition_scores", operand_ordinal=0, relative_path="wrong")]
    elif fault == "failure_detail": bundle["failures"] = [failure("execution", "immutable_input_changed", "models", ordinal=True)]
    elif fault == "wrong_nonzero": bundle["failures"] = [failure("execution", "nonzero_returncode", returncode=1)]
    else: bundle["fabricated"] = 1
    with pytest.raises(ValueError):
        acquisition.validate_original_bundle(bundle, plan)


@pytest.mark.parametrize("field", ["run_id", "origin_episode_id", "resource_id", "execution_id", "request_sha256"])
def test_wrong_target_rejected_after_intent_before_manifest(tmp_path, monkeypatch, field):
    _, _, _, target = sealed_case(tmp_path, monkeypatch)
    target[field] = "0" * 64 if field == "request_sha256" else "wrong"
    monkeypatch.setattr(acquisition, "_capture_file", forbidden)
    with Store(tmp_path / "store") as store, pytest.raises(ValueError):
        acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
    assert json.loads((tmp_path / "capture/capture-intent.json").read_bytes()) == {"target": target}


@pytest.mark.parametrize("category", ["input", "working_copy", "output"])
@pytest.mark.parametrize("fault", ["bytes", "size", "missing", "symlink", "parent_symlink", "directory", "fifo"])
def test_partial_capture_preserves_valid_siblings(tmp_path, monkeypatch, category, fault):
    root, _, bundle, target = sealed_case(tmp_path, monkeypatch)
    relative = {"input": "inputs/partition_scores/1", "working_copy": "work/partition.2", "output": "outputs/stdout"}[category]
    path = root / relative
    if fault == "bytes": path.write_bytes(b"X" * path.stat().st_size)
    elif fault == "size": path.write_bytes(path.read_bytes() + b"x")
    elif fault == "parent_symlink":
        outside = tmp_path / "outside"
        shutil.move(path.parent, outside)
        path.parent.symlink_to(outside, target_is_directory=True)
    else:
        raw = path.read_bytes()
        path.unlink()
        if fault == "symlink":
            outside = tmp_path / "outside-file"
            outside.write_bytes(raw)
            path.symlink_to(outside)
        elif fault == "directory": path.mkdir()
        elif fault == "fifo": os.mkfifo(path)
    with Store(tmp_path / "store") as store:
        captured = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert captured["bundle_validated"] and not captured["complete"]
        assert captured["artifacts"] and captured["failures"]
        affected = [f for f in captured["failures"] if f["code"].endswith(relative)]
        assert len(affected) == 1
        assert ("sealed_artifact_digest_mismatch" in affected[0]["code"]) == (fault in {"bytes", "size"})
        assert bool(captured["invalid_artifacts"]) == (fault in {"bytes", "size"})
        shutil.rmtree(root.parent)
        monkeypatch.setattr(acquisition, "local_infernal_preparation_plan", forbidden)
        monkeypatch.setattr(acquisition, "_capture_file", forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture") == captured


@pytest.mark.parametrize("raw", [b"{", b"null", b"[]", b"\xff", b'{"version":1,"version":2}', b'{"a":NaN}'])
def test_bad_manifest_retained_and_replayed_without_parsing_science(tmp_path, monkeypatch, raw):
    root, _, _, target = sealed_case(tmp_path, monkeypatch)
    (root / "bundle.json").write_bytes(raw)
    with Store(tmp_path / "store") as store:
        captured = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert not captured["complete"] and not captured["bundle_validated"]
        assert store.get_artifact(captured["bundle_artifact_ref"]) == raw
        shutil.rmtree(root.parent)
        monkeypatch.setattr(acquisition, "local_infernal_preparation_plan", forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture") == captured


@pytest.mark.parametrize("state", ["native_nonzero", "input_changed", "input_missing", "partial_staging", "missing_output", "stray_output"])
def test_custody_completion_is_separate_from_native_success(tmp_path, monkeypatch, state):
    root, plan, bundle, target = sealed_case(tmp_path, monkeypatch)
    if state in {"native_nonzero", "input_changed", "missing_output", "stray_output"}:
        bundle["returncode"] = 1
        bundle["failures"] = [failure("execution", "nonzero_returncode", returncode=1)]
    if state == "input_changed":
        row = bundle["inputs"][1]
        data = b"mutated final staged input"
        (root / row["relative_path"]).write_bytes(data)
        row["final_size_bytes"], row["final_sha256"] = pair(data)
        bundle["failures"].append(failure("execution", "immutable_input_changed", row["role"], ordinal=row["ordinal"]))
    if state in {"input_missing", "partial_staging"}:
        # An unavailable/partial original cannot have an initialized copy or an invocation.
        bundle["returncode"] = None
        row, copy = bundle["inputs"][1], bundle["working_copies"][1]
        if state == "input_missing":
            (root / row["relative_path"]).unlink()
            size, sha = None, None
            bundle["failures"] = [failure("inputs", "input_missing", row["role"], ordinal=row["ordinal"])]
        else:
            data = b"part"
            (root / row["relative_path"]).write_bytes(data)
            size, sha = pair(data)
            bundle["failures"] = [failure("inputs", "input_identity_mismatch", row["role"], ordinal=row["ordinal"])]
        for prefix in ("staged", "final"):
            row[prefix + "_sha256"], row[prefix + "_size_bytes"] = sha, size
        copy["source_sha256"] = sha
        (root / copy["relative_path"]).unlink()
        for prefix in ("initial", "final"):
            copy[prefix + "_sha256"], copy[prefix + "_size_bytes"] = None, None
        bundle["failures"].append(failure("staging", "working_copy_not_staged", copy["operand_role"],
            operand_ordinal=copy["operand_ordinal"], relative_path=copy["relative_path"]))
    if state in {"missing_output", "stray_output"}:
        row = bundle["artifacts"].pop(0)
        bundle["failures"].append(failure("outputs", "missing_output", row["role"], relative_path=row["relative_path"]))
        if state == "missing_output": (root / row["relative_path"]).unlink()
    write_json(root / "bundle.json", bundle)
    assert acquisition.validate_original_bundle(bundle, plan) == bundle
    with Store(tmp_path / "store") as store:
        captured = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert captured["bundle_validated"]
        assert captured["complete"] == (state != "stray_output")
        if state == "stray_output":
            assert "unlisted_file_present:output:stdout:0:outputs/stdout" in captured["failures"][0]["code"]
        if state == "input_changed":
            item = next(r for r in captured["artifacts"] if r["direction"] == "input" and r["ordinal"] == 0 and r["role"] == "partition_scores")
            assert store.get_artifact(item["artifact_ref"]) == b"mutated final staged input"
            assert bundle["inputs"][1]["staged_sha256"] != bundle["inputs"][1]["final_sha256"]


@pytest.mark.parametrize("fault", ["role", "ordinal", "direction", "format", "path", "ref", "missing_row", "duplicate",
    "order", "flag", "failure", "invalid_category", "shared_reference"])
def test_replay_reconstructs_associations_and_completion(tmp_path, monkeypatch, fault):
    _, _, _, target = sealed_case(tmp_path, monkeypatch)
    directory = tmp_path / "capture"
    with Store(tmp_path / "store") as store:
        captured = acquisition.capture_local_bundle(store, target=target, directory=directory)
        row = captured["artifacts"][0]
        if fault == "role": row["role"] = "partition_scores"
        elif fault == "ordinal": row["ordinal"] = True
        elif fault == "direction": row["direction"] = "output"
        elif fault == "format": row["format"] = "infernal_cm_ascii"
        elif fault == "path": row["relative_path"] = "other"
        elif fault == "ref": row["artifact_ref"] = store.artifact(b"unrelated")
        elif fault == "missing_row": captured["artifacts"].pop()
        elif fault == "duplicate": captured["artifacts"].append(deepcopy(row))
        elif fault == "order": captured["artifacts"][1:3] = reversed(captured["artifacts"][1:3])
        elif fault == "flag": captured["complete"] = False
        elif fault == "failure": captured["failures"] = [{"stage": "capture", "code": "fabricated", "record_key": None}]
        elif fault == "invalid_category": captured["invalid_artifacts"].append(captured["artifacts"].pop())
        else:
            next(r for r in captured["artifacts"] if r["role"] == "calibrated_models")["artifact_ref"] = store.artifact(b"unrelated")
        (directory / "capture.json").write_text(canonical(captured) + "\n")
        monkeypatch.setattr(acquisition, "local_infernal_preparation_plan", forbidden)
        with pytest.raises(ValueError):
            acquisition.capture_local_bundle(store, target=target, directory=directory)


@pytest.mark.parametrize("fault", ["bytes", "metadata_size", "symlink", "parent_symlink"])
def test_retained_store_corruption_is_rejected(tmp_path, monkeypatch, fault):
    _, _, _, target = sealed_case(tmp_path, monkeypatch)
    directory = tmp_path / "capture"
    with Store(tmp_path / "store") as store:
        captured = acquisition.capture_local_bundle(store, target=target, directory=directory)
        ref = captured["artifacts"][0]["artifact_ref"]
        metadata = store.get(ref)
        path = store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]
        if fault == "bytes": path.write_bytes(b"corrupt")
        elif fault == "metadata_size": store.db.execute("UPDATE artifacts SET size=size+1 WHERE id=?", (ref,))
        elif fault == "symlink":
            outside = tmp_path / "outside"
            path.rename(outside)
            path.symlink_to(outside)
        else:
            outside = tmp_path / "outside"
            path.parent.rename(outside)
            path.parent.symlink_to(outside, target_is_directory=True)
        monkeypatch.setattr(acquisition, "local_infernal_preparation_plan", forbidden)
        with pytest.raises((ValueError, OSError)):
            acquisition.capture_local_bundle(store, target=target, directory=directory)


@pytest.mark.parametrize("fault", ["hpc", "wrong_workspace", "attempt_escape", "plan_digest", "capture_symlink", "manifest_symlink"])
def test_target_plan_and_filesystem_confinement(tmp_path, monkeypatch, fault):
    root, plan, _, target = sealed_case(tmp_path, monkeypatch)
    directory = tmp_path / "capture"
    if fault == "hpc": target["resource_kind"] = "hpc"
    elif fault == "wrong_workspace": target["assignment"]["workspace"] += "-other"
    elif fault == "attempt_escape": plan["attempt_directory"] = str(tmp_path / "other")
    elif fault == "plan_digest": plan["identity"]["requested_job_sha256"] = "0" * 64
    elif fault == "capture_symlink":
        outside = tmp_path / "outside"
        outside.mkdir()
        directory.symlink_to(outside, target_is_directory=True)
    else:
        (root / "bundle.json").rename(root / "actual.json")
        (root / "bundle.json").symlink_to(root / "actual.json")
    with Store(tmp_path / "store") as store:
        if fault == "manifest_symlink":
            captured = acquisition.capture_local_bundle(store, target=target, directory=directory)
            assert captured["bundle_artifact_ref"] is None and not captured["complete"]
        else:
            with pytest.raises(ValueError):
                acquisition.capture_local_bundle(store, target=target, directory=directory)


def test_source_publication_has_stable_attempt_identity_and_no_scientific_records(tmp_path, monkeypatch):
    _, _, bundle, target = sealed_case(tmp_path, monkeypatch)
    with Store(tmp_path / "store") as store:
        captured = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        grading = store.artifact(b'{"explicit":"saved supporting validation"}', "application/json")
        prepared = {"source_grading_artifact_ref": grading, "projection": {"offset": 0}}
        first = acquisition.original_source_payload(bundle=bundle, capture=captured, prepared=prepared)
        prepared["projection"] = {"offset": 99}
        assert acquisition.original_source_payload(bundle=bundle, capture=captured, prepared=prepared) == first
        source = acquisition.publish_original_source(store, bundle=bundle, capture=captured, prepared=prepared)
        assert acquisition.publish_original_source(store, bundle=bundle, capture=captured, prepared=prepared) == source
        assert first["accession"] == PREFIX + digest(bundle["identity"])
        assert first["retrieved_at"] == bundle["finished_at"] and first["provider"] == "episode.execution_result"
        assert first["auxiliary_artifact_refs"] == sorted({grading, *(r["artifact_ref"] for r in captured["artifacts"])})
        assert [r[0] for r in store.db.execute("SELECT record_type FROM records")] == ["source"]
        forged = deepcopy(bundle)
        forged["returncode"] = 9
        with pytest.raises(ValueError, match="source_bundle_association_conflict"):
            acquisition.publish_original_source(store, bundle=forged, capture=captured)


def test_saved_intent_cannot_substitute_a_new_target(tmp_path, monkeypatch):
    _, _, _, target = sealed_case(tmp_path, monkeypatch)
    with Store(tmp_path / "store") as store:
        acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        target["handle"] = "source_replacement"
        monkeypatch.setattr(acquisition, "local_infernal_preparation_plan", forbidden)
        with pytest.raises(ValueError, match="immutable_record_conflict"):
            acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")


NATIVE_CASES = sorted(p for p in (PRODUCER / "producer_001/temporary/pytest").glob(
    "test_actual_selected_native_mo*/plan.json") if not p.parent.is_symlink())
NATIVE_INDEX = json.loads((PRODUCER / "NATIVE_PRODUCER_INDEX_001.json").read_bytes())


@pytest.mark.parametrize("plan_path", NATIVE_CASES, ids=lambda p: p.parent.name)
def test_true_retained_native_mode_pure_validation(plan_path, monkeypatch):
    plan = json.loads(plan_path.read_bytes())
    bundle = json.loads((Path(plan["attempt_directory"]) / "bundle.json").read_bytes())
    for name in ("open", "stat", "resolve", "read_bytes"):
        monkeypatch.setattr(Path, name, forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    assert acquisition.validate_original_bundle(bundle, plan) == bundle


def test_native_fixture_population_is_all_27_modes():
    assert len(NATIVE_CASES) == 27
    selections = set()
    for path in NATIVE_CASES:
        plan = json.loads(path.read_bytes())
        job = plan["requested_job"]["native_infernal_preparation"]
        selections.add((job["program"], job["mode"]))
    assert len(selections) == 27


def indexed_json(row):
    raw = (ROOT / row["path"]).read_bytes()
    assert len(raw) == row["size_bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    return json.loads(raw)


@pytest.mark.parametrize("case", NATIVE_INDEX["reservations"], ids=lambda c: c["case"])
def test_true_native_original_reservation_capture_and_replay(tmp_path, monkeypatch, case):
    target, plan, bundle = (indexed_json(case[k]) for k in ("target", "plan", "bundle"))
    assert target["assignment"] == indexed_json(case["assignment"])
    indexed_json(case["native_handle"])
    indexed_json(case["native_receipt"])
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    with Store(tmp_path / "store") as store:
        captured = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert captured["bundle_validated"] and captured["complete"] and not captured["failures"]
        assert json.loads(store.get_artifact(captured["bundle_artifact_ref"])) == bundle
        assert bundle["returncode"] == case["returncode"]
        expected_rows = len(bundle["inputs"]) + len(bundle["working_copies"]) + len(bundle["artifacts"])
        assert len(captured["artifacts"]) == expected_rows
        for row in captured["artifacts"]:
            assert store.get_artifact(row["artifact_ref"]) == (Path(plan["attempt_directory"]) / row["relative_path"]).read_bytes()
        if case["case"] == "merge_scores":
            rows = [r for r in captured["artifacts"] if r["direction"] == "input" and r["role"] == "partition_scores"]
            assert [r["ordinal"] for r in rows] == [0, 1]
        if case["program"] == "cmcalibrate":
            output = next(r for r in captured["artifacts"] if r["role"] == "calibrated_models")
            copy = next(r for r in captured["artifacts"] if r["direction"] == "working_copy" and r["role"] == "models")
            assert output["artifact_ref"] == copy["artifact_ref"]
        if case["case"] == "calibration_failure":
            assert bundle["returncode"] == 1 and bundle["failures"]
        source = acquisition.publish_original_source(store, bundle=bundle, capture=captured)
        assert store.get(source)["provider"] == "episode.execution_result"
        monkeypatch.setattr(acquisition, "local_infernal_preparation_plan", forbidden)
        monkeypatch.setattr(acquisition, "_capture_file", forbidden)
        # Keep producer evidence immutable; guard reads of its entire workspace.
        original_open, original_read = Path.open, Path.read_bytes
        def guarded_open(path, *args, **kwargs):
            if path.is_relative_to(PRODUCER):
                forbidden()
            return original_open(path, *args, **kwargs)
        def guarded_read(path, *args, **kwargs):
            if path.is_relative_to(PRODUCER):
                forbidden()
            return original_read(path, *args, **kwargs)
        monkeypatch.setattr(Path, "open", guarded_open)
        monkeypatch.setattr(Path, "read_bytes", guarded_read)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture") == captured


def test_absent_original_bundle_has_immutable_failed_capture(tmp_path, monkeypatch):
    root, _, _, target = sealed_case(tmp_path, monkeypatch)
    original = (root / "bundle.json").read_bytes()
    (root / "bundle.json").unlink()
    with Store(tmp_path / "store") as store:
        captured = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture")
        assert not captured["bundle_validated"] and captured["bundle_artifact_ref"] is None
        (root / "bundle.json").write_bytes(original)
        monkeypatch.setattr(acquisition, "local_infernal_preparation_plan", forbidden)
        monkeypatch.setattr(acquisition, "_capture_file", forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / "capture") == captured
