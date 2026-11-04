"""Native event transport and byte custody, without native scientific work.

Synthetic receipts establish ledger, notification and identity behavior only.
The tiny ordinary Episode fixtures exercise the unchanged mixed pidfd path.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import signal
import sqlite3

import pytest

import method_loop.durable as durable
from method_loop.durable import (DurableExecutionError, DurableExecutionStore,
    canonical, content_digest, native_target_descriptor, native_target_handle,
    read_native_target, validate_native_publication, validate_native_registration)
from test_durable_episode import (await_event, commission_spec, event_condition,
                                 returned, starter)


STAMP = "2026-10-21T16:00:00+00:00"


def registration(*, unit="fixture-native.service", **changes):
    identity = {"kind": "systemd_user_service", "unit": unit,
                "request_sha256": "a" * 64}
    return {"version": "native_event_registration_v1", "handle": native_target_handle(identity),
        "run_id": "native-event-fixture", "owner_episode_id": "episode:actual-submitter",
        "job_ref": "homology_job_fixture", "registry_ref": "execution_registry_fixture",
        "resource_id": "resource:fixture-local", "native_identity": identity, **changes}


def receipt_and_publication(target, *, status="0"):
    receipt = {"version": "native_service_exit_receipt_v1", "native_identity": target["native_identity"],
        "SERVICE_RESULT": "success", "EXIT_CODE": "exited", "EXIT_STATUS": status,
        "ended": {"at": STAMP, "monotonic_ns": 123456, "boot_id": "fixture-boot"}}
    # These are original file bytes, deliberately different from canonical JSON.
    raw = (json.dumps(receipt, indent=2) + "\n").encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    publication = {"version": "native_event_publication_v1", "event": "state_changed",
        "cause": "service_exit_receipt_committed", "record_ref": "native_event_record_" + digest[:24],
        "receipt_sha256": digest, "occurred_at": receipt["ended"]["at"]}
    return raw, publication


def publish(store, target, *, status="0"):
    raw, publication = receipt_and_publication(target, status=status)
    return store.publish_native_event(target["handle"], publication, receipt_bytes=raw)


def condition(target, *, after_cursor=0, reconsider_at=None, event="state_changed"):
    return event_condition(target["handle"], event, after_cursor, reconsider_at)


def event_count(store):
    with store._connect() as db:
        return db.execute("SELECT count(*) FROM events").fetchone()[0]


def test_pure_records_are_exact_detached_and_handle_uses_only_reserved_identity():
    target = registration()
    identity = target["native_identity"]
    assert target["handle"] == "native_event_target_" + content_digest(identity)[:24]
    copied = validate_native_registration(target)
    copied["native_identity"]["unit"] = "mutated-copy.service"
    assert target["native_identity"]["unit"] == "fixture-native.service"
    assert native_target_handle(dict(reversed(list(identity.items())))) == target["handle"]
    assert native_target_handle({**identity, "request_sha256": "b" * 64}) != target["handle"]
    descriptor = native_target_descriptor(target)
    assert descriptor == {"version": "native_event_target_v1", "handle": target["handle"],
        "job_ref": target["job_ref"], "registry_ref": target["registry_ref"],
        "resource_id": target["resource_id"], "event": "state_changed",
        "cause": "service_exit_receipt_committed"}
    assert not {"unit", "owner_episode_id", "native_identity", "run_id", "cursor"} & descriptor.keys()
    raw, publication = receipt_and_publication(target)
    assert hashlib.sha256(raw).hexdigest() != content_digest(json.loads(raw))
    copied = validate_native_publication(publication)
    copied["occurred_at"] = "2026-10-21T17:00:00Z"
    assert publication["occurred_at"] == STAMP


@pytest.mark.parametrize("change", [
    {"version": "unknown"}, {"run_id": ""}, {"owner_episode_id": None},
    {"job_ref": 12}, {"registry_ref": []}, {"resource_id": ""},
    {"handle": "native_event_target_wrong"}, {"extra": True},
    {"native_identity": {"kind": "process", "unit": "unit", "request_sha256": "a" * 64}},
    {"native_identity": {"kind": "systemd_user_service", "unit": "", "request_sha256": "a" * 64}},
    {"native_identity": {"kind": "systemd_user_service", "unit": "unit", "request_sha256": "A" * 64}},
    {"native_identity": {"kind": "systemd_user_service", "unit": "unit", "request_sha256": "a" * 64,
                         "status": "inactive"}},
    {"native_identity": {"kind": "systemd_user_service", "unit": "unit", "request_sha256": float("nan")}},
])
def test_malformed_registrations_are_value_errors(change):
    with pytest.raises(ValueError):
        validate_native_registration({**registration(), **change})


@pytest.mark.parametrize("change", [
    {"version": "unknown"}, {"event": "returned"}, {"event": "progress_committed"},
    {"cause": "service_inactive"}, {"record_ref": "native_event_record_wrong"},
    {"receipt_sha256": "A" * 64}, {"occurred_at": "2026-10-21T16:00:00"},
    {"occurred_at": "2026-10-21T16:00:00+01:00"}, {"occurred_at": {}},
    {"extra": True}, {"receipt_sha256": float("inf")},
])
def test_malformed_publications_are_value_errors(change):
    _, publication = receipt_and_publication(registration())
    with pytest.raises(ValueError):
        validate_native_publication({**publication, **change})


def test_registration_is_identity_only_immutable_and_idempotent(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    assert store.register_native_target(target) == native_target_descriptor(target)
    assert store.register_native_target(deepcopy(target)) == native_target_descriptor(target)
    assert event_count(store) == 0
    assert store.native_target(target["handle"]) == target
    loaded = store.native_target(target["handle"])
    loaded["native_identity"]["unit"] = "detached-copy.service"
    assert store.native_target(target["handle"]) == target
    for name in ("owner_episode_id", "run_id", "job_ref", "registry_ref", "resource_id"):
        with pytest.raises(DurableExecutionError) as failure:
            store.register_native_target({**target, name: "different"})
        assert failure.value.failure["code"] == "identity_conflict"
    with pytest.raises(KeyError):
        store.status(target["handle"])
    with pytest.raises(KeyError):
        store.load_commission(target["handle"])
    with pytest.raises(KeyError):
        store.native_target("missing")
    assert store.return_page(target["owner_episode_id"], 0, 10)["items"] == []
    assert event_count(store) == 0


def test_read_only_native_lookup_creates_no_backend_and_uses_no_writable_connection(tmp_path, monkeypatch):
    absent = tmp_path / "absent-backend"
    with pytest.raises(DurableExecutionError) as failure:
        read_native_target(absent, "missing")
    assert failure.value.failure["code"] == "storage_failure"
    assert not absent.exists()
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    original_connect = sqlite3.connect
    calls = []
    def read_only(*args, **kwargs):
        calls.append((args, kwargs))
        assert args[0] == (store.root_directory / "executions.sqlite").as_uri() + "?mode=ro"
        assert kwargs["uri"] is True
        return original_connect(*args, **kwargs)
    monkeypatch.setattr(sqlite3, "connect", read_only)
    monkeypatch.setattr(DurableExecutionStore, "__init__", lambda *_: pytest.fail("read prepared a backend"))
    assert read_native_target(store.root_directory, target["handle"]) == target
    with pytest.raises(KeyError):
        read_native_target(store.root_directory, "missing")
    assert len(calls) == 2


@pytest.mark.parametrize("native_first", [True, False])
def test_cross_kind_collisions_conflict_in_both_directions(tmp_path, native_first):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    spec = commission_spec(tmp_path)
    spec["handle"] = target["handle"]
    if native_first:
        store.register_native_target(target)
        with pytest.raises(DurableExecutionError) as failure:
            store.commission(spec)
    else:
        store.commission(spec)
        with pytest.raises(DurableExecutionError) as failure:
            store.register_native_target(target)
    assert failure.value.failure["code"] == "identity_conflict"
    assert event_count(store) == (0 if native_first else 1)


def test_publication_keeps_original_bytes_and_cursor_after_cleanup_and_restart(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    raw, publication = receipt_and_publication(target)
    receipt_path = tmp_path / "local-exit-receipt.json"
    receipt_path.write_bytes(raw)
    row = store.publish_native_event(target["handle"], publication, receipt_bytes=receipt_path.read_bytes())
    assert row == {"cursor": 1, "handle": target["handle"], "event": "state_changed",
                   "record_ref": publication["record_ref"]}
    receipt_path.unlink()
    restarted = DurableExecutionStore(store.root_directory)
    loaded = restarted.native_publication(target["handle"], publication["record_ref"])
    assert loaded == {"publication": publication, "cursor": row["cursor"], "receipt_bytes": raw}
    loaded["publication"]["occurred_at"] = "2026-10-21T17:00:00Z"
    assert restarted.publish_native_event(target["handle"], publication, receipt_bytes=raw) == row
    assert restarted.native_publication(target["handle"], publication["record_ref"])["publication"] == publication
    with restarted._connect() as db:
        assert db.execute("SELECT observed_at FROM events").fetchone()[0] != publication["occurred_at"]
        assert db.execute("SELECT typeof(receipt_bytes) FROM native_publications").fetchone()[0] == "blob"
    assert event_count(restarted) == 1
    assert restarted.return_page(target["owner_episode_id"], 0, 10)["items"] == []
    with pytest.raises(KeyError):
        restarted.native_publication(target["handle"], "missing")


def test_changed_bytes_or_metadata_conflict_without_rewriting_original(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    raw, publication = receipt_and_publication(target)
    original = store.publish_native_event(target["handle"], publication, receipt_bytes=raw)
    changed_metadata = {**publication, "occurred_at": "2026-10-21T17:00:00Z"}
    changed_bytes, changed_publication = receipt_and_publication(target, status="1")
    for value, data in ((changed_metadata, raw), (changed_publication, changed_bytes)):
        with pytest.raises(DurableExecutionError) as failure:
            store.publish_native_event(target["handle"], value, receipt_bytes=data)
        assert failure.value.failure["code"] == "identity_conflict"
    assert store.native_publication(target["handle"], publication["record_ref"]) == {
        "publication": publication, "cursor": original["cursor"], "receipt_bytes": raw}
    assert event_count(store) == 1


@pytest.mark.parametrize("raw", [b"", b"different bytes", "not bytes", bytearray(b"not bytes"), None])
def test_missing_or_mismatched_receipt_bytes_create_no_event(tmp_path, raw):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    _, publication = receipt_and_publication(target)
    with pytest.raises(ValueError):
        store.publish_native_event(target["handle"], publication, receipt_bytes=raw)
    assert event_count(store) == 0
    with pytest.raises(KeyError):
        store.native_publication(target["handle"], publication["record_ref"])


def test_unknown_publication_identity_is_key_error(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    with pytest.raises(KeyError):
        publish(store, target)
    assert event_count(store) == 0


def test_receipt_publication_and_global_event_rollback_together(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    with store._connect(write=True) as db:
        db.execute("CREATE TRIGGER fixture_publication_failure BEFORE INSERT ON native_publications "
                   "BEGIN SELECT RAISE(ABORT, 'fixture storage unavailable'); END")
    with pytest.raises(DurableExecutionError) as failure:
        publish(store, target)
    assert failure.value.failure["code"] == "storage_failure"
    with store._connect() as db:
        assert db.execute("SELECT count(*) FROM native_publications").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 0
    with store._connect(write=True) as db:
        db.execute("DROP TRIGGER fixture_publication_failure")
    assert publish(store, target)["cursor"] == 1


def test_storage_failure_keeps_existing_error_code(tmp_path, monkeypatch):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    def unavailable(*_args, **_kwargs):
        raise sqlite3.OperationalError("fixture storage unavailable")
    monkeypatch.setattr(sqlite3, "connect", unavailable)
    with pytest.raises(DurableExecutionError) as failure:
        publish(store, target)
    assert failure.value.failure["code"] == "storage_failure"


def test_concurrent_identical_publications_keep_one_physical_receipt_and_cursor(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    with ThreadPoolExecutor(max_workers=6) as workers:
        rows = list(workers.map(lambda _: publish(store, target), range(12)))
    assert all(row == rows[0] for row in rows)
    assert event_count(store) == 1
    with store._connect() as db:
        assert db.execute("SELECT count(*) FROM native_publications").fetchone()[0] == 1


def test_mixed_native_and_episode_events_keep_global_cursor_order(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    spec = commission_spec(tmp_path)
    store.commission(spec)
    first = store.record_progress(spec["handle"], "fixture:first", "first")
    target = registration()
    store.register_native_target(target)
    native = publish(store, target)
    final = store.record_progress(spec["handle"], "fixture:final", "final")
    selected = condition(target)
    selected["events"].append({"handle": spec["handle"], "event": "progress_committed", "after_cursor": 0})
    wake = asyncio.run(store.wait_events(selected))
    assert wake["reason"] == "progress_committed"
    assert wake["events"] == [first, native]
    selected["events"][1]["after_cursor"] = first["cursor"]
    wake = asyncio.run(store.wait_events(selected))
    assert wake["reason"] == "state_changed"
    assert wake["events"] == [native, final]
    assert first["cursor"] < native["cursor"] < final["cursor"]


@pytest.mark.parametrize("event", ["returned", "progress_committed"])
def test_native_unsupported_event_rejected_even_if_another_selection_can_wake(tmp_path, event):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    publish(store, target)
    selected = condition(target, event=event)
    selected["events"].append({"handle": target["handle"], "event": "state_changed", "after_cursor": 0})
    with pytest.raises(ValueError, match="native targets support only state_changed"):
        asyncio.run(store.wait_events(selected))


def test_unknown_wait_target_remains_key_error(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    with pytest.raises(KeyError):
        asyncio.run(store.wait_events(condition(registration())))


def test_native_wait_before_and_during_subscription_uses_no_episode_or_liveness_ports(tmp_path, monkeypatch):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    for name in ("status", "load_commission", "return_page", "load_return"):
        monkeypatch.setattr(store, name, lambda *_args, **_kwargs: pytest.fail("native wait used episode state"))
    monkeypatch.setattr(durable, "process_identity", lambda *_: pytest.fail("native wait probed process liveness"))
    monkeypatch.setattr(os, "pidfd_open", lambda *_: pytest.fail("native wait opened a pidfd"))
    async def scenario():
        waiter = asyncio.create_task(store.wait_events(condition(target)))
        await asyncio.sleep(0)  # Subscription and empty ledger read are installed.
        assert not waiter.done()  # Registration alone cannot satisfy the condition.
        row = publish(store, target)
        wake = await asyncio.wait_for(waiter, 10)
        assert wake["events"] == [row]
        assert wake["reason"] == "state_changed"
        earlier = await store.wait_events(condition(target))
        assert earlier["events"] == [row]
        # An arbitrary selected threshold is retained; it claims no observation.
        selected = condition(target, after_cursor=row["cursor"] + 100,
            reconsider_at=(datetime.now(timezone.utc) + timedelta(milliseconds=20)).isoformat())
        later = await store.wait_events(selected)
        assert later["reason"] == "reconsideration" and later["events"] == []
    asyncio.run(scenario())


def test_native_commit_between_empty_read_and_await_is_not_lost(tmp_path, monkeypatch):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    original, inserted = store._matching_events, []
    def arrive_after_read(selected):
        rows = original(selected)
        if not inserted:
            inserted.append(publish(store, target))
        return rows
    monkeypatch.setattr(store, "_matching_events", arrive_after_read)
    wake = asyncio.run(asyncio.wait_for(store.wait_events(condition(target)), 10))
    assert wake["events"] == inserted


def test_native_publication_from_another_process_wakes_existing_subscription(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    raw, publication = receipt_and_publication(target)
    command = """
import json,sys
from method_loop.durable import DurableExecutionStore
result = DurableExecutionStore(sys.argv[1]).publish_native_event(sys.argv[2], json.loads(sys.argv[3]), receipt_bytes=bytes.fromhex(sys.argv[4]))
print(json.dumps(result))
"""
    async def scenario():
        waiter = asyncio.create_task(store.wait_events(condition(target)))
        await asyncio.sleep(0)
        process = starter(command, store.root_directory, target["handle"], canonical(publication), raw.hex())
        output, error = await asyncio.to_thread(process.communicate, timeout=10)
        assert process.returncode == 0, error
        wake = await asyncio.wait_for(waiter, 10)
        assert wake["events"] == [json.loads(output)]
    asyncio.run(scenario())


def test_cancelled_native_wait_closes_notification_and_preserves_target(tmp_path, monkeypatch):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    descriptors = []
    original = durable._DirectoryNotification.__enter__
    def entered(notification):
        descriptors.append(notification.fd)
        return original(notification)
    monkeypatch.setattr(durable._DirectoryNotification, "__enter__", entered)
    async def scenario():
        waiter = asyncio.create_task(store.wait_events(condition(target)))
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert store.native_target(target["handle"]) == target
        assert event_count(store) == 0
        with pytest.raises(OSError):
            os.fstat(descriptors[0])
        row = publish(store, target)
        assert (await store.wait_events(condition(target)))["events"] == [row]
    asyncio.run(scenario())


def test_mixed_wait_preserves_episode_pidfd_recovery(tmp_path):
    store = DurableExecutionStore(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    gate = tmp_path / "gate"
    os.mkfifo(gate)
    spec = commission_spec(tmp_path, arguments={"gate": str(gate)})
    store.commission(spec)
    started = store.start(spec["handle"])
    await_event(store, spec["handle"], "progress_committed")
    async def scenario():
        selected = condition(target)
        selected["events"].append({"handle": spec["handle"], "event": "returned", "after_cursor": 0})
        waiter = asyncio.create_task(store.wait_events(selected))
        await asyncio.sleep(0)
        os.kill(started["execution_identity"]["pid"], signal.SIGKILL)
        wake = await asyncio.wait_for(waiter, 10)
        assert wake["reason"] == "returned"
        assert wake["events"][0]["handle"] == spec["handle"]
    asyncio.run(scenario())
    assert returned(store, spec)["outcome"] == "interrupted"
    assert store.native_target(target["handle"]) == target
    with store._connect() as db:
        assert db.execute("SELECT count(*) FROM native_publications").fetchone()[0] == 0
