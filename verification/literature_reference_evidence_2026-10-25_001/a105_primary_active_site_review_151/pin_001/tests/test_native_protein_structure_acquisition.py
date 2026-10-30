"""Original C manifests and byte-custody failures inside the bounded local job.

Inputs are tiny synthetic PDB fixtures. These tests establish the capture port,
not scientific parent authorization, publication or complete episode delivery.
"""
from copy import deepcopy
from importlib import import_module
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
from types import SimpleNamespace
import urllib.request

import pytest

from gene_annotation_episode import native_protein_structure_acquisition as acquisition
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_protein_structure_contracts import (
    POLICY, BUNDLE_FILENAME, RUN_PLAN_FILENAME, requested_job_from_protein_structure,
    validate_protein_structure_request,
)
from gene_annotation_episode.native_protein_structure_driver import run_protein_structure_driver
from gene_annotation_episode.native_protein_structure_local import (
    prepare_local_protein_structure, local_protein_structure_plan,
)
from gene_annotation_episode.protein_structure_contracts import issue, validate_file_identity
from gene_annotation_episode.state import Store

F = import_module("verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers")


def encoded(value):
    return canonical(value).encode("utf-8")


def forbidden(*args, **kwargs):
    pytest.fail("capture used a forbidden scientific, network, producer or lifecycle operation")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    import requests
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)


def case(tmp_path, kind="inspect", *, absent=False, nonzero=False, metadata=False):
    selected = F.job(tmp_path / "selected-inputs", kind=kind,
        **({"fixed_kwargs": {"sequence": "XGST"}} if absent else {}))
    if metadata:
        document = {"version": "protein_structure_metadata_v1", "semantics_declarations": [], "metric_unit_declarations": []}
        for raw in (encoded(document), b" " + encoded(document)):
            identity = F.identity(raw, "protein_structure_metadata_v1")
            index = len(selected["inputs"])
            path = tmp_path / ("metadata-" + str(index) + ".json")
            path.write_bytes(raw)
            selected["request"]["supplied_metadata_files"].append(identity)
            selected["inputs"].append({"input_id": "input_" + str(index), "role": "supplied_metadata",
                "file_identity": identity, "path": str(path), "staged_relative_path": "inputs/input_" + str(index)})
    if nonzero:
        fault = tmp_path / "deliberate-exit-fault"
        fault.mkdir()
        source = fault / "sitecustomize.py"
        source.write_bytes(b"import atexit, os\natexit.register(lambda: os._exit(9))\n")
        source.chmod(0o444)
        selected["environment"]["PYTHONPATH"] = str(fault) + ":" + str(F.REPO)
    requested = requested_job_from_protein_structure(selected)
    assignment = {"resource_kind": "local", "resource_id": "local-capture", "workspace": str(tmp_path),
        "requested_job": requested, "constraints": {"allocation": deepcopy(POLICY)}}
    state = SimpleNamespace(assignment=assignment, run_id="capture-rün", episode_id="original-épisode")
    root = tmp_path / ".episode-operations" / digest({"run": state.run_id, "episode": state.episode_id}) / digest("selected-start")
    handle = prepare_local_protein_structure(state, "selected-start", root=root, policy=LocalJobPolicy(**POLICY))
    plan = local_protein_structure_plan(assignment, str(handle.path))
    # This is actual C execution within the enclosing local_jobs process/cgroup.
    # Its prepared identity is sufficient for the pure capture target; lifecycle
    # completion is not used to infer native success or capture completeness.
    bundle = run_protein_structure_driver(plan)
    target = {"version": "execution_target_v1", "handle": "selected-protein-work", "run_id": state.run_id,
        "resource_id": "local-capture", "resource_kind": "local", "execution_id": str(handle.path),
        "request_sha256": digest(requested), "origin_episode_id": state.episode_id,
        "assignment": assignment, "scope": {}}
    return SimpleNamespace(target=target, plan=plan, bundle=bundle, root=root,
        attempt=Path(plan["attempt_directory"]), producer=tmp_path)


def guard_capture(monkeypatch, *, replay=False, producer=None):
    for module, names in (
        ("native_protein_structure_driver", ["run_protein_structure_driver"]),
        ("native_protein_structure_worker", ["execute_protein_structure_request"]),
        ("native_protein_structure_local", ["prepare_local_protein_structure"]),
        ("protein_structure_calculations", ["calculate_protein_structure_components", "fit_ca_transform"]),
        ("protein_structure_sheet", ["build_protein_structure_sheet", "parse_native_protein_comparison"]),
        ("native_lifecycle", ["prepare_job", "start_prepared", "start_job", "resume_start", "status", "collect", "wait_job"]),
    ):
        loaded = import_module("gene_annotation_episode." + module)
        for name in names:
            monkeypatch.setattr(loaded, name, forbidden)
    if replay:
        monkeypatch.setattr("gene_annotation_episode.native_protein_structure_local.local_protein_structure_plan", forbidden)
        monkeypatch.setattr(acquisition, "_producer_file", forbidden)
        monkeypatch.setattr(native.NativeJobHandle, "read", forbidden)
        original_open, original_resolve, original_io_open = os.open, Path.resolve, io.open

        def no_producer(path):
            return not isinstance(path, (str, Path)) or not Path(path).is_relative_to(producer)

        def checked_os_open(path, *args, **kwargs):
            full = path
            if kwargs.get("dir_fd") is not None:
                full = Path(os.readlink("/proc/self/fd/" + str(kwargs["dir_fd"]))) / path
            assert no_producer(full), "replay opened producer path"
            return original_open(path, *args, **kwargs)

        def checked_resolve(path, *args, **kwargs):
            assert no_producer(path), "replay resolved producer path"
            return original_resolve(path, *args, **kwargs)

        def checked_io_open(path, *args, **kwargs):
            assert no_producer(path), "replay read producer bytes"
            return original_io_open(path, *args, **kwargs)

        monkeypatch.setattr(os, "open", checked_os_open)
        monkeypatch.setattr(Path, "resolve", checked_resolve)
        monkeypatch.setattr(io, "open", checked_io_open)


def capture(store, f, directory):
    return acquisition.capture_local_protein_structure_bundle(store, target=f.target, directory=directory)


def retain_example(directory, name, f, result):
    (directory / (name + ".json")).write_bytes(encoded({"target": f.target, "bundle": f.bundle, "capture": result}))


@pytest.mark.parametrize("kind", ["inspect", "extract_sequence", "compare"])
def test_actual_manifests_capture_every_original_association(tmp_path, monkeypatch, kind):
    f = case(tmp_path / "producer", kind)
    original = {r["relative_path"]: (f.attempt / r["relative_path"]).read_bytes() for r in f.bundle["files"]}
    guard_capture(monkeypatch)
    with Store(tmp_path / "store") as store:
        monkeypatch.setattr(store, "put", forbidden)
        result = capture(store, f, tmp_path / "capture")
        assert result["capture_complete"] and result["bundle_validated"] and not result["failures"]
        assert result["original_plan"] == f.plan
        assert [r["declared"] for r in result["files"]] == f.bundle["files"]
        for index, row in enumerate(result["files"]):
            assert row["manifest_index_0based"] == index and row["outcome"] == "verified" and row["issue"] is None
            assert row["observed"]["format"] == row["declared"]["format"]
            assert acquisition.retained_protein_structure_file(store, row["observed"]).read_bytes() == original[row["declared"]["relative_path"]]
        assert acquisition.retained_protein_structure_file(store, result["bundle_file"]).read_bytes() == encoded(f.bundle)
        checked = acquisition.validate_protein_structure_capture(store, result, target=f.target)
        checked["files"][0]["declared"]["role"] = "stderr"
        assert result["files"][0]["declared"]["role"] != "stderr"
        for filename, value in (("capture-intent.json", {"target": f.target}), ("capture.json", result)):
            assert (tmp_path / "capture" / filename).read_bytes() == encoded(value)
            assert b"capture-r\xc3\xbcn" in (tmp_path / "capture" / filename).read_bytes()
        retain_example(tmp_path, "filled-" + kind, f, result)


def test_exact_replay_after_deleting_all_producer_bytes(tmp_path, monkeypatch):
    f = case(tmp_path / "producer", "extract_sequence")
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        before = (tmp_path / "capture/capture.json").read_bytes()
        shutil.rmtree(f.producer)
        guard_capture(monkeypatch, replay=True, producer=f.producer)
        assert capture(store, f, tmp_path / "capture") == result
        assert acquisition.validate_protein_structure_capture(store, result, target=f.target) == result
        assert (tmp_path / "capture/capture.json").read_bytes() == before
        retain_example(tmp_path, "producer-independent-replay", f, result)


@pytest.mark.parametrize("kind", ["absence", "nonzero"])
def test_native_failure_and_declared_absence_are_complete_custody(tmp_path, monkeypatch, kind):
    f = case(tmp_path / "producer", "extract_sequence" if kind == "absence" else "inspect",
        absent=kind == "absence", nonzero=kind == "nonzero")
    assert f.bundle["native_status"] == "partial"
    assert f.bundle["returncode"] == (0 if kind == "absence" else 9)
    guard_capture(monkeypatch)
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        assert result["capture_complete"] and result["failures"] == []
        absent = [r for r in result["files"] if r["outcome"] == "declared_absent"]
        assert len(absent) == (1 if kind == "absence" else 0)
        if absent:
            assert absent[0]["declared"]["role"] == "sequence"
            assert absent[0]["observed"] is None and absent[0]["issue"] is None
        else:
            assert any(r["declared"]["role"] == "native_result" and r["outcome"] == "verified" for r in result["files"])
        retain_example(tmp_path, "complete-custody-" + kind, f, result)


def test_repeated_roles_and_missing_files_keep_distinct_ordered_rows(tmp_path, monkeypatch):
    f = case(tmp_path / "producer", "extract_sequence", metadata=True)
    metadata = [r for r in f.bundle["files"] if r["role"] == "supplied_metadata"]
    assert len(metadata) == 2 and metadata[0]["input_id"] != metadata[1]["input_id"]
    for row in metadata:
        (f.attempt / row["relative_path"]).unlink()
    guard_capture(monkeypatch)
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        missing = [r for r in result["files"] if r["outcome"] == "unavailable"]
        assert [r["declared"] for r in missing] == metadata
        assert len(result["failures"]) == 2 and result["failures"][0] == result["failures"][1]
        assert not result["capture_complete"]
        retain_example(tmp_path, "repeated-role-failures", f, result)


@pytest.mark.parametrize("problem", ["changed", "missing", "symlink_file", "symlink_directory", "fifo", "directory"])
def test_changed_or_unavailable_present_file_is_never_verified(tmp_path, monkeypatch, problem):
    f = case(tmp_path / "producer")
    target = f.attempt / "inputs/input_0" if problem == "symlink_directory" else f.attempt / "result.json"
    if problem == "symlink_directory":
        original = f.attempt / "inputs"
        other = f.attempt / "original-inputs"
        original.rename(other)
        original.symlink_to(other, target_is_directory=True)
    else:
        target.unlink()
        if problem == "changed": target.write_bytes(b"changed native bytes\x00\xff")
        elif problem == "symlink_file": target.symlink_to(f.attempt / "stdout.log")
        elif problem == "fifo": os.mkfifo(target)
        elif problem == "directory": target.mkdir()
    guard_capture(monkeypatch)
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        assert result["bundle_validated"] and not result["capture_complete"]
        bad = [r for r in result["files"] if r["issue"] is not None]
        assert len(bad) == 1
        row = bad[0]
        assert row["outcome"] == ("digest_mismatch" if problem == "changed" else "unavailable")
        assert row["issue"]["code"] == ("input_digest_mismatch" if problem == "changed" else "capture_incomplete")
        if problem == "changed":
            assert acquisition.retained_protein_structure_file(store, row["observed"]).read_bytes() == b"changed native bytes\x00\xff"
            assert row["observed"]["sha256"] != row["declared"]["sha256"]
        else:
            assert row["observed"] is None
        # Final incomplete captures never acquire a replacement from the producer.
        guard_capture(monkeypatch, replay=True, producer=f.producer)
        assert capture(store, f, tmp_path / "capture") == result
        retain_example(tmp_path, "capture-" + problem, f, result)


@pytest.mark.parametrize("mutation,code", [
    (lambda b: b.update(sealed=False), "invalid_schema"),
    (lambda b: b["identity"].update(episode_id="foreign"), "original_commission_mismatch"),
    (lambda b: b["files"][0].update(relative_path="../foreign"), "original_commission_mismatch"),
    (lambda b: b["files"].pop(), "capture_incomplete"),
    (lambda b: b["files"][0].update(byte_length=1.0), "invalid_schema"),
    (lambda b: b["files"][0].update(byte_length=True), "invalid_schema"),
    (lambda b: b["files"][0].update(unexpected=True), "invalid_schema"),
])
def test_invalid_manifest_retains_only_bundle_bytes(tmp_path, monkeypatch, mutation, code):
    f = case(tmp_path / "producer")
    malformed = deepcopy(f.bundle)
    mutation(malformed)
    (f.attempt / BUNDLE_FILENAME).write_bytes(encoded(malformed))
    guard_capture(monkeypatch)
    original = acquisition._producer_file

    def only_bundle(directory, relative):
        assert relative == BUNDLE_FILENAME, "invalid manifest authorized a file read"
        return original(directory, relative)

    monkeypatch.setattr(acquisition, "_producer_file", only_bundle)
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        assert not result["bundle_validated"] and not result["capture_complete"] and result["files"] == []
        assert result["original_plan"] == f.plan
        assert result["failures"] == [issue(code, stage="capture", field="manifest")]
        assert acquisition.retained_protein_structure_file(store, result["bundle_file"]).read_bytes() == encoded(malformed)
        assert capture(store, f, tmp_path / "capture") == result


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":1e999}', b'\xff', b'{}\n', b'\xef\xbb\xbf{}'])
def test_malformed_original_bundle_is_retained_and_never_expanded(tmp_path, raw):
    f = case(tmp_path / "producer")
    (f.attempt / BUNDLE_FILENAME).write_bytes(raw)
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        assert result["files"] == [] and not result["bundle_validated"]
        assert acquisition.retained_protein_structure_file(store, result["bundle_file"]).read_bytes() == raw
        assert result["failures"][0]["code"] == "invalid_schema"


@pytest.mark.parametrize("problem", ["missing", "symlink"])
def test_unavailable_bundle_keeps_qualified_plan_and_no_trusted_files(tmp_path, problem):
    f = case(tmp_path / "producer")
    bundle = f.attempt / BUNDLE_FILENAME
    bundle.unlink()
    if problem == "symlink": bundle.symlink_to(f.attempt / "result.json")
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        assert result["original_plan"] == f.plan and result["bundle_file"] is None
        assert not result["bundle_validated"] and result["files"] == []
        assert capture(store, f, tmp_path / "capture") == result


@pytest.mark.parametrize("problem", ["invalid_plan", "foreign_plan", "operation_directory", "producer_symlink"])
def test_failed_plan_qualification_never_opens_bundle(tmp_path, monkeypatch, problem):
    f = case(tmp_path / "producer")
    if problem == "invalid_plan":
        (f.root / RUN_PLAN_FILENAME).write_bytes(b"{}")
    elif problem == "foreign_plan":
        f.target["origin_episode_id"] = "other-original-episode"
    elif problem == "operation_directory":
        f.target["assignment"]["workspace"] = str(tmp_path / "other-workspace")
    else:
        other = f.attempt.with_name("original-attempt")
        f.attempt.rename(other)
        f.attempt.symlink_to(other, target_is_directory=True)
    monkeypatch.setattr(acquisition, "_producer_file", forbidden)
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        assert result["original_plan"] is None and result["bundle_file"] is None
        assert result["files"] == [] and not result["capture_complete"]
        assert result["failures"][0]["stage"] == "capture"
        assert result["failures"][0]["field"] == "request"


def test_qualifier_is_pure_and_checks_each_original_identity(tmp_path, monkeypatch):
    f = case(tmp_path / "producer")
    monkeypatch.setattr(Path, "resolve", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(os, "open", forbidden)
    result = acquisition.qualify_protein_structure_target_plan(f.target, f.plan)
    assert result == f.plan and result is not f.plan
    for field in ("run_id", "origin_episode_id", "resource_id", "execution_id", "request_sha256"):
        changed = deepcopy(f.target)
        changed[field] = "a" * 64 if field == "request_sha256" else (
            "/wrong/native.json" if field == "execution_id" else "wrong")
        with pytest.raises(ValueError): acquisition.qualify_protein_structure_target_plan(changed, f.plan)
    result["identity"]["operation_key"] = "detached"
    assert f.plan["identity"]["operation_key"] == "selected-start"


@pytest.mark.parametrize("mutation", [
    lambda c: c.update(extra=None), lambda c: c.update(capture_complete=1),
    lambda c: c.update(bundle_validated=1), lambda c: c["files"][0].update(manifest_index_0based=True),
    lambda c: c["files"][0].update(manifest_index_0based=0.0),
    lambda c: c["files"][0]["observed"].update(byte_length=float(c["files"][0]["observed"]["byte_length"])),
    lambda c: c["files"][0]["observed"].update(format="text"),
    lambda c: c["files"].reverse(), lambda c: c["files"].pop(),
    lambda c: c["files"][0].update(issue=issue("capture_incomplete", stage="capture")),
    lambda c: c.update(bundle_validated=False, files=[], capture_complete=False,
        failures=[issue("invalid_schema", stage="capture", field="manifest")]),
])
def test_capture_shape_counts_and_manifest_relationships_are_strict(tmp_path, mutation):
    f = case(tmp_path / "producer")
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        mutation(result)
        with pytest.raises(ValueError): acquisition.validate_protein_structure_capture(store, result, target=f.target)


@pytest.mark.parametrize("problem", ["missing", "tampered", "metadata_size", "metadata_digest"])
def test_lost_or_corrupt_retained_bytes_fail_without_reacquisition(tmp_path, monkeypatch, problem):
    f = case(tmp_path / "producer")
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        identity = result["files"][0]["observed"]
        retained = acquisition.retained_protein_structure_file(store, identity)
        if problem == "missing": retained.unlink()
        elif problem == "tampered": retained.write_bytes(b"corrupted stored bytes")
        elif problem == "metadata_size": store.db.execute("UPDATE artifacts SET size=size+1 WHERE id=?", (identity["artifact_ref"],))
        else: store.db.execute("UPDATE artifacts SET sha256=? WHERE id=?", ("0" * 64, identity["artifact_ref"]))
        guard_capture(monkeypatch, replay=True, producer=f.producer)
        with pytest.raises(ValueError, match="^retained_artifact_missing$" if problem == "missing" else "^input_digest_mismatch$"):
            capture(store, f, tmp_path / "capture")


def test_conflicting_or_missing_intent_and_corrupt_control_are_errors(tmp_path, monkeypatch):
    f = case(tmp_path / "producer")
    with Store(tmp_path / "store") as store:
        capture(store, f, tmp_path / "capture")
        saved = (tmp_path / "capture/capture.json").read_bytes()
        guard_capture(monkeypatch, replay=True, producer=f.producer)
        wrong = deepcopy(f.target)
        wrong["handle"] = "another-selected-target"
        with pytest.raises(ValueError, match="original_commission_mismatch"):
            acquisition.capture_local_protein_structure_bundle(store, target=wrong, directory=tmp_path / "capture")
        assert (tmp_path / "capture/capture.json").read_bytes() == saved
        (tmp_path / "capture/capture-intent.json").unlink()
        with pytest.raises(ValueError, match="original_commission_mismatch"): capture(store, f, tmp_path / "capture")
        (tmp_path / "capture/capture-intent.json").write_bytes(encoded({"target": f.target}))
        (tmp_path / "capture/capture.json").chmod(0o600)
        (tmp_path / "capture/capture.json").write_bytes(saved + b"\n")
        with pytest.raises(ValueError, match="invalid_schema"): capture(store, f, tmp_path / "capture")


def test_invalid_caller_and_result_paths_fail_before_capture(tmp_path, monkeypatch):
    f = case(tmp_path / "producer")
    monkeypatch.setattr("gene_annotation_episode.native_protein_structure_local.local_protein_structure_plan", forbidden)
    with Store(tmp_path / "store") as store:
        for target in ({}, {**f.target, "resource_kind": "api"}, {**f.target, "request_sha256": "0" * 64}):
            with pytest.raises(ValueError):
                acquisition.capture_local_protein_structure_bundle(store, target=target, directory=tmp_path / "unused")
        assert not (tmp_path / "unused").exists()
        for directory in (Path("relative"), tmp_path / ".." / "escape"):
            with pytest.raises(ValueError, match="invalid_output_path"):
                acquisition.capture_local_protein_structure_bundle(store, target=f.target, directory=directory)
        (tmp_path / "other").mkdir()
        (tmp_path / "symlink").symlink_to(tmp_path / "other", target_is_directory=True)
        with pytest.raises(ValueError, match="invalid_output_path"):
            capture(store, f, tmp_path / "symlink/capture")


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'NaN', b'Infinity', b'-Infinity', b'1e999',
    b'\xff', b'{', b'{}{}', b'"\\ud800"', b'\xef\xbb\xbf{}'])
def test_json_decoder_rejects_invalid_content(raw):
    with pytest.raises(ValueError, match="invalid_schema"): acquisition.decode_protein_structure_json(raw)


def test_json_decoder_exact_unicode_canonical_and_typed_arguments():
    value = {"β": "résidu", "integer": 2}
    assert acquisition.decode_protein_structure_json(encoded(value), canonical_bytes=True) == value
    for raw in (encoded(value) + b"\n", json.dumps(value).encode(), b'{ "integer":2,"\xce\xb2":"r\xc3\xa9sidu"}'):
        assert acquisition.decode_protein_structure_json(raw) == value
        with pytest.raises(ValueError): acquisition.decode_protein_structure_json(raw, canonical_bytes=True)
    for raw in ("{}", bytearray(b"{}"), None):
        with pytest.raises(ValueError): acquisition.decode_protein_structure_json(raw)
    with pytest.raises(ValueError): acquisition.decode_protein_structure_json(b"{}", canonical_bytes=1)


def test_shared_file_formats_and_wrong_operation_format(tmp_path):
    with Store(tmp_path / "store") as store:
        raw = b"one retained byte stream"
        reference = store.artifact(raw)
        formats = ["native_protein_structure_bundle_v1", "native_protein_structure_run_plan_v1",
            "protein_structure_worker_input_v1", "protein_structure_native_v1",
            "protein_structure_inventory_native_v1", "protein_structure_sequence_native_v1", "text"]
        for format in formats:
            identity = {"artifact_ref": reference, "sha256": reference.removeprefix("artifact_"), "byte_length": len(raw), "format": format}
            assert validate_file_identity(identity) == identity
            assert acquisition.retained_protein_structure_file(store, identity).read_bytes() == raw
            request = {"version": "protein_structure_inspect_request_v1", "operation": "inspect", "structure_file": identity,
                "inventory": {"blocks": {"kind": "all"}, "include": ["models"]}}
            with pytest.raises(ValueError, match="unsupported_format"): validate_protein_structure_request(request)
        identity["format"] = "invented_format"
        with pytest.raises(ValueError, match="invalid_schema"): acquisition.retained_protein_structure_file(store, identity)


@pytest.mark.parametrize("component", ["file", "directory"])
def test_producer_substitution_after_open_uses_pinned_descriptor(tmp_path, monkeypatch, component):
    f = case(tmp_path / "producer")
    original = acquisition.artifact_file
    expected = (f.attempt / "inputs/input_0").read_bytes()
    replaced = []

    def substitute(store, path, *args, **kwargs):
        if not replaced and os.readlink(path).endswith("/inputs/input_0"):
            victim = f.attempt / ("inputs/input_0" if component == "file" else "inputs")
            moved = victim.with_name(victim.name + "-original")
            victim.rename(moved)
            if component == "file":
                malicious = f.attempt / "replacement-bytes"
                malicious.write_bytes(b"replacement must not be captured")
            else:
                malicious = f.attempt / "replacement-directory"
                malicious.mkdir()
                (malicious / "input_0").write_bytes(b"replacement must not be captured")
            victim.symlink_to(malicious, target_is_directory=component == "directory")
            replaced.append((victim, moved))
        return original(store, path, *args, **kwargs)

    monkeypatch.setattr(acquisition, "artifact_file", substitute)
    with Store(tmp_path / "store") as store:
        result = capture(store, f, tmp_path / "capture")
        assert replaced and result["capture_complete"]
        assert acquisition.retained_protein_structure_file(store, result["files"][0]["observed"]).read_bytes() == expected
