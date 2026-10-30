"""406 receipt mechanism tests with explicit injected scientific qualification.

Store, Journal, parent commissions, practical receipt publication and result
controls are real. The compact native/worker qualification in these fixtures is
injected; live scientific and complete receiving-episode verification is separate.
"""
import asyncio
from copy import deepcopy
import fcntl
from importlib import import_module
import json
import os
from pathlib import Path
import shutil
import threading
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.protein_structure_result_receipts import (
    ProteinResultAction, ProteinResultReceipts,
)
from gene_annotation_episode.state import Store

F = import_module("verification.tool_graders_protein_structure_result_receipts_2026-10-27_406.fixture_helpers")


@pytest.fixture
def f(tmp_path):
    with Store(tmp_path / "store") as store:
        fixture = F.ReceiptFixture(store, tmp_path / "fixture")
        fixture.injected_handoff()
        yield fixture


def run(value):
    return asyncio.run(value)


def completed(f, **kwargs):
    context, receipt = run(f.publish(**kwargs))
    return context, receipt, receipt["body"]["intent"]["operation_key"]


def read(f, context, key):
    return f.receipts.read_completed(episode_id=context.episode_id, operation_key=key, scope=f.scope)


def write(path, value):
    path.chmod(0o600)
    path.write_bytes(canonical(value).encode())
    path.chmod(0o444)


def forbid(*_args, **_kwargs):
    raise AssertionError("Historical authority opened scientific bytes, executed work or mutated Store")


def test_constructor_inert_paths_pure_and_dependency_late(tmp_path):
    class Inert:
        directory, run_id = tmp_path, "inert"
        def __getattr__(self, name):
            raise AssertionError(name)
    receipts = ProteinResultReceipts(Inert())
    assert receipts.action_directory(episode_id="episode", operation_key="key") == (
        tmp_path / "execution-results" / digest(["inert", "episode"]) /
        "native-protein-structure-actions" / digest("key"))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("legacy_without_newline", [False, True])
def test_shared_result_directory_manifest_envelope(f, legacy_without_newline):
    context = f.child()
    directory = ExecutionEpisodes._result_directory(f.owner, context)
    path = directory / "assignment.json"
    raw = path.read_bytes()
    assert raw == canonical(json.loads(raw)).encode() + b"\n"
    if legacy_without_newline:
        raw = raw[:-1]
        path.write_bytes(raw)
    context, receipt, key = completed(f, context=context)
    assert path.read_bytes() == raw
    assert read(f, context, key) == receipt
    if not legacy_without_newline:
        assert ExecutionEpisodes._result_directory(f.owner, context) == directory
        assert path.read_bytes() == raw


def test_receipt_created_assignment_matches_shared_writer(f):
    context, receipt, key = completed(f)
    directory = ExecutionEpisodes._result_directory(f.owner, context)
    raw = (directory / "assignment.json").read_bytes()
    assert raw == canonical(json.loads(raw)).encode() + b"\n"
    assert read(f, context, key) == receipt


@pytest.mark.parametrize("suffix", [b"\n\n", b"\r\n"])
def test_shared_assignment_rejects_other_byte_envelopes(f, suffix):
    context = f.child()
    directory = ExecutionEpisodes._result_directory(f.owner, context)
    path = directory / "assignment.json"
    path.write_bytes(path.read_bytes()[:-1] + suffix)
    key = f.select(context)
    async def select():
        async with f.receipts.locked_action(context, target=f.target,
                tool_name="execution.results.collect", arguments={}, operation_key=key):
            raise AssertionError("Malformed shared manifest was accepted")
    with pytest.raises(ValueError, match="invalid_schema"):
        run(select())


@pytest.mark.parametrize("name", ["intent.json", "publication.json"])
def test_receipt_owned_controls_still_reject_newline(f, name):
    context, _, key = completed(f)
    path = f.receipts.action_directory(episode_id=context.episode_id, operation_key=key) / name
    raw = path.read_bytes()
    assert raw == canonical(json.loads(raw)).encode()
    path.chmod(0o600)
    path.write_bytes(raw + b"\n")
    path.chmod(0o444)
    with pytest.raises(ValueError, match="invalid_schema"):
        read(f, context, key)


def test_private_replay_pending_is_not_completed_authority(f):
    context, receipt, key = completed(f, commit=False)
    assert receipt["publication"]["delivery_complete"] is True
    with pytest.raises(ValueError):
        read(f, context, key)
    assert f.receipts.completed_receipts(context) == []
    async def replay():
        async with f.receipts.locked_action(context, target=f.target, tool_name="execution.results.collect",
                arguments={}, operation_key=key) as action:
            return f.receipts.read_staged(action)
    assert run(replay()) == receipt
    f.commit(context, F.outcome(receipt))
    assert read(f, context, key) == receipt
    assert f.receipts.completed_receipts(context) == [receipt]
    # Runtime credit is independently still null after outcome recording.
    assert f.journal.row("runtime_actions", context.episode_id, 0)["credit"] is None


def test_authenticated_unsaved_construction_has_no_completed_receipts(f):
    context = f.child(save=False)
    assert f.receipts.completed_receipts(context) == []
    assert not (f.owner.directory / "execution-results").exists()


def test_metadata_history_survives_every_artifact_and_producer_loss(f, monkeypatch):
    context, receipt, key = completed(f)
    for path in (f.store.path / "artifacts").rglob("*"):
        if path.is_file():
            path.unlink()
    shutil.rmtree(f.workspace)
    action_dir = f.receipts.action_directory(episode_id=context.episode_id, operation_key=key)
    for name in ("worker", "capture"):
        shutil.rmtree(action_dir / name, ignore_errors=True)
    monkeypatch.setattr(f.store, "get_artifact", forbid)
    monkeypatch.setattr(f.store, "_validate_record", forbid)
    monkeypatch.setattr(f.store, "put", forbid)
    monkeypatch.setattr("gene_annotation_episode.native_protein_structure_acquisition.capture_local_protein_structure_bundle", forbid)
    monkeypatch.setattr("gene_annotation_episode.native_protein_structure_preparation.prepare_protein_structure_worker", forbid)
    monkeypatch.setattr("gene_annotation_episode.native_protein_structure_preparation.validate_prepared_protein_structure_worker", forbid)
    monkeypatch.setattr("gene_annotation_episode.native_protein_structure_local.local_protein_structure_plan", forbid)
    before = list(f.store.db.iterdump())
    assert read(f, context, key) == receipt
    assert f.receipts.completed_receipts(context) == [receipt]
    assert all(f.receipts.owns_reference(ref) for ref in receipt["publication"]["family_artifact_refs"])
    assert list(f.store.db.iterdump()) == before
    fresh = ProteinResultReceipts(f.owner)
    assert fresh.read_completed(episode_id=context.episode_id, operation_key=key, scope=f.scope) == receipt


@pytest.mark.parametrize("name", ["body.json", "publication.json", "receipt.json", "handoff-proof.json", "intent.json"])
def test_missing_required_control_is_not_reconstructed(f, name):
    context, receipt, key = completed(f)
    directory = f.receipts.action_directory(episode_id=context.episode_id, operation_key=key)
    (directory / name).unlink()
    with pytest.raises(ValueError):
        read(f, context, key)


def test_missing_private_receipt_after_runtime_commit_never_reexecutes(f):
    context, receipt, key = completed(f)
    directory = f.receipts.action_directory(episode_id=context.episode_id, operation_key=key)
    (directory / "receipt.json").unlink()
    async def selected():
        async with f.receipts.locked_action(context, target=f.target, tool_name="execution.results.collect",
                arguments={}, operation_key=key):
            pytest.fail("committed action was allowed to execute again")
    with pytest.raises(ValueError): run(selected())


@pytest.mark.parametrize("case", ["pending", "status", "different_tool", "extra_action", "partial", "extra_envelope", "changed_refs", "missing_row", "bad_pending_wrapper"])
def test_exact_completed_collect_runtime_outcome_required(f, case):
    context, receipt, key = completed(f)
    row = f.journal.row("runtime_actions", context.episode_id, 0)
    action, result = json.loads(row["action"]), json.loads(row["result"])
    if case == "pending": result = None
    elif case == "status": action["tool"] = "execution.results.status"
    elif case == "different_tool": action["tool"] = "execution.results.read"
    elif case == "extra_action": action["extra"] = True
    elif case == "partial": result["status"] = "partial"
    elif case == "extra_envelope": result["ignored"] = 1
    elif case == "changed_refs": result["changed_record_refs"] = []
    elif case == "bad_pending_wrapper": result["pending_work_after_action"] = {"invented": True}
    if case == "missing_row":
        f.store.db.execute("DELETE FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
            (f.run_id, context.episode_id))
    else:
        f.store.db.execute("UPDATE runtime_actions SET action=?,result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(action), None if result is None else canonical(result), f.run_id, context.episode_id))
    with pytest.raises(ValueError):
        read(f, context, key)


@pytest.mark.parametrize("case", ["parent_purpose", "parent_goal", "parent_schema", "parent_assignment", "parent_scope", "child_request", "child_path", "manifest"])
def test_full_original_commission_and_frozen_context_checked(f, case):
    context, receipt, key = completed(f)
    if case.startswith("parent_"):
        row = f.journal.row("runtime_actions", f.root.episode_id, 1)
        action = json.loads(row["action"])
        field = case.removeprefix("parent_")
        if field == "schema": action["schema_json"] = canonical({"type": "string"})
        else: action[field] = "changed" if field in ("purpose", "goal") else {"changed": True}
        f.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=1",
            (canonical(action), f.run_id, f.root.episode_id))
    elif case == "child_request":
        request = plain(context.request)
        request["extra_request_information"] = "changed full request"
        f.store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?",
            (canonical(request), f.run_id, context.episode_id))
    elif case == "child_path":
        f.store.db.execute("UPDATE runtime_episodes SET path=? WHERE run_id=? AND episode_id=?",
            (canonical([["results", "wrong"]]), f.run_id, context.episode_id))
    else:
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET parent_episode_id=? WHERE run_id=? AND episode_id=?",
            (context.episode_id, f.run_id, context.episode_id))
    with pytest.raises(ValueError):
        read(f, context, key)


@pytest.mark.parametrize("case", ["target", "plan", "capture_index", "worker_plan", "worker_policy", "source", "body_hash", "completion", "capture_count", "observation_count"])
def test_closed_metadata_relationships_reject_even_consistent_envelope_rewrite(f, case):
    context, receipt, key = completed(f)
    altered = deepcopy(receipt)
    body, publication = altered["body"], altered["publication"]
    if case == "target": body["intent"]["target"]["resource_id"] = "other"
    elif case == "plan": body["capture"]["original_plan"]["identity"]["attempt_id"] = "1" * 64
    elif case == "capture_index": body["capture"]["files"][0]["manifest_index_0based"] = 1
    elif case == "worker_plan": body["worker"]["plan"]["directory"] += "-foreign"
    elif case == "worker_policy": body["worker"]["execution"]["metadata"]["policy"]["memory_bytes"] = 1
    elif case == "source": publication["source_record"]["retrieved_at"] = "different"
    elif case == "body_hash": publication["body_sha256"] = "2" * 64
    elif case == "completion": publication["delivery_complete"] = False
    elif case == "capture_count": body["capture"]["files"][0]["manifest_index_0based"] = False
    else:
        body["observation"] = {"observed_at": "2026-10-27T00:00:00+00:00", "state": "completed",
            "returncode": True, "failure_code": None, "result_available": False, "measurements": [],
            "outputs": [], "logs": [], "provenance_refs": [], "native": {}}
        body["observation_origin"] = "selected_native_observation"
    if case != "body_hash": publication["body_sha256"] = digest(body)
    directory = f.receipts.action_directory(episode_id=context.episode_id, operation_key=key)
    for name, value in (("intent.json", body["intent"]), ("body.json", body),
                        ("publication.json", publication), ("receipt.json", altered)):
        write(directory / name, value)
    f.commit(context, F.outcome(altered))
    with pytest.raises(ValueError):
        read(f, context, key)


@pytest.mark.parametrize("copy", ["publication.json", "receipt.json", "runtime"])
@pytest.mark.parametrize("change", ["extra", "reorder", "changed"])
def test_lifecycle_membership_is_bound_to_each_persisted_copy(f, copy, change):
    context, receipt, key = completed(f)
    altered = deepcopy(receipt)
    refs = altered["publication"]["family_artifact_refs"]
    if change == "extra": refs.append(f.store.artifact(b"not this published lifecycle"))
    elif change == "changed": refs[-1] = f.store.artifact(b"changed lifecycle control")
    else: refs[-2:] = reversed(refs[-2:])
    if copy == "runtime": f.commit(context, F.outcome(altered))
    else:
        directory = f.receipts.action_directory(episode_id=context.episode_id, operation_key=key)
        write(directory / copy, altered["publication"] if copy == "publication.json" else altered)
    with pytest.raises(ValueError): read(f, context, key)


def test_two_same_source_collections_resolve_the_exact_operation(f):
    first, receipt1, key1 = completed(f)
    second, receipt2, key2 = completed(f, context=f.child(index=2))
    assert receipt1["publication"]["source_record"] == receipt2["publication"]["source_record"]
    assert receipt1["publication"]["custody"] != receipt2["publication"]["custody"]
    assert read(f, second, key2) == receipt2
    assert read(f, first, key1) == receipt1


def test_action_instance_must_be_live_owned_and_unchanged(f):
    context = f.child()
    key = f.select(context)
    async def exercise():
        async with f.receipts.locked_action(context, target=f.target, tool_name="execution.results.collect",
                arguments={}, operation_key=key) as action:
            f.receipts.require_action(action)
            for alien in (ProteinResultAction(), ProteinResultReceipts(f.owner)):
                with pytest.raises(ValueError): f.receipts.require_action(alien)
            with pytest.raises(ValueError): ProteinResultReceipts(f.owner).require_action(action)
            action.intent["original_request_sha256"] = "0" * 64
            with pytest.raises(ValueError): f.receipts.read_staged(action)
            action.intent["original_request_sha256"] = digest(plain(context.request))
        for port in (f.receipts.require_action, f.receipts.read_staged, f.receipts.read_observation):
            with pytest.raises(ValueError): port(action)
    run(exercise())


def test_replaced_lock_file_cannot_reuse_live_action(f):
    context = f.child()
    key = f.select(context)
    async def replace():
        async with f.receipts.locked_action(context, target=f.target, tool_name="execution.results.collect",
                arguments={}, operation_key=key) as action:
            lock = action.directory / ".action.lock"
            lock.rename(action.directory / "previous.lock")
            lock.write_bytes(b"")
            with pytest.raises(ValueError, match="invalid_output_path"):
                f.receipts.read_staged(action)
    run(replace())


@pytest.mark.parametrize("name", [".action.lock", "intent.json", "capture", "worker", "assignment.json", "action_directory"])
def test_symlink_controls_and_directories_reject_before_dispatch(f, name):
    context = f.child()
    key = f.select(context)
    directory = f.receipts.action_directory(episode_id=context.episode_id, operation_key=key)
    directory.mkdir(parents=True)
    outside = f.directory / "outside"
    outside.mkdir()
    if name == "action_directory":
        directory.rmdir()
        directory.symlink_to(outside, target_is_directory=True)
    else:
        path = directory.parent.parent / name if name == "assignment.json" else directory / name
        if name in ("capture", "worker"): path.symlink_to(outside, target_is_directory=True)
        else:
            (outside / "file").write_text("{}")
            path.symlink_to(outside / "file")
    async def select():
        async with f.receipts.locked_action(context, target=f.target, tool_name="execution.results.collect",
                arguments={}, operation_key=key):
            pytest.fail("unsafe action reached host")
    with pytest.raises(ValueError): run(select())


def test_two_async_same_action_callers_share_immutable_publication(f):
    context = f.child()
    key = f.select(context)
    async def race():
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []
        async def selected(first):
            async with f.receipts.locked_action(context, target=f.target, tool_name="execution.results.collect",
                    arguments={}, operation_key=key) as action:
                staged = f.receipts.read_staged(action)
                if staged is not None: return staged
                calls.append("qualification")
                entered.set()
                if first: await release.wait()
                proof = f.receipts.read_handoff_proof(action, context=context, target=f.target)
                body, publication = f.injected_publication(action, proof)
                return f.receipts.publish(action, body=body, publication=publication)
        first = asyncio.create_task(selected(True))
        await entered.wait()
        second = asyncio.create_task(selected(False))
        # Responsive loop makes this explicit test event runnable while flock waits.
        await asyncio.sleep(.02)
        assert not second.done()
        release.set()
        a, b = await asyncio.gather(first, second)
        assert a == b and calls == ["qualification"]
        return a
    receipt = run(race())
    assert f.receipts.completed_receipts(context) == []
    f.commit(context, F.outcome(receipt))
    assert read(f, context, key) == receipt


def test_cancelled_lock_wait_drains_thread_before_fd_close(f, monkeypatch):
    context = f.child()
    key = f.select(context)
    directory = f.receipts.action_directory(episode_id=context.episode_id, operation_key=key)
    directory.mkdir(parents=True)
    holder = os.open(directory / ".action.lock", os.O_CREAT | os.O_RDWR, 0o600)
    actual = fcntl.flock
    actual(holder, fcntl.LOCK_EX)
    started, acquired = threading.Event(), []
    def observed(fd, operation):
        if operation == fcntl.LOCK_EX:
            started.set()
            actual(fd, operation)
            acquired.append(os.fstat(fd).st_ino)  # must still be a live descriptor
        else: actual(fd, operation)
    monkeypatch.setattr("gene_annotation_episode.protein_structure_result_receipts.fcntl.flock", observed)
    async def cancel_wait():
        async def selected():
            async with f.receipts.locked_action(context, target=f.target, tool_name="execution.results.collect",
                    arguments={}, operation_key=key):
                pytest.fail("cancelled lock waiter entered host")
        task = asyncio.create_task(selected())
        await asyncio.to_thread(started.wait)
        task.cancel()
        await asyncio.sleep(.01)
        task.cancel()
        await asyncio.sleep(.01)
        assert not task.done()
        actual(holder, fcntl.LOCK_UN)
        with pytest.raises(asyncio.CancelledError): await asyncio.wait_for(task, 5)
    try:
        run(cancel_wait())
        assert len(acquired) == 1
        actual(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (directory / "intent.json").exists()
    finally:
        actual(holder, fcntl.LOCK_UN)
        os.close(holder)


def test_no_transaction_across_async_lock_acquisition(f):
    context = f.child()
    key = f.select(context)
    async def select():
        async with f.receipts.locked_action(context, target=f.target, tool_name="execution.results.collect",
                arguments={}, operation_key=key): pytest.fail("transaction crossed await")
    f.store.db.execute("BEGIN")
    try:
        with pytest.raises(ValueError): run(select())
    finally:
        f.store.db.rollback()


def test_foreign_runtime_metadata_classifies_without_authority_or_new_table(f, monkeypatch):
    context, receipt, key = completed(f)
    refs = receipt["publication"]["family_artifact_refs"]
    before = list(f.store.db.execute("SELECT name FROM sqlite_master WHERE type='table'"))
    foreign = ProteinResultReceipts(SimpleNamespace(store=f.store, directory=f.owner.directory, run_id="foreign-run"))
    monkeypatch.setattr(f.store, "get_artifact", forbid)
    assert all(foreign.owns_reference(ref) for ref in refs)
    assert foreign.owns_reference(receipt["publication"]["source_record"]["id"])
    assert not foreign.owns_reference(f.store.artifact(b"ordinary unrelated explicit bytes"))
    assert list(f.store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")) == before


def test_pending_private_worker_refs_are_not_published_membership(f):
    context, receipt, key = completed(f, commit=False)
    ref = receipt["body"]["worker"]["prepared"]["plan_artifact_ref"]
    assert not f.receipts.owns_reference(ref)
    f.commit(context, F.outcome(receipt))
    assert f.receipts.owns_reference(ref)


def test_ordinary_source_artifacts_classify_without_runtime_table(f, monkeypatch):
    _, receipt, _ = completed(f)
    source = receipt["publication"]["source_record"]
    refs = [source["artifact_ref"], *source["auxiliary_artifact_refs"]]
    unrelated = f.store.artifact(b"unrelated artifact without a runtime table")
    f.store.db.execute("DROP TABLE runtime_actions")
    f.store.db.commit()
    before = list(f.store.db.execute("SELECT name FROM sqlite_master WHERE type='table'"))
    foreign = ProteinResultReceipts(SimpleNamespace(store=f.store, directory=f.owner.directory, run_id="foreign-run"))
    monkeypatch.setattr(f.store, "get_artifact", forbid)
    assert all(foreign.owns_reference(ref) for ref in refs)
    assert not foreign.owns_reference(unrelated)
    assert list(f.store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")) == before


def test_observation_is_immutable_detached_and_strict(f):
    context = f.child()
    key = f.select(context, "execution.results.status")
    observation = {"observed_at": "2026-10-27T00:00:00+00:00", "state": "completed", "returncode": 0,
        "failure_code": None, "result_available": False, "measurements": [], "outputs": [], "logs": [],
        "provenance_refs": [], "native": {}}
    async def select():
        async with f.receipts.locked_action(context, target=f.target, tool_name="execution.results.status",
                arguments={}, operation_key=key) as action:
            assert f.receipts.read_observation(action) is None
            returned = f.receipts.record_observation(action, observation=observation)
            returned["native"]["changed"] = True
            assert f.receipts.read_observation(action) == observation
            with pytest.raises(ValueError): f.receipts.record_observation(action, observation=returned)
            bad = deepcopy(observation)
            bad["returncode"] = False
            with pytest.raises(ValueError): f.receipts.record_observation(action, observation=bad)
    run(select())
    with pytest.raises(ValueError): read(f, context, key)
    assert f.receipts.completed_receipts(context) == []
