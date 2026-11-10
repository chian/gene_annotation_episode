"""Producer/custody engineering fixtures, not native BLAST measurements.

Every selected subprocess is replaced with an explicit controlled fixture here.
Native format evidence belongs to retained084/085 and separately selected runs.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_blast_utility_driver as driver
from gene_annotation_episode import native_blast_utility_local as local
from gene_annotation_episode import native_blast_utility_acquisition as acquisition
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_blast_utility_contracts import (
    ATTEMPT_NAME, BUNDLE_NAME, BUNDLE_VERSION, OWNER_NAME, PLAN_VERSION,
    database_file_selections, native_blast_digest, requested_job_from_native_blast_utility,
    staged_relative, validate_native_blast_utility_bundle, validate_native_blast_utility_plan,
)
from gene_annotation_episode.native_infernal_driver import _atomic_new, _encoded
from gene_annotation_episode.practical_execution_records import canonical
from gene_annotation_episode.state import Store
from test_blast_utility_contracts_625 import operation


POLICY = {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
FAMILY = {"nhr": b"fixture header", "nin": b"fixture index", "nsq": b"fixture symbols",
          "ndb": b"fixture v5 member", "njs": b'{"fixture_only":true}', "future-member": b"retain this too"}


def identity(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), "artifact_ref": None}


def job_fixture(tmp_path, mode="create_sequence_database"):
    source = tmp_path / "selected"
    software = identity(source / operation(mode)["program"], b"fixture software: never executed\n")
    Path(software["path"]).chmod(0o755)
    job = {"version": "native_blast_utility_job_v1", "operation": operation(mode),
        "software": {"executable": software["path"], "sha256": software["sha256"], "engine_version": "fixture-only"},
        "environment": {"BLAST_USAGE_REPORT": "false", "NCBI_DONT_USE_NCBIRC": "1"}, "inputs": [], "databases": [],
        "outputs": [{"role": "stdout", "path_kind": "file", "relative_path": "logs/native.stdout", "format": {
            "create_sequence_database": "text", "extract_sequences": "blastdbcmd_tabular_v1", "info": "blastdb_info_text",
            "metadata": "blastdb_metadata_json", "integrity": "blastdbcheck_text"}[mode]},
            {"role": "stderr", "path_kind": "file", "relative_path": "logs/native.stderr", "format": "text"}]}
    if mode == "create_sequence_database":
        fasta = identity(source / "supplied.fa", b">ALPHA\nACGTACGT\n")
        job["inputs"] = [{**fasta, "input_key": "source", "role": "sequence_input", "format": "fasta"}]
        job["outputs"].append({"role": "database_family", "path_kind": "prefix", "relative_path": "db/tiny", "format": "blastdb_family"})
    else:
        files = [identity(source / ("tiny." + suffix), data) for suffix, data in FAMILY.items()]
        receipt = identity(source / "receipt.json", b'{"fixture_only":"preparation"}')
        metadata = identity(source / "metadata.json", b'{"fixture_only":"metadata"}')
        inputs = identity(source / "input-manifest.json", b'{"fixture_only":"inputs"}')
        offline = identity(source / "offline.ini", b"fixture_only=true\n")
        provenance = {"source_ref": "source_fixture_only", "pointer": ""}
        db_identity = {"namespace": "fixture", "value": "tiny", "version": None, "release": None,
            "scope": None, "preparation_type": "sequence_database", "source": provenance}
        manifest = {"version": "native_blast_standard_prepared_database_manifest_v1", "database_key": "tiny",
            "kind": "blast_nucleotide_sequence", "identity": db_identity, "native_paths": [str(source / "tiny")],
            "files": [{k: v for k, v in f.items() if k != "artifact_ref"} for f in files],
            "preparation": {"method": "other_recorded", "preparation_type": "sequence_database",
                "software": {"name": "fixture-only", "version": None, "executable_sha256": None},
                "argv": None, "source": provenance, "input_manifest": inputs, "receipt": receipt},
            "metadata_manifests": [metadata], "access": {"mode": "prepared_local", "offline_configuration": offline},
            "inventory_complete": True}
        manifest_file = identity(source / "prepared.json", json.dumps(manifest, sort_keys=True).encode())
        job["databases"] = [{"database_key": "tiny", "role": "target", "kind": manifest["kind"], "identity": db_identity,
            "native_paths": manifest["native_paths"], "manifest_file": manifest_file, "manifest": manifest}]
    return job


def plan_fixture(tmp_path, job=None, *, root=None, operation_key="selected-operation"):
    job = job_fixture(tmp_path) if job is None else job
    request = requested_job_from_native_blast_utility(job)
    root = tmp_path / "reservation" if root is None else root
    root.mkdir(parents=True, exist_ok=True)
    return {"version": PLAN_VERSION, "identity": {"run_id": "run-fixture", "episode_id": "episode-fixture",
        "resource_id": "local-fixture", "execution_id": str(root / "native.json"),
        "attempt_id": native_blast_digest(operation_key), "operation_key": operation_key,
        "requested_job_sha256": native_blast_digest(request)}, "requested_job": request,
        "attempt_directory": str(root / ATTEMPT_NAME), "policy": deepcopy(POLICY)}


def controlled_native(monkeypatch, *, returncode=0, family=None, after=None):
    calls = []
    def selected(argv, **kwargs):
        calls.append((list(argv), kwargs))
        assert kwargs["stdin"] == driver.subprocess.DEVNULL
        assert kwargs["check"] is False
        assert set(kwargs) == {"cwd", "env", "stdin", "stdout", "stderr", "check"}
        kwargs["stdout"].write(b"controlled utility fixture\n")
        kwargs["stderr"].write(b"controlled failure\n" if returncode else b"")
        if "-out" in argv:
            prefix = Path(argv[argv.index("-out") + 1])
            for suffix, data in (FAMILY if family is None else family).items():
                Path(str(prefix) + "." + suffix).write_bytes(data)
        if after:
            after(argv, kwargs)
        return SimpleNamespace(returncode=returncode)
    monkeypatch.setattr(driver.subprocess, "run", selected)
    return calls


def reserved_fixture(tmp_path, monkeypatch, *, job=None):
    job = job_fixture(tmp_path) if job is None else job
    request = requested_job_from_native_blast_utility(job)
    assignment = {"workspace": str(tmp_path), "resource_kind": "local", "resource_id": "local-fixture",
        "requested_job": request, "constraints": {"allocation": deepcopy(POLICY)}}
    state = SimpleNamespace(run_id="run-fixture", episode_id="episode-fixture", assignment=assignment)
    operation_key = "selected-operation"
    root = tmp_path / ".episode-operations" / native_blast_digest({"run": state.run_id, "episode": state.episode_id}) / native_blast_digest(operation_key)
    root.mkdir(parents=True)
    monkeypatch.setattr(local.native, "start_prepared", lambda *a, **k: pytest.fail("reservation dispatched a command"))
    handle = local.prepare_local_blast_utility(state, operation_key, root=root, policy=LocalJobPolicy(**POLICY))
    plan = local.local_blast_utility_plan(assignment, str(handle.path))
    target = {"version": "execution_target_v1", "handle": "execution-fixture", "run_id": state.run_id,
        "resource_id": assignment["resource_id"], "resource_kind": "local", "execution_id": str(handle.path),
        "request_sha256": native_blast_digest(request), "origin_episode_id": state.episode_id,
        "assignment": assignment, "scope": {}, "attempt_id": plan["identity"]["attempt_id"],
        "original_operation_key": operation_key}
    return state, handle, plan, target


def sealed_fixture(tmp_path, monkeypatch, **native_options):
    state, handle, plan, target = reserved_fixture(tmp_path, monkeypatch)
    calls = controlled_native(monkeypatch, **native_options)
    bundle = driver.run_native_blast_utility(plan)
    assert len(calls) == 1
    return state, handle, plan, target, bundle


def test_plan_validation_is_detached_and_pure(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("pure plan validation performed IO")
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "resolve", forbidden)
    monkeypatch.setattr(driver.subprocess, "run", forbidden)
    result = validate_native_blast_utility_plan(plan)
    assert result == plan and result is not plan
    result["identity"]["run_id"] = "other"
    assert plan["identity"]["run_id"] == "run-fixture"


@pytest.mark.parametrize("change", [
    lambda p: p.update(unselected=True),
    lambda p: p["identity"].update(attempt_id="a" * 64),
    lambda p: p["identity"].update(requested_job_sha256="b" * 64),
    lambda p: p["identity"].update(execution_id="/other/native.json"),
    lambda p: p.update(attempt_directory="/other/blast-utility-attempt"),
    lambda p: p["policy"].update(memory_bytes=True),
    lambda p: p["policy"].update(scratch_bytes=0),
    lambda p: p["policy"].update(wall_seconds=float("nan")),
    lambda p: p["requested_job"]["argv"].append("-unselected"),
])
def test_plan_rejects_unselected_or_invalid_reservation(tmp_path, change):
    plan = plan_fixture(tmp_path)
    change(plan)
    with pytest.raises(ValueError):
        validate_native_blast_utility_plan(plan)


def test_builder_retains_every_family_member_and_exact_selection(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    calls = controlled_native(monkeypatch)
    bundle = driver.run_native_blast_utility(plan)
    assert bundle["version"] == BUNDLE_VERSION
    assert bundle["started"] and bundle["writer_closed"] and bundle["inventory_complete"]
    assert bundle["returncode"] == 0 and bundle["failures"] == [] and len(calls) == 1
    files = [row for row in bundle["artifacts"] if row["role"].startswith("database_")]
    assert {Path(row["relative_path"]).suffix[1:] for row in files} == set(FAMILY)
    metadata, = [row for row in files if row["role"] == "database_metadata"]
    assert metadata["format"] == "blastdb_metadata_json"
    source = bundle["inputs"][0]
    assert source["staged_sha256"] == source["expected_sha256"] == source["final_sha256"]
    assert (Path(plan["attempt_directory"]) / source["relative_path"]).stat().st_mode & 0o222 == 0
    assert calls[0][0] == bundle["realized_argv"]
    assert calls[0][1]["env"] == bundle["environment"]
    assert "PATH" not in bundle["environment"]
    assert validate_native_blast_utility_bundle(bundle, plan) == bundle


@pytest.mark.parametrize("mode", ["extract_sequences", "info", "metadata", "integrity"])
def test_inspection_retains_complete_selected_dependency_closure(tmp_path, monkeypatch, mode):
    job = job_fixture(tmp_path, mode)
    plan = plan_fixture(tmp_path, job)
    before = {row["original_path"]: Path(row["original_path"]).read_bytes() for row in database_file_selections(job)}
    calls = controlled_native(monkeypatch)
    bundle = driver.run_native_blast_utility(plan)
    assert len(calls) == 1 and bundle["failures"] == []
    assert bundle["inputs"] == []
    assert {row["role"] for row in bundle["database_files"]} == {
        "manifest", "database_file", "preparation_receipt", "metadata_manifest", "input_manifest", "offline_configuration"}
    assert len(bundle["database_files"]) == len(FAMILY) + 5
    for row in bundle["database_files"]:
        assert row["before_sha256"] == row["expected_sha256"] == row["final_sha256"]
        assert Path(row["original_path"]).read_bytes() == before[row["original_path"]]
    assert calls[0][0][calls[0][0].index("-db") + 1] == job["databases"][0]["native_paths"][0]
    assert list((Path(plan["attempt_directory"]) / "inputs").iterdir()) == []


@pytest.mark.parametrize("change", [
    lambda b: b["identity"].update(episode_id="other"),
    lambda b: b["operation"]["parameters"].update(title="other"),
    lambda b: b["realized_argv"].append("-unselected"),
    lambda b: b["environment"].update(PATH="/discovery"),
    lambda b: b["software"].update(actual_sha256="e" * 64),
    lambda b: b.update(returncode=True),
    lambda b: b.update(started=False),
    lambda b: b.update(writer_closed=False),
    lambda b: b.update(inventory_complete=False),
    lambda b: b.update(finished_at="2026-01-01T00:00:00-05:00"),
    lambda b: b["inputs"][0].update(staged_size_bytes=True),
    lambda b: b["inputs"][0].update(final_sha256=None),
    lambda b: b["inputs"][0].update(relative_path="inputs/unselected.fa"),
    lambda b: b["artifacts"][0].update(relative_path="../unselected"),
    lambda b: b["artifacts"][0].update(ordinal=True),
    lambda b: b["artifacts"][0].update(completeness="partial"),
    lambda b: b["artifacts"].append(deepcopy(b["artifacts"][-1])),
    lambda b: b["artifacts"].pop(0),
    lambda b: b["failures"].append({"stage": "execution", "code": "nonzero_returncode", "input_key": None, "database_key": None, "relative_path": None}),
])
def test_bundle_rejects_tampered_original_relationships(tmp_path, monkeypatch, change):
    plan = plan_fixture(tmp_path)
    controlled_native(monkeypatch)
    bundle = driver.run_native_blast_utility(plan)
    change(bundle)
    with pytest.raises(ValueError):
        validate_native_blast_utility_bundle(bundle, plan)


@pytest.mark.parametrize("failure", ["missing_software", "software_digest", "not_executable", "missing_input", "input_digest", "scratch"])
def test_preflight_failures_preserve_actual_bytes_without_invocation(tmp_path, monkeypatch, failure):
    job = job_fixture(tmp_path)
    if failure == "missing_software": Path(job["software"]["executable"]).unlink()
    if failure == "software_digest": job["software"]["sha256"] = "a" * 64
    if failure == "not_executable": Path(job["software"]["executable"]).chmod(0o644)
    if failure == "missing_input": Path(job["inputs"][0]["path"]).unlink()
    if failure == "input_digest": job["inputs"][0]["sha256"] = "b" * 64
    plan = plan_fixture(tmp_path, job)
    if failure == "scratch": plan["policy"]["scratch_bytes"] = 1
    calls = controlled_native(monkeypatch)
    bundle = driver.run_native_blast_utility(plan)
    assert calls == [] and not bundle["started"] and bundle["returncode"] is None
    assert bundle["writer_closed"] and bundle["inventory_complete"]
    assert all(row["sha256"] is None for row in bundle["artifacts"])
    assert "missing_output" in {row["code"] for row in bundle["failures"]}
    if failure == "input_digest":
        row = bundle["inputs"][0]
        assert row["staged_sha256"] == row["final_sha256"] != row["expected_sha256"]
        assert (Path(plan["attempt_directory"]) / row["relative_path"]).read_bytes() == b">ALPHA\nACGTACGT\n"


def test_failed_native_build_retains_complete_captured_bytes_and_inventory(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    calls = controlled_native(monkeypatch, returncode=7, family={"nhr": b"partial header"})
    bundle = driver.run_native_blast_utility(plan)
    assert len(calls) == 1 and bundle["returncode"] == 7
    assert bundle["output_completeness_basis"] == "captured_bytes"
    assert bundle["inventory_complete"] and all(row["completeness"] == "complete" for row in bundle["artifacts"])
    assert [r["code"] for r in bundle["failures"]] == ["nonzero_returncode"]


@pytest.mark.parametrize("kind", ["symlink", "directory", "missing_stream", "bare_prefix"])
def test_output_failures_preserve_other_files(tmp_path, monkeypatch, kind):
    plan = plan_fixture(tmp_path)
    def change(argv, kwargs):
        prefix = Path(argv[argv.index("-out") + 1])
        if kind == "symlink": Path(str(prefix) + ".escape").symlink_to(tmp_path / "selected" / "supplied.fa")
        if kind == "directory": Path(str(prefix) + ".not-regular").mkdir()
        if kind == "missing_stream": Path(kwargs["stderr"].name).unlink()
        if kind == "bare_prefix": prefix.write_bytes(b"collision")
    controlled_native(monkeypatch, after=change)
    bundle = driver.run_native_blast_utility(plan)
    assert any(row["sha256"] is not None and row["role"] == "database_file" for row in bundle["artifacts"])
    codes = {r["code"] for r in bundle["failures"]}
    assert ("missing_output" if kind == "missing_stream" else "invalid_output") in codes
    assert bundle["inventory_complete"] == (kind == "missing_stream")


def test_changed_readonly_input_is_retained_as_a_qualified_failure(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    def change(argv, kwargs):
        path = Path(argv[argv.index("-in") + 1])
        path.chmod(0o644)
        path.write_bytes(b">CHANGED\nT\n")
    controlled_native(monkeypatch, after=change)
    bundle = driver.run_native_blast_utility(plan)
    assert bundle["returncode"] == 0
    assert "immutable_input_changed" in {r["code"] for r in bundle["failures"]}
    assert bundle["inputs"][0]["final_sha256"] != bundle["inputs"][0]["staged_sha256"]


@pytest.mark.parametrize("kind", ["missing_sidecar", "unlisted_family", "manifest_content", "changed_after"])
def test_prepared_dependency_conflicts_do_not_choose_a_repair(tmp_path, monkeypatch, kind):
    job = job_fixture(tmp_path, "info")
    db = job["databases"][0]
    if kind == "missing_sidecar": Path(db["manifest"]["access"]["offline_configuration"]["path"]).unlink()
    if kind == "unlisted_family": Path(db["native_paths"][0] + ".unlisted").write_bytes(b"not selected")
    if kind == "manifest_content":
        db["manifest_file"] = identity(Path(db["manifest_file"]["path"]), b'{"different":"manifest"}')
    def change(argv, kwargs):
        if kind == "changed_after": Path(db["manifest"]["files"][0]["path"]).write_bytes(b"changed by fixture")
    calls = controlled_native(monkeypatch, after=change)
    bundle = driver.run_native_blast_utility(plan_fixture(tmp_path, job))
    assert len(calls) == (1 if kind == "changed_after" else 0)
    assert {r["code"] for r in bundle["failures"]} & {"database_unavailable", "database_identity_mismatch", "database_changed"}
    assert all("database_key" in row for row in bundle["database_files"])


def test_sealed_replay_never_reexecutes_and_detects_added_family(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    calls = controlled_native(monkeypatch)
    bundle = driver.run_native_blast_utility(plan)
    assert driver.run_native_blast_utility(plan) == bundle and len(calls) == 1
    (Path(plan["attempt_directory"]) / "db/tiny.extra").write_bytes(b"later")
    with pytest.raises(ValueError, match="sealed_output_inventory_changed"):
        driver.run_native_blast_utility(plan)
    assert len(calls) == 1


def test_unsealed_attempt_never_restarts(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    root = Path(plan["attempt_directory"])
    root.mkdir()
    _atomic_new(root / OWNER_NAME, plan)
    calls = controlled_native(monkeypatch)
    with pytest.raises(ValueError, match="unsealed_attempt_execution_uncertain"):
        driver.run_native_blast_utility(plan)
    assert calls == []


def test_local_reservation_is_exact_idempotent_and_does_not_dispatch(tmp_path, monkeypatch):
    state, handle, plan, target = reserved_fixture(tmp_path, monkeypatch)
    assert handle.read()["stage"] == "prepared"
    assert local.prepare_local_blast_utility(state, plan["identity"]["operation_key"], root=handle.path.parent,
        policy=LocalJobPolicy(**POLICY)).path == handle.path
    assert local.local_blast_utility_plan(state.assignment, str(handle.path)) == plan
    handle.path.unlink()
    with pytest.raises(ValueError, match="missing_reservation_execution_uncertain"):
        local.prepare_local_blast_utility(state, plan["identity"]["operation_key"], root=handle.path.parent, policy=LocalJobPolicy(**POLICY))


@pytest.mark.parametrize("change", [
    lambda h: h["metadata"]["policy"].update(memory_bytes=1024),
    lambda h: h["command"].append("unselected"),
    lambda h: h["paths"].update(result="/outside/result"),
    lambda h: h.update(request_sha256="a" * 64),
])
def test_local_original_reservation_rejects_tampering(tmp_path, monkeypatch, change):
    state, handle, plan, target = reserved_fixture(tmp_path, monkeypatch)
    body = handle.read()
    change(body)
    handle.path.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        local.local_blast_utility_plan(state.assignment, str(handle.path))


def test_capture_retains_original_bytes_and_replays_without_native_files(tmp_path, monkeypatch):
    _, handle, plan, target, bundle = sealed_fixture(tmp_path, monkeypatch)
    store = Store(tmp_path / "store")
    directory = tmp_path / "capture"
    captured = acquisition.capture_local_utility_bundle(store, target=target, directory=directory)
    assert captured["original_bundle"] == bundle and captured["bundle_validated"]
    assert captured["source_ref"] and captured["failures"] == []
    assert len(captured["artifacts"]) == 1 + 2 + len(FAMILY)
    assert store.get(captured["source_ref"])["auxiliary_artifact_refs"] == sorted({row["artifact_ref"] for row in captured["artifacts"]})
    for row in captured["artifacts"]:
        data = store.get_artifact(row["artifact_ref"])
        assert len(data) == row["size_bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"]
    shutil.rmtree(handle.path.parent)
    shutil.rmtree(tmp_path / "selected")
    monkeypatch.setattr(acquisition, "local_blast_utility_plan", lambda *a, **k: pytest.fail("replay read native paths"))
    monkeypatch.setattr(acquisition, "_capture_file", lambda *a, **k: pytest.fail("replay recaptured files"))
    assert acquisition.capture_local_utility_bundle(store, target=target, directory=directory) == captured


@pytest.mark.parametrize("kind", ["missing_output", "changed_output", "changed_input"])
def test_capture_preserves_valid_partial_files_after_original_file_loss(tmp_path, monkeypatch, kind):
    _, _, plan, target, bundle = sealed_fixture(tmp_path, monkeypatch)
    root = Path(plan["attempt_directory"])
    selected = root / (bundle["inputs"][0]["relative_path"] if kind == "changed_input" else bundle["artifacts"][0]["relative_path"])
    if kind == "missing_output": selected.unlink()
    else:
        selected.chmod(0o644)
        selected.write_bytes(b"later different bytes")
    store = Store(tmp_path / "store")
    captured = acquisition.capture_local_utility_bundle(store, target=target, directory=tmp_path / "capture")
    assert captured["bundle_validated"] and captured["source_ref"]
    assert len(captured["artifacts"]) == len(bundle["artifacts"])
    failure, = captured["failures"]
    assert failure["code"] == ("original_file_unavailable" if kind == "missing_output" else "original_file_identity_mismatch")
    if kind != "missing_output": assert store.get_artifact(failure["diagnostic_artifact_ref"]) == b"later different bytes"


def test_capture_of_nonoriginal_input_retains_diagnostic_without_measurement(tmp_path, monkeypatch):
    job = job_fixture(tmp_path)
    job["inputs"][0]["sha256"] = "b" * 64
    _, _, plan, target = reserved_fixture(tmp_path, monkeypatch, job=job)
    calls = controlled_native(monkeypatch)
    driver.run_native_blast_utility(plan)
    assert calls == []
    store = Store(tmp_path / "store")
    captured = acquisition.capture_local_utility_bundle(store, target=target, directory=tmp_path / "capture")
    assert captured["bundle_validated"] and not captured["artifacts"]
    failure, = captured["failures"]
    assert failure["code"] == "input_not_original"
    assert store.get_artifact(failure["diagnostic_artifact_ref"]) == b">ALPHA\nACGTACGT\n"


@pytest.mark.parametrize("kind", ["missing_bundle", "invalid_bundle", "unsealed_bundle", "invalid_owner"])
def test_unvalidated_bundle_never_publishes_measurements(tmp_path, monkeypatch, kind):
    _, _, plan, target, bundle = sealed_fixture(tmp_path, monkeypatch)
    path = Path(plan["attempt_directory"]) / BUNDLE_NAME
    if kind == "missing_bundle": path.unlink()
    elif kind == "invalid_bundle": path.write_bytes(b'{"invalid":true}')
    elif kind == "unsealed_bundle": path.write_text(json.dumps(bundle))
    else: (path.parent / OWNER_NAME).write_bytes(b'{"wrong":"owner"}')
    store = Store(tmp_path / "store")
    captured = acquisition.capture_local_utility_bundle(store, target=target, directory=tmp_path / "capture")
    assert not captured["bundle_validated"] and captured["original_bundle"] is None and captured["source_ref"] is None
    assert captured["artifacts"] == []
    assert any(f["direction"] is None for f in captured["failures"])
    assert any(f["code"] == "unsealed_file" and f["diagnostic_artifact_ref"] for f in captured["failures"])
    if kind == "invalid_owner": assert any(f["code"] == "original_owner_invalid" for f in captured["failures"])


@pytest.mark.parametrize("change", [
    lambda t: t.update(run_id="other"),
    lambda t: t.update(origin_episode_id="other"),
    lambda t: t.update(attempt_id="a" * 64),
    lambda t: t.update(original_operation_key="other"),
    lambda t: t.update(native_outcome={"kind": "native_blast_utility"}),
    lambda t: t.update(driver_plan="/arbitrary"),
    lambda t: t["assignment"]["constraints"]["allocation"].update(wall_seconds=1),
])
def test_capture_rejects_cross_attempt_targets_and_unrecognized_extensions(tmp_path, monkeypatch, change):
    _, _, _, target, _ = sealed_fixture(tmp_path, monkeypatch)
    change(target)
    with pytest.raises(ValueError):
        acquisition.capture_local_utility_bundle(Store(tmp_path / "store"), target=target, directory=tmp_path / "capture")


def test_saved_capture_cannot_relabel_an_original_output(tmp_path, monkeypatch):
    _, _, _, target, _ = sealed_fixture(tmp_path, monkeypatch)
    store = Store(tmp_path / "store")
    directory = tmp_path / "capture"
    capture = acquisition.capture_local_utility_bundle(store, target=target, directory=directory)
    capture["artifacts"][-1]["original_path"] = "/unselected/output"
    (directory / "capture.json").write_text(canonical(capture) + "\n")
    with pytest.raises(ValueError, match="capture_artifact_association_conflict"):
        acquisition.capture_local_utility_bundle(store, target=target, directory=directory)


def test_saved_capture_verifies_retained_digest_before_return(tmp_path, monkeypatch):
    _, _, _, target, _ = sealed_fixture(tmp_path, monkeypatch)
    store = Store(tmp_path / "store")
    directory = tmp_path / "capture"
    capture = acquisition.capture_local_utility_bundle(store, target=target, directory=directory)
    sha = capture["artifacts"][-1]["sha256"]
    (store.path / "artifacts" / sha[:2] / sha).write_bytes(b"corrupt retained bytes")
    with pytest.raises(ValueError):
        acquisition.capture_local_utility_bundle(store, target=target, directory=directory)
