"""Real subprocess durability checks with ordinary synthetic Episodes.

These test selected execution and typed infrastructure records. They do not
exercise configured models, application admission or scientific conclusions.
All deadlines below bound tests, never production episode work.
"""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys

import pytest

from method_loop import EpisodeGoal
from method_loop.communication import ReportContract
from method_loop.durable import (DurableExecutionError, DurableExecutionStore,
                                 canonical, content_digest)
from method_loop.identities import EpisodeRef


def commission_spec(tmp_path, *, key="child", arguments=None, parent=None):
    run_id = "durable-fixture-run"
    if parent is None:
        parent_goal = EpisodeGoal.root(objective="Resolve the synthetic question", result_contract={})
        parent_path = [["science", "root"]]
    else:
        parent_goal = EpisodeGoal.from_record(parent["child"]["request"]["goal"])
        parent_path = parent["child"]["path"]
    goal = EpisodeGoal.child(parent_goal, objective="Iteratively resolve " + key, result_contract={})
    contract = ReportContract("Return one measured fixture value", {"value": {"type": "integer"}},
                              {"value": "The final measured fixture value"})
    child_path = parent_path + [["science", key]]
    root = tmp_path / key
    root.mkdir()
    args = {"fixture_directory": str(root), "execution_directory": str(tmp_path / "executions"),
            **(arguments or {})}
    return {"version": "episode_commission_v1", "handle": "work:" + key,
        "operation_key": "commission:" + key, "run_id": run_id,
        "parent": {"episode_id": EpisodeRef(run_id, parent_path).episode_id,
                   "goal_id": parent_goal.goal_id, "path": parent_path},
        "child": {"episode_id": EpisodeRef(run_id, child_path).episode_id,
                  "role": "science", "key": key, "path": child_path,
                  "request": {"goal": goal.as_record(), "message": {}, "report_contract": contract.as_record()},
                  "scope": {"subject_refs": ["synthetic_subject"]}},
        "input_versions": [],
        "runtime_binding": {"factory_module": "durable_fixture", "factory_name": "open_commission",
                            "arguments": args,
                            "implementation_sha256": hashlib.sha256((Path(__file__).with_name("durable_fixture.py")).read_bytes()).hexdigest(),
                            "settings_sha256": content_digest(args)},
        "constraints": {"fixture_only": True}, "resource_selection": None,
        "expectation_snapshot_refs": []}


def event_condition(handle, event="returned", after_cursor=0, reconsider_at=None):
    return {"version": "event_condition_v1", "events": [{"handle": handle, "event": event,
            "after_cursor": after_cursor}], "reconsider_at": reconsider_at}


def await_event(store, handle, event="returned", after_cursor=0):
    return asyncio.run(asyncio.wait_for(store.wait_events(event_condition(handle, event, after_cursor)), 10))


def release_gate(path):
    with path.open("wb", buffering=0) as stream:
        stream.write(b"1")


def returned(store, spec):
    await_event(store, spec["handle"])
    page = store.return_page(spec["parent"]["episode_id"], 0, 10)
    item = next(item for item in page["items"] if item["handle"] == spec["handle"])
    return store.load_return(item["handle"], item["return_id"])


def starter(command, *arguments):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(Path(__file__).parent), str(Path(__file__).parent.parent)])
    return subprocess.Popen([sys.executable, "-c", command, *map(str, arguments)],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def test_commission_is_immutable_and_parent_scoped_operation_identity_conflicts(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    receipt = store.commission(spec)
    assert receipt == store.commission(deepcopy(spec))
    assert receipt["commission_sha256"] == content_digest(spec)
    changed = deepcopy(spec)
    changed["constraints"]["changed"] = True
    with pytest.raises(DurableExecutionError) as error:
        store.commission(changed)
    assert error.value.failure["code"] == "identity_conflict"
    changed = deepcopy(spec)
    changed["handle"] = "work:different"
    with pytest.raises(DurableExecutionError):
        store.commission(changed)
    assert store.load_commission(spec["handle"]) == spec
    assert store.status(spec["handle"])["lifecycle_state"] == "pending"
    assert not (tmp_path / "child" / "invocations").exists()
    invalid = deepcopy(spec)
    invalid["constraints"]["invalid"] = float("nan")
    with pytest.raises(ValueError):
        store.commission(invalid)


def test_worker_runner_rejects_unclaimed_execution_before_invoking_factory(tmp_path):
    from method_loop.durable_worker import execute_commission
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    store.commission(spec)
    with store._connect() as db:
        token = store._row(db, spec["handle"])["execution_token"]
    with pytest.raises(DurableExecutionError) as error:
        asyncio.run(execute_commission(store, spec["handle"], token))
    assert error.value.failure["code"] == "identity_conflict"
    assert not (tmp_path / "child" / "invocations").exists()


def test_storage_unavailability_is_structured_and_never_dispatches_work(tmp_path, monkeypatch):
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    store.commission(spec)
    def unavailable(*_args, **_kwargs):
        raise sqlite3.OperationalError("fixture storage unavailable")
    monkeypatch.setattr(sqlite3, "connect", unavailable)
    with pytest.raises(DurableExecutionError) as error:
        store.start(spec["handle"])
    assert error.value.failure["code"] == "storage_failure"
    assert error.value.failure["affected_refs"] == [str(store.root_directory / "executions.sqlite")]
    assert not (tmp_path / "child" / "invocations").exists()


def test_normal_subprocess_runs_original_loop_and_return_survives_store_restart(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    store.commission(spec)
    status = store.start(spec["handle"])
    assert status["execution_identity"]["pid"] != os.getpid()
    envelope = returned(store, spec)
    assert envelope["outcome"] == "closed" and envelope["failure"] is None
    assert envelope["completion"] == {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 2}
    assert envelope["form"] == {"value": 6}
    assert set(envelope["episode_archive"]) == {"file", "sha256", "index_sha256"}
    archive = tmp_path / "child" / "archive" / envelope["episode_archive"]["file"]
    trace = json.loads(archive.read_text())
    assert trace["path"] == spec["child"]["path"]
    assert [row["unit_label"] for row in trace["units"]] == ["first", "second"]
    restarted = DurableExecutionStore(tmp_path / "executions")
    assert restarted.start(spec["handle"])["execution_identity"] == status["execution_identity"]
    assert restarted.load_return(spec["handle"], envelope["return_id"]) == envelope
    assert (tmp_path / "child" / "invocations").read_text().splitlines() == [str(status["execution_identity"]["pid"])]
    acknowledgment = restarted.acknowledge(spec["handle"], envelope["return_id"], "admission:one")
    assert restarted.acknowledge(spec["handle"], envelope["return_id"], "admission:one") == acknowledgment
    assert restarted.status(spec["handle"])["lifecycle_state"] == "admitted"
    with pytest.raises(DurableExecutionError):
        restarted.acknowledge(spec["handle"], envelope["return_id"], "admission:different")
    assert restarted.return_page(spec["parent"]["episode_id"], 0, 1)["items"][0]["return_id"] == envelope["return_id"]


def test_concurrent_process_starters_run_work_once_and_recover_existing_identity(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    gate = tmp_path / "gate"
    os.mkfifo(gate)
    spec = commission_spec(tmp_path, arguments={"gate": str(gate)})
    store.commission(spec)
    command = "from method_loop.durable import DurableExecutionStore; import json,sys; print(json.dumps(DurableExecutionStore(sys.argv[1]).start(sys.argv[2])))"
    processes = [starter(command, store.root_directory, spec["handle"]) for _ in range(4)]
    statuses = []
    for process in processes:
        output, error = process.communicate(timeout=10)
        assert process.returncode == 0, error
        statuses.append(json.loads(output))
    assert len({canonical(status["execution_identity"]) for status in statuses}) == 1
    await_event(store, spec["handle"], "progress_committed")
    assert store.start(spec["handle"])["execution_identity"] == statuses[0]["execution_identity"]
    assert len((tmp_path / "child" / "invocations").read_text().splitlines()) == 1
    release_gate(gate)
    assert returned(store, spec)["form"] == {"value": 6}


@pytest.mark.parametrize("death_window", ["before_spawn", "after_spawn"])
def test_parent_death_at_spawn_boundary_preserves_exactly_one_selected_attempt(tmp_path, death_window):
    store = DurableExecutionStore(tmp_path / "executions")
    gate = tmp_path / "gate"
    os.mkfifo(gate)
    spec = commission_spec(tmp_path, arguments={"gate": str(gate)})
    store.commission(spec)
    command = """
import os,sys
import method_loop.durable as durable
original = durable.subprocess.Popen
def die(*args, **kwargs):
    if sys.argv[3] == 'after_spawn':
        original(*args, **kwargs)
    os._exit(37)
durable.subprocess.Popen = die
durable.DurableExecutionStore(sys.argv[1]).start(sys.argv[2])
"""
    process = starter(command, store.root_directory, spec["handle"], death_window)
    _, error = process.communicate(timeout=10)
    assert process.returncode == 37, error
    # No owner/controller/process object from the dead parent is available.
    status = DurableExecutionStore(store.root_directory).start(spec["handle"])
    await_event(store, spec["handle"], "progress_committed")
    assert status["execution_identity"] is not None
    assert len((tmp_path / "child" / "invocations").read_text().splitlines()) == 1
    release_gate(gate)
    assert returned(store, spec)["outcome"] == "closed"


def test_killed_claimed_worker_is_interrupted_without_automatic_retry(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    gate = tmp_path / "gate"
    os.mkfifo(gate)
    spec = commission_spec(tmp_path, arguments={"gate": str(gate)})
    store.commission(spec)
    status = store.start(spec["handle"])
    await_event(store, spec["handle"], "progress_committed")
    pid = status["execution_identity"]["pid"]
    os.kill(pid, signal.SIGKILL)
    # pidfd waits for this measured incarnation, without observing timeouts or
    # inferring absence from a polling delay.
    import select
    pidfd = os.pidfd_open(pid)
    try:
        assert select.select([pidfd], [], [], 10)[0]
    finally:
        os.close(pidfd)
    restored = store.start(spec["handle"])
    assert restored["execution_identity"] == status["execution_identity"]
    assert restored["liveness"] == "not_live"
    assert restored["failure"]["code"] == "interrupted_execution"
    envelope = returned(store, spec)
    assert envelope["outcome"] == "interrupted" and envelope["completion"] is None
    assert len((tmp_path / "child" / "invocations").read_text().splitlines()) == 1
    assert (tmp_path / "child" / "committed.json").exists()


@pytest.mark.parametrize("mode", ["partial_failure", "pack_failure", "invalid_form", "unavailable_binding",
                                  "settings_mismatch", "implementation_mismatch"])
def test_failures_remain_typed_and_preserve_actual_partial_or_closed_work(tmp_path, mode):
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path, arguments={mode: True})
    if mode == "unavailable_binding":
        spec["runtime_binding"]["factory_module"] = "absent_fixture_binding"
    elif mode in ("settings_mismatch", "implementation_mismatch"):
        field = "settings_sha256" if mode == "settings_mismatch" else "implementation_sha256"
        spec["runtime_binding"][field] = "0" * 64
    store.commission(spec)
    store.start(spec["handle"])
    envelope = returned(store, spec)
    assert envelope["form"] is None
    if mode == "partial_failure":
        assert envelope["outcome"] == "execution_failed"
        assert envelope["failure"]["partial_record_refs"] == ["fixture_committed_1"]
        assert (tmp_path / "child" / "committed.json").exists()
    elif mode in ("pack_failure", "invalid_form"):
        assert envelope["outcome"] == "closed"
        assert envelope["failure"]["code"] == "invalid_return"
        assert envelope["completion"]["units_consumed"] == 2
        assert envelope["episode_archive"] and envelope["result_archive"]
        if mode == "invalid_form":
            assert envelope["facts_archive"] is not None
    else:
        assert envelope["outcome"] == "execution_failed"
        assert envelope["failure"]["code"] == "unavailable_binding"
        assert envelope["completion"] is None
    assert Path(envelope["failure"]["diagnostic_ref"]).is_file()


def test_binding_declared_interruption_keeps_its_outcome_and_partial_records(tmp_path, monkeypatch):
    from contextlib import asynccontextmanager
    import durable_fixture
    from method_loop.durable_worker import execute_commission

    store = DurableExecutionStore(tmp_path / 'executions')
    spec = commission_spec(tmp_path)
    committed = tmp_path / 'child' / 'committed.json'

    @asynccontextmanager
    async def interrupted_binding(spec):
        committed.write_text(canonical({'version': 'fixture_commit_v1', 'value': 3}))
        raise DurableExecutionError('interrupted_execution', affected_refs=[spec['handle']],
            partial_record_refs=[str(committed)])
        yield  # A factory can be interrupted before it yields an Episode.

    monkeypatch.setattr(durable_fixture, 'open_commission', interrupted_binding)
    store.commission(spec)
    with store._connect() as db:
        token = store._row(db, spec['handle'])['execution_token']
    assert store._claim(spec['handle'], token)
    receipt = asyncio.run(execute_commission(store, spec['handle'], token))
    envelope = store.load_return(spec['handle'], receipt['return_id'])
    assert envelope['outcome'] == 'interrupted'
    assert envelope['completion'] is None and envelope['form'] is None
    assert envelope['failure']['code'] == 'interrupted_execution'
    assert envelope['failure']['partial_record_refs'] == [str(committed)]
    assert json.loads(committed.read_text())['value'] == 3


def test_worker_closure_keeps_a_commissioned_descendant_executing(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    gate = tmp_path / "descendant_gate"
    os.mkfifo(gate)
    parent = commission_spec(tmp_path, key="parent")
    descendant = commission_spec(tmp_path, key="descendant", parent=parent,
                                 arguments={"gate": str(gate)})
    parent["runtime_binding"]["arguments"]["descendant_spec"] = descendant
    parent["runtime_binding"]["settings_sha256"] = content_digest(parent["runtime_binding"]["arguments"])
    store.commission(parent)
    parent_status = store.start(parent["handle"])
    envelope = returned(store, parent)
    import select
    try:
        parent_pidfd = os.pidfd_open(parent_status["execution_identity"]["pid"])
    except ProcessLookupError:
        pass  # Its measured process incarnation has already exited/reaped.
    else:
        try:
            assert select.select([parent_pidfd], [], [], 10)[0]
        finally:
            os.close(parent_pidfd)
    await_event(store, descendant["handle"], "progress_committed")
    assert envelope["pending_handles"] == [descendant["handle"]]
    assert store.status(descendant["handle"])["liveness"] == "live"
    assert store.status(descendant["handle"])["lifecycle_state"] == "executing"
    before = deepcopy(envelope)
    release_gate(gate)
    assert returned(store, descendant)["outcome"] == "closed"
    assert store.load_return(parent["handle"], envelope["return_id"]) == before


def test_event_wait_matches_selected_set_and_catches_arrival_before_subscription(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    a, b = commission_spec(tmp_path, key="a"), commission_spec(tmp_path, key="b")
    store.commission(a)
    store.commission(b)

    async def exercise():
        selected = event_condition(a["handle"], "progress_committed")
        selected["events"].append({"handle": b["handle"], "event": "progress_committed", "after_cursor": 0})
        waiter = asyncio.create_task(store.wait_events(selected))
        await asyncio.sleep(0)  # Let the production provider install its fd.
        store.record_progress(b["handle"], "progress:b:1", "b:1")
        wake = await asyncio.wait_for(waiter, 10)
        assert wake["reason"] == "progress_committed"
        assert [(event["handle"], event["record_ref"]) for event in wake["events"]] == [(b["handle"], "progress:b:1")]
        # Simulate the caller inspecting status immediately before the report
        # arrives; provider subscription must recheck the durable cursor.
        store.status(a["handle"])
        row = store.record_progress(a["handle"], "progress:a:1", "a:1")
        assert store.record_progress(a["handle"], "progress:a:1", "a:1") == row
        with pytest.raises(DurableExecutionError):
            store.record_progress(a["handle"], "progress:a:different", "a:1")
        wake_a = await asyncio.wait_for(store.wait_events(event_condition(a["handle"], "progress_committed")), 10)
        assert wake_a["reason"] == "progress_committed" and wake_a["events"] == [row]
    asyncio.run(exercise())


def test_event_arrival_after_empty_ledger_read_before_await_is_not_lost(tmp_path, monkeypatch):
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    store.commission(spec)
    original = store._matching_events
    inserted = []
    def arrive_between_read_and_wait(condition):
        result = original(condition)
        if not inserted:
            inserted.append(store.record_progress(spec["handle"], "progress:race", "race"))
        return result
    monkeypatch.setattr(store, "_matching_events", arrive_between_read_and_wait)
    wake = await_event(store, spec["handle"], "progress_committed")
    assert wake["events"] == inserted


def test_return_publication_is_authorized_immutable_and_idempotent(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    store.commission(spec)
    store.start(spec["handle"])
    envelope = returned(store, spec)
    # The test reads private authority solely to verify the publisher boundary.
    with store._connect() as db:
        token = store._row(db, spec["handle"])["execution_token"]
    receipt = store.publish_return(spec["handle"], token, envelope)
    assert store.publish_return(spec["handle"], token, envelope) == receipt
    with pytest.raises(DurableExecutionError) as error:
        store.publish_return(spec["handle"], "wrong_authority", envelope)
    assert error.value.failure["code"] == "identity_conflict"
    changed = deepcopy(envelope)
    changed["form"]["value"] = 12
    changed["return_id"] = content_digest({key: value for key, value in changed.items() if key != "return_id"})
    with pytest.raises(DurableExecutionError) as error:
        store.publish_return(spec["handle"], token, changed)
    assert error.value.failure["code"] == "identity_conflict"
    assert store.load_return(spec["handle"], envelope["return_id"]) == envelope


def test_unknown_liveness_retains_existing_identity_and_does_not_start_work(tmp_path, monkeypatch):
    import method_loop.durable as durable
    store = DurableExecutionStore(tmp_path / "executions")
    gate = tmp_path / "gate"
    os.mkfifo(gate)
    spec = commission_spec(tmp_path, arguments={"gate": str(gate)})
    store.commission(spec)
    status = store.start(spec["handle"])
    await_event(store, spec["handle"], "progress_committed")
    with monkeypatch.context() as patch:
        patch.setattr(durable, "process_identity", lambda *_: (None, "unknown"))
        patch.setattr(durable.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("unknown liveness cannot select another execution"))
        observed = store.start(spec["handle"])
        assert observed["liveness"] == "unknown"
        assert observed["execution_identity"] == status["execution_identity"]
        assert observed["lifecycle_state"] == "executing" and observed["failure"] is None
    release_gate(gate)
    assert returned(store, spec)["outcome"] == "closed"


def test_failed_bootstrap_is_recorded_without_retry_or_selected_work(tmp_path, monkeypatch):
    import method_loop.durable as durable
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    store.commission(spec)
    calls = []
    def unavailable(*_args, **_kwargs):
        calls.append("attempted process creation")
        raise OSError("fixture process creation unavailable")
    with monkeypatch.context() as patch:
        patch.setattr(durable.subprocess, "Popen", unavailable)
        status = store.start(spec["handle"])
    assert calls == ["attempted process creation"]
    assert status["lifecycle_state"] == "pending" and status["execution_identity"] is None
    assert status["failure"]["code"] == "unavailable_resource"
    assert store.status(spec["handle"])["failure"] == status["failure"]
    assert not (tmp_path / "child" / "invocations").exists()
    # A new explicit start may repair bootstrap setup before the first claim.
    store.start(spec["handle"])
    assert returned(store, spec)["outcome"] == "closed"
    assert len((tmp_path / "child" / "invocations").read_text().splitlines()) == 1


def test_status_does_not_load_archived_history_or_return_form(tmp_path, monkeypatch):
    from method_loop.archive import ArchivedRecord
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    store.commission(spec)
    store.start(spec["handle"])
    envelope = returned(store, spec)
    def forbidden(*_args, **_kwargs):
        pytest.fail("status must not materialize a closed trace")
    monkeypatch.setattr(ArchivedRecord, "load", forbidden)
    # Status uses only compact commission metadata and the separately recorded
    # failure field; it has no reason to fetch the immutable envelope/form.
    original_connect = store._connect
    from contextlib import contextmanager
    @contextmanager
    def guarded_connect(*args, **kwargs):
        with original_connect(*args, **kwargs) as db:
            def authorize(action, table, _column, *_rest):
                if action == sqlite3.SQLITE_READ and table == "returns":
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            db.set_authorizer(authorize)
            yield db
    monkeypatch.setattr(store, "_connect", guarded_connect)
    assert store.status(spec["handle"])["return_id"] == envelope["return_id"]


def test_reconsideration_and_wait_cancellation_do_not_change_execution(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    store.commission(spec)

    async def exercise():
        condition = event_condition(spec["handle"], reconsider_at=(datetime.now(timezone.utc) + timedelta(milliseconds=20)).isoformat())
        wake = await store.wait_events(condition)
        assert wake["reason"] == "reconsideration" and wake["events"] == []
        waiter = asyncio.create_task(store.wait_events(event_condition(spec["handle"])))
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert store.status(spec["handle"])["lifecycle_state"] == "pending"
    asyncio.run(exercise())


def test_selected_return_wait_observes_worker_exit_without_a_poll_or_operator_status(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    gate = tmp_path / "gate"
    os.mkfifo(gate)
    spec = commission_spec(tmp_path, arguments={"gate": str(gate)})
    store.commission(spec)
    observed = store.start(spec["handle"])
    await_event(store, spec["handle"], "progress_committed")
    async def exercise():
        waiter = asyncio.create_task(store.wait_events(event_condition(spec["handle"])))
        await asyncio.sleep(0)  # Allow filesystem/pidfd subscription.
        os.kill(observed["execution_identity"]["pid"], signal.SIGKILL)
        wake = await asyncio.wait_for(waiter, 10)
        assert wake["reason"] == "returned"
        assert wake["events"][0]["handle"] == spec["handle"]
    asyncio.run(exercise())
    envelope = returned(store, spec)
    assert envelope["outcome"] == "interrupted"
    assert envelope["failure"]["code"] == "interrupted_execution"
    assert len((tmp_path / "child" / "invocations").read_text().splitlines()) == 1


def test_quiet_selected_wait_uses_notifications_without_repeated_status_scans(tmp_path, monkeypatch):
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    store.commission(spec)
    scans = []
    original = store._matching_events
    def observe(condition):
        scans.append("ledger observation")
        return original(condition)
    monkeypatch.setattr(store, "_matching_events", observe)
    condition = event_condition(spec["handle"], reconsider_at=(datetime.now(timezone.utc) + timedelta(milliseconds=50)).isoformat())
    wake = asyncio.run(asyncio.wait_for(store.wait_events(condition), 10))
    assert wake["reason"] == "reconsideration"
    assert len(scans) <= 3  # initial observation and chosen reconsideration
