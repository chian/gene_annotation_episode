"""Native event transport and byte custody, without native scientific work.

Synthetic receipts establish ledger, notification and identity behavior only, over a real SQLite ledger.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from method_loop.jsonvalue import canonical, content_digest
import gene_annotation_episode.episodic_workflow.episode_support.jobs.native_event_ledger as native_event_ledger
from gene_annotation_episode.episodic_workflow.episode_support.jobs.native_event_ledger import (
    EventTargetError, NativeEventLedger, NativeEventLedgerError, native_target_descriptor, native_target_handle,
    read_native_target, validate_native_publication, validate_native_registration)


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
    return {"version": "event_condition_v1", "events": [{"handle": target["handle"], "event": event,
            "after_cursor": after_cursor}], "reconsider_at": reconsider_at}


def starter(command, *arguments):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parent.parent)
    return subprocess.Popen([sys.executable, "-c", command, *map(str, arguments)],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


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
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    assert store.register_native_target(target) == native_target_descriptor(target)
    assert store.register_native_target(deepcopy(target)) == native_target_descriptor(target)
    assert event_count(store) == 0
    assert store.native_target(target["handle"]) == target
    loaded = store.native_target(target["handle"])
    loaded["native_identity"]["unit"] = "detached-copy.service"
    assert store.native_target(target["handle"]) == target
    for name in ("owner_episode_id", "run_id", "job_ref", "registry_ref", "resource_id"):
        with pytest.raises(NativeEventLedgerError) as failure:
            store.register_native_target({**target, name: "different"})
        assert failure.value.failure["code"] == "identity_conflict"
    with pytest.raises(KeyError):
        store.native_target("missing")
    assert event_count(store) == 0


def test_read_only_native_lookup_creates_no_backend_and_uses_no_writable_connection(tmp_path, monkeypatch):
    absent = tmp_path / "absent-backend"
    with pytest.raises(NativeEventLedgerError) as failure:
        read_native_target(absent, "missing")
    assert failure.value.failure["code"] == "storage_failure"
    assert not absent.exists()
    store = NativeEventLedger(tmp_path / "executions")
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
    monkeypatch.setattr(NativeEventLedger, "__init__", lambda *_: pytest.fail("read prepared a backend"))
    assert read_native_target(store.root_directory, target["handle"]) == target
    with pytest.raises(KeyError):
        read_native_target(store.root_directory, "missing")
    assert len(calls) == 2


def test_publication_keeps_original_bytes_and_cursor_after_cleanup_and_restart(tmp_path):
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    raw, publication = receipt_and_publication(target)
    receipt_path = tmp_path / "local-exit-receipt.json"
    receipt_path.write_bytes(raw)
    row = store.publish_native_event(target["handle"], publication, receipt_bytes=receipt_path.read_bytes())
    assert row == {"cursor": 1, "handle": target["handle"], "event": "state_changed",
                   "record_ref": publication["record_ref"]}
    receipt_path.unlink()
    restarted = NativeEventLedger(store.root_directory)
    loaded = restarted.native_publication(target["handle"], publication["record_ref"])
    assert loaded == {"publication": publication, "cursor": row["cursor"], "receipt_bytes": raw}
    loaded["publication"]["occurred_at"] = "2026-10-21T17:00:00Z"
    assert restarted.publish_native_event(target["handle"], publication, receipt_bytes=raw) == row
    assert restarted.native_publication(target["handle"], publication["record_ref"])["publication"] == publication
    with restarted._connect() as db:
        assert db.execute("SELECT observed_at FROM events").fetchone()[0] != publication["occurred_at"]
        assert db.execute("SELECT typeof(receipt_bytes) FROM native_publications").fetchone()[0] == "blob"
    assert event_count(restarted) == 1
    with pytest.raises(KeyError):
        restarted.native_publication(target["handle"], "missing")


def test_changed_bytes_or_metadata_conflict_without_rewriting_original(tmp_path):
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    raw, publication = receipt_and_publication(target)
    original = store.publish_native_event(target["handle"], publication, receipt_bytes=raw)
    changed_metadata = {**publication, "occurred_at": "2026-10-21T17:00:00Z"}
    changed_bytes, changed_publication = receipt_and_publication(target, status="1")
    for value, data in ((changed_metadata, raw), (changed_publication, changed_bytes)):
        with pytest.raises(NativeEventLedgerError) as failure:
            store.publish_native_event(target["handle"], value, receipt_bytes=data)
        assert failure.value.failure["code"] == "identity_conflict"
    assert store.native_publication(target["handle"], publication["record_ref"]) == {
        "publication": publication, "cursor": original["cursor"], "receipt_bytes": raw}
    assert event_count(store) == 1


@pytest.mark.parametrize("raw", [b"", b"different bytes", "not bytes", bytearray(b"not bytes"), None])
def test_missing_or_mismatched_receipt_bytes_create_no_event(tmp_path, raw):
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    _, publication = receipt_and_publication(target)
    with pytest.raises(ValueError):
        store.publish_native_event(target["handle"], publication, receipt_bytes=raw)
    assert event_count(store) == 0
    with pytest.raises(KeyError):
        store.native_publication(target["handle"], publication["record_ref"])


def test_unknown_publication_identity_is_key_error(tmp_path):
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    with pytest.raises(KeyError):
        publish(store, target)
    assert event_count(store) == 0


def test_receipt_publication_and_global_event_rollback_together(tmp_path):
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    with store._connect(write=True) as db:
        db.execute("CREATE TRIGGER fixture_publication_failure BEFORE INSERT ON native_publications "
                   "BEGIN SELECT RAISE(ABORT, 'fixture storage unavailable'); END")
    with pytest.raises(NativeEventLedgerError) as failure:
        publish(store, target)
    assert failure.value.failure["code"] == "storage_failure"
    with store._connect() as db:
        assert db.execute("SELECT count(*) FROM native_publications").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 0
    with store._connect(write=True) as db:
        db.execute("DROP TRIGGER fixture_publication_failure")
    assert publish(store, target)["cursor"] == 1


def test_unreadable_database_is_a_structured_storage_failure(tmp_path):
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    database = store.root_directory / "executions.sqlite"
    for leftover in store.root_directory.glob("executions.sqlite-*"):
        leftover.unlink()
    database.write_bytes(b"these bytes are not an SQLite database\n" * 200)
    with pytest.raises(NativeEventLedgerError) as failure:
        publish(store, target)
    assert failure.value.failure == {"code": "storage_failure", "affected_refs": [str(database)]}
    with pytest.raises(NativeEventLedgerError) as failure:
        read_native_target(store.root_directory, target["handle"])
    assert failure.value.failure == {"code": "storage_failure", "affected_refs": [str(database)]}


def test_concurrent_identical_publications_keep_one_physical_receipt_and_cursor(tmp_path):
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    with ThreadPoolExecutor(max_workers=6) as workers:
        rows = list(workers.map(lambda _: publish(store, target), range(12)))
    assert all(row == rows[0] for row in rows)
    assert event_count(store) == 1
    with store._connect() as db:
        assert db.execute("SELECT count(*) FROM native_publications").fetchone()[0] == 1


def test_events_of_several_native_targets_keep_global_cursor_order(tmp_path):
    store = NativeEventLedger(tmp_path / "executions")
    targets = [registration(unit=f"fixture-native-{name}.service") for name in ("a", "b", "c")]
    for target in targets:
        store.register_native_target(target)
    # Published in an order that differs from the selection order below.
    second, first, third = targets
    rows = [publish(store, target) for target in (first, second, third)]
    assert rows[0]["cursor"] < rows[1]["cursor"] < rows[2]["cursor"]
    selected = condition(second)
    selected["events"] += [{"handle": target["handle"], "event": "state_changed", "after_cursor": 0}
                           for target in (third, first)]
    wake = asyncio.run(store.wait_events(selected))
    assert wake["reason"] == "state_changed"
    assert wake["events"] == rows
    # A selection that has already seen one target's event receives only the others.
    selected["events"][2]["after_cursor"] = rows[0]["cursor"]
    assert asyncio.run(store.wait_events(selected))["events"] == rows[1:]


def test_wait_on_a_selected_set_wakes_with_only_the_target_that_published(tmp_path):
    store = NativeEventLedger(tmp_path / "executions")
    a, b = registration(unit="fixture-native-a.service"), registration(unit="fixture-native-b.service")
    store.register_native_target(a)
    store.register_native_target(b)
    async def scenario():
        selected = condition(a)
        selected["events"].append({"handle": b["handle"], "event": "state_changed", "after_cursor": 0})
        waiter = asyncio.create_task(store.wait_events(selected))
        await asyncio.sleep(0)  # Let the ledger install its notification fd.
        assert not waiter.done()
        row_b = publish(store, b)
        wake = await asyncio.wait_for(waiter, 10)
        assert wake["reason"] == "state_changed" and wake["events"] == [row_b]
        # The other target's later event is found by a wait that starts after it was committed.
        row_a = publish(store, a)
        assert (await asyncio.wait_for(store.wait_events(condition(a)), 10))["events"] == [row_a]
    asyncio.run(scenario())


@pytest.mark.parametrize("event", ["returned", "progress_committed"])
def test_native_unsupported_event_rejected_even_if_another_selection_can_wake(tmp_path, event):
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    publish(store, target)
    selected = condition(target, event=event)
    selected["events"].append({"handle": target["handle"], "event": "state_changed", "after_cursor": 0})
    with pytest.raises(EventTargetError, match="native targets support only state_changed") as refusal:
        asyncio.run(store.wait_events(selected))
    assert refusal.value.code == "unsupported_wait_event"
    assert refusal.value.affected_refs == (target["handle"],)


def test_unknown_wait_target_is_refused(tmp_path):
    store = NativeEventLedger(tmp_path / "executions")
    with pytest.raises(EventTargetError, match="unknown_wait_target") as refusal:
        asyncio.run(store.wait_events(condition(registration())))
    assert refusal.value.affected_refs == (registration()["handle"],)


def test_native_wait_before_and_during_subscription_and_at_reconsideration(tmp_path):
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
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
    store = NativeEventLedger(tmp_path / "executions")
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
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    raw, publication = receipt_and_publication(target)
    command = """
import json,sys
from gene_annotation_episode.episodic_workflow.episode_support.jobs.native_event_ledger import NativeEventLedger
result = NativeEventLedger(sys.argv[1]).publish_native_event(sys.argv[2], json.loads(sys.argv[3]), receipt_bytes=bytes.fromhex(sys.argv[4]))
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
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    descriptors = []
    original = native_event_ledger._DirectoryNotification.__enter__
    def entered(notification):
        descriptors.append(notification.fd)
        return original(notification)
    monkeypatch.setattr(native_event_ledger._DirectoryNotification, "__enter__", entered)
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


def test_quiet_native_wait_uses_notifications_without_repeated_ledger_scans(tmp_path, monkeypatch):
    store = NativeEventLedger(tmp_path / "executions")
    target = registration()
    store.register_native_target(target)
    scans = []
    original = store._matching_events
    def observe(selected):
        scans.append("ledger observation")
        return original(selected)
    monkeypatch.setattr(store, "_matching_events", observe)
    selected = condition(target, reconsider_at=(datetime.now(timezone.utc) + timedelta(milliseconds=50)).isoformat())
    wake = asyncio.run(asyncio.wait_for(store.wait_events(selected), 10))
    assert wake["reason"] == "reconsideration" and wake["events"] == []
    assert len(scans) <= 3  # initial observation and chosen reconsideration
