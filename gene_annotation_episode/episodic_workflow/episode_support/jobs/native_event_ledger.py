"""The durable ledger of native job events: registered targets, service-exit publications and waits.

A detached local job is named by its reserved native identity (one systemd user service and the digest of its
request). Its owner registers that identity as an event target; when the job's service-exit receipt is committed,
the original receipt bytes are published once as the target's ``state_changed`` event. A wait selects targets and
the cursor it last saw, and returns the later events or its reconsideration time.

This module persists identities, receipts and event cursors. It does not choose scientific work, resources,
continuation or credit, and it runs nothing.

The backend is one SQLite database (``executions.sqlite``) in the ledger directory and requires Linux inotify.
Filesystem notification is only a wake hint: matching events always come from the durable cursor ledger. No open
connection is retained by the ledger.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import struct

from method_loop.jsonvalue import canonical, content_digest


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _copy(value):
    return json.loads(canonical(value))


def _text(value, name):
    if not isinstance(value, str) or not value:
        raise ValueError(name + " must be nonempty text")
    return value


def _exact(value, fields, name):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError(name + " fields must be exact")


def _digest(value, name):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(name + " must be a sha256 digest")


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be UTC text")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be UTC text") from exc
    if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must be UTC")
    return stamp


def native_target_handle(native_identity):
    """Name one reserved native unit/request, independent of mutable status."""
    identity = _copy(native_identity)
    _exact(identity, "kind unit request_sha256", "native identity")
    if identity["kind"] != "systemd_user_service":
        raise ValueError("unsupported native identity kind")
    _text(identity["unit"], "native unit")
    _digest(identity["request_sha256"], "native request digest")
    return "native_event_target_" + content_digest(identity)[:24]


def validate_native_registration(value):
    """Copy exact identity metadata; the application authenticates ownership."""
    value = _copy(value)
    _exact(value, "version handle run_id owner_episode_id job_ref registry_ref resource_id native_identity",
           "native event registration")
    if value["version"] != "native_event_registration":
        raise ValueError("unsupported native event registration")
    for name in ("handle", "run_id", "owner_episode_id", "job_ref", "registry_ref", "resource_id"):
        _text(value[name], name)
    if value["handle"] != native_target_handle(value["native_identity"]):
        raise ValueError("native target handle differs from its identity")
    return value


def native_target_descriptor(registration):
    """Expose a native event reference without private execution identities."""
    registration = validate_native_registration(registration)
    return {"version": "native_event_target",
        **{name: registration[name] for name in ("handle", "job_ref", "registry_ref", "resource_id")},
        "event": "state_changed", "cause": "service_exit_receipt_committed"}


def validate_native_publication(value):
    """Copy publication provenance without implying native writer closure."""
    value = _copy(value)
    _exact(value, "version event cause record_ref receipt_sha256 occurred_at", "native event publication")
    if (value["version"] != "native_event_publication" or value["event"] != "state_changed"
            or value["cause"] != "service_exit_receipt_committed"):
        raise ValueError("unsupported native event publication")
    _digest(value["receipt_sha256"], "native receipt digest")
    if value["record_ref"] != "native_event_record_" + value["receipt_sha256"][:24]:
        raise ValueError("native event record differs from its receipt digest")
    _timestamp(value["occurred_at"])
    return value


class NativeEventLedgerError(RuntimeError):
    """A declared ledger failure; ``failure`` is ``{'code': ..., 'affected_refs': [...]}``.

    ``identity_conflict``: a registration or publication differs from the one already recorded under its handle.
    ``storage_failure``: the ledger database could not be read or written.
    """
    CODES = frozenset({"identity_conflict", "storage_failure"})

    def __init__(self, code, *, affected_refs):
        if code not in self.CODES:
            raise ValueError("undeclared native event ledger failure code")
        refs = list(affected_refs)
        for ref in refs:
            _text(ref, "affected_refs")
        self.failure = {"code": code, "affected_refs": refs}
        super().__init__(code)


class EventTargetError(ValueError):
    """A selected reference/event cannot be used by the bound event provider.

    Application bindings retain their own visibility rules. This exception
    carries the offending references without choosing replacement work.
    """
    CODES = frozenset({"unknown_wait_target", "unsupported_wait_event",
                       "wait_target_not_visible", "wait_target_unavailable"})

    def __init__(self, code, *, affected_refs, detail=None):
        if code not in self.CODES:
            raise ValueError("undeclared_event_target_failure_code")
        refs = tuple(affected_refs)
        if not refs or any(type(ref) is not str or not ref for ref in refs):
            raise ValueError("event_target_failure_references_required")
        self.code, self.affected_refs = code, refs
        super().__init__(code if detail is None else _text(detail, "detail"))


def read_native_target(root_directory, handle):
    """Read an existing native registration without preparing a backend.

    Metadata discovery must neither create directories/tables nor expose a
    writable ledger. SQLite's read-only URI also prevents a missing database
    from being created during this lookup.
    """
    _text(handle, "handle")
    database = Path(root_directory).resolve() / "executions.sqlite"
    db = None
    try:
        db = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=30)
        row = db.execute("SELECT registration FROM native_targets WHERE handle=?", (handle,)).fetchone()
    except sqlite3.Error as error:
        raise NativeEventLedgerError("storage_failure", affected_refs=[str(database)]) from error
    finally:
        if db is not None:
            db.close()
    if row is None:
        raise KeyError(handle)
    return validate_native_registration(json.loads(row[0]))


class NativeEventLedger:
    """The native targets, their one service-exit publication each, and the event cursor, in one directory."""

    def __init__(self, root_directory):
        self.root_directory = Path(root_directory).resolve()
        self.root_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._database = self.root_directory / "executions.sqlite"
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    cursor INTEGER PRIMARY KEY AUTOINCREMENT, handle TEXT NOT NULL,
                    event TEXT NOT NULL, record_ref TEXT, operation_key TEXT,
                    observed_at TEXT NOT NULL,
                    UNIQUE(handle,event,operation_key));
                CREATE TABLE IF NOT EXISTS native_targets (
                    handle TEXT PRIMARY KEY, registration TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS native_publications (
                    handle TEXT PRIMARY KEY REFERENCES native_targets(handle),
                    record_ref TEXT NOT NULL, publication TEXT NOT NULL,
                    receipt_bytes BLOB NOT NULL,
                    cursor INTEGER NOT NULL UNIQUE REFERENCES events(cursor));
            """)

    @contextmanager
    def _connect(self, *, write=False):
        # The storage lock wait is unrelated to a selected reconsideration time.
        db = None
        try:
            db = sqlite3.connect(self._database, timeout=30)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA synchronous=FULL")
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except sqlite3.Error as error:
            if db is not None:
                try:
                    db.rollback()
                except sqlite3.Error:
                    pass
            raise NativeEventLedgerError("storage_failure", affected_refs=[str(self._database)]) from error
        except BaseException:
            if db is not None:
                db.rollback()
            raise
        finally:
            if db is not None:
                db.close()

    @staticmethod
    def _event(db, handle, event, *, record_ref=None, operation_key=None):
        return db.execute("INSERT INTO events(handle,event,record_ref,operation_key,observed_at) VALUES(?,?,?,?,?)",
                          (handle, event, record_ref, operation_key, utc_now())).lastrowid

    def register_native_target(self, registration):
        registration = validate_native_registration(registration)
        handle, encoded = registration["handle"], canonical(registration)
        with self._connect(write=True) as db:
            previous = db.execute("SELECT registration FROM native_targets WHERE handle=?", (handle,)).fetchone()
            if previous:
                if previous["registration"] != encoded:
                    raise NativeEventLedgerError("identity_conflict", affected_refs=[handle])
            else:
                # Registration establishes identity only, never an event.
                db.execute("INSERT INTO native_targets(handle,registration) VALUES(?,?)", (handle, encoded))
        return native_target_descriptor(registration)

    def native_target(self, handle):
        return read_native_target(self.root_directory, handle)

    def publish_native_event(self, handle, publication, *, receipt_bytes: bytes):
        _text(handle, "handle")
        publication = validate_native_publication(publication)
        if (not isinstance(receipt_bytes, bytes) or not receipt_bytes
                or hashlib.sha256(receipt_bytes).hexdigest() != publication["receipt_sha256"]):
            raise ValueError("native receipt bytes must match the publication digest")
        encoded = canonical(publication)
        with self._connect(write=True) as db:
            if not db.execute("SELECT 1 FROM native_targets WHERE handle=?", (handle,)).fetchone():
                raise KeyError(handle)
            previous = db.execute("SELECT * FROM native_publications WHERE handle=?", (handle,)).fetchone()
            if previous:
                if previous["publication"] != encoded or previous["receipt_bytes"] != receipt_bytes:
                    raise NativeEventLedgerError("identity_conflict", affected_refs=[handle, publication["record_ref"]])
                cursor = previous["cursor"]
            else:
                cursor = self._event(db, handle, "state_changed", record_ref=publication["record_ref"],
                                     operation_key="service_exit_receipt_committed")
                db.execute("INSERT INTO native_publications(handle,record_ref,publication,receipt_bytes,cursor) VALUES(?,?,?,?,?)",
                    (handle, publication["record_ref"], encoded, sqlite3.Binary(receipt_bytes), cursor))
        return {"cursor": cursor, "handle": handle, "event": "state_changed",
                "record_ref": publication["record_ref"]}

    def native_publication(self, handle, record_ref):
        """Internal receipt custody; original bytes never enter a parent form."""
        _text(handle, "handle")
        _text(record_ref, "record_ref")
        with self._connect() as db:
            row = db.execute("SELECT * FROM native_publications WHERE handle=? AND record_ref=?",
                             (handle, record_ref)).fetchone()
        if row is None:
            raise KeyError((handle, record_ref))
        return {"publication": json.loads(row["publication"]), "cursor": row["cursor"],
                "receipt_bytes": row["receipt_bytes"]}

    def _check_selected_targets(self, condition):
        """Every selected handle is a registered native target and every selected event is its one event."""
        with self._connect() as db:
            registered = set()
            for selected in condition["events"]:
                handle = selected["handle"]
                if handle not in registered:
                    if not db.execute("SELECT 1 FROM native_targets WHERE handle=?", (handle,)).fetchone():
                        raise EventTargetError("unknown_wait_target", affected_refs=[handle])
                    registered.add(handle)
                if selected["event"] != "state_changed":
                    raise EventTargetError("unsupported_wait_event", affected_refs=[handle],
                        detail="native targets support only state_changed")

    def validate_event_targets(self, condition):
        """Check identities/event kinds in an already shape-validated choice.

        This reads registrations only: no status observation, event publication,
        deadline fallback, work dispatch or application ownership decision.
        """
        condition = _copy(condition)
        self._check_selected_targets(condition)
        return condition

    def _matching_events(self, condition):
        with self._connect() as db:
            matches = {}
            for selected in condition["events"]:
                for row in db.execute("SELECT cursor,handle,event,record_ref FROM events WHERE handle=? AND event=? AND cursor>? ORDER BY cursor LIMIT 1",
                    (selected["handle"], selected["event"], selected["after_cursor"])):
                    matches[row["cursor"]] = dict(row)
        return [matches[key] for key in sorted(matches)]

    async def wait_events(self, condition):
        condition = _copy(condition)
        _exact(condition, "version events reconsider_at", "event condition")
        if condition["version"] != "event_condition" or not isinstance(condition["events"], list):
            raise ValueError("unsupported event condition")
        for item in condition["events"]:
            _exact(item, "handle event after_cursor", "selected event")
            _text(item["handle"], "event handle")
            if (not isinstance(item["event"], str) or not item["event"]
                    or type(item["after_cursor"]) is not int or item["after_cursor"] < 0):
                raise ValueError("invalid selected event")
        deadline = _timestamp(condition["reconsider_at"]) if condition["reconsider_at"] is not None else None
        if not condition["events"] and deadline is None:
            raise ValueError("wait requires selected events or reconsideration time")
        self._check_selected_targets(condition)
        # Subscribe BEFORE inspecting the persistent ledger. A commit anywhere
        # in the inspection/subscription boundary therefore remains observable.
        with _DirectoryNotification(self.root_directory) as notification:
            while True:
                events = self._matching_events(condition)
                if events:
                    return {"version": "event_wake", "reason": events[0]["event"],
                        "observed_at": utc_now(), "events": events,
                        "reconsider_at": condition["reconsider_at"]}
                if deadline is not None and datetime.now(timezone.utc) >= deadline:
                    return {"version": "event_wake", "reason": "reconsideration",
                        "observed_at": utc_now(), "events": [], "reconsider_at": condition["reconsider_at"]}
                await notification.wait(deadline)


class _DirectoryNotification:
    """One Linux fd per active wait, closed on success or cancellation."""
    def __init__(self, path):
        libc = ctypes.CDLL(None, use_errno=True)
        init = libc.inotify_init1
        init.argtypes, init.restype = [ctypes.c_int], ctypes.c_int
        add = libc.inotify_add_watch
        add.argtypes, add.restype = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32], ctypes.c_int
        self.fd = init(os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), "inotify_init1")
        # Actual writes, including SQLite's WAL. File opens/closes and creation
        # are excluded: a read connection must never wake its own quiet wait.
        if add(self.fd, os.fsencode(path), 0x2) < 0:
            error = ctypes.get_errno()
            os.close(self.fd)
            raise OSError(error, "inotify_add_watch")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        os.close(self.fd)

    async def wait(self, deadline):
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        def ready():
            relevant = False
            try:
                while data := os.read(self.fd, 65536):
                    offset = 0
                    while offset < len(data):
                        _watch, mask, _cookie, length = struct.unpack_from("iIII", data, offset)
                        name = data[offset + 16:offset + 16 + length].rstrip(b"\0")
                        relevant |= bool(mask & 0x4000) or name in (b"executions.sqlite", b"executions.sqlite-wal")
                        offset += 16 + length
            except BlockingIOError:
                pass
            # WAL shared-memory coordination changes on an ordinary read.
            # Those writes are not durable events and must not cause rescans.
            if relevant and not future.done():
                future.set_result(None)
        loop.add_reader(self.fd, ready)
        timer = None
        try:
            if deadline is not None:
                delay = max(0, (deadline - datetime.now(timezone.utc)).total_seconds())
                timer = loop.call_later(delay, lambda: None if future.done() else future.set_result(None))
            await future
        finally:
            loop.remove_reader(self.fd)
            if timer is not None:
                timer.cancel()


__all__ = ['EventTargetError', 'NativeEventLedger', 'NativeEventLedgerError', 'native_target_descriptor',
           'native_target_handle', 'read_native_target', 'validate_native_publication',
           'validate_native_registration']
