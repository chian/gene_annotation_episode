"""Durable execution of a selected, parent-owned Episode commission.

This module persists C1/C3 records and process identities. It does not choose
work, resources, retries, continuation or scientific credit. A bootstrap can be
repeated in the crash window before a claim; its atomic claim permits only one
process incarnation to invoke the caller's reconstruction factory. A dead
claimed incarnation produces an interruption, never another work attempt.

The local backend requires Linux /proc and inotify. Filesystem notification is
only a wake hint: matching events always come from the durable cursor ledger.
No open connection, process object or child history is retained by the store.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import struct
import subprocess
import sys

from .communication import ReportContract
from .episode import EpisodeCompletion, EpisodeGoal
from .identities import EpisodeRef, normalize_structural_path


FAILURE_CODES = frozenset({"identity_conflict", "unavailable_binding", "unavailable_resource",
    "invalid_return", "storage_failure", "interrupted_execution", "execution_failed"})
_EVENTS = frozenset({"returned", "state_changed", "progress_committed"})


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    """Finite JSON with string keys, without coercing an unsupported value."""
    def plain(item):
        if isinstance(item, Mapping):
            if any(not isinstance(key, str) for key in item):
                raise ValueError("JSON record keys must be strings")
            return {key: plain(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [plain(child) for child in item]
        if item is None or type(item) in (str, bool, int, float):
            return item
        raise ValueError("record must contain finite JSON values")
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def content_digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


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


def _references(value, name):
    if not isinstance(value, list):
        raise ValueError(name + " must be an array")
    for item in value:
        _text(item, name)


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
    if value["version"] != "native_event_registration_v1":
        raise ValueError("unsupported native event registration")
    for name in ("handle", "run_id", "owner_episode_id", "job_ref", "registry_ref", "resource_id"):
        _text(value[name], name)
    if value["handle"] != native_target_handle(value["native_identity"]):
        raise ValueError("native target handle differs from its identity")
    return value


def native_target_descriptor(registration):
    """Expose a native event reference without private execution identities."""
    registration = validate_native_registration(registration)
    return {"version": "native_event_target_v1",
        **{name: registration[name] for name in ("handle", "job_ref", "registry_ref", "resource_id")},
        "event": "state_changed", "cause": "service_exit_receipt_committed"}


def validate_native_publication(value):
    """Copy publication provenance without implying native writer closure."""
    value = _copy(value)
    _exact(value, "version event cause record_ref receipt_sha256 occurred_at", "native event publication")
    if (value["version"] != "native_event_publication_v1" or value["event"] != "state_changed"
            or value["cause"] != "service_exit_receipt_committed"):
        raise ValueError("unsupported native event publication")
    _digest(value["receipt_sha256"], "native receipt digest")
    if value["record_ref"] != "native_event_record_" + value["receipt_sha256"][:24]:
        raise ValueError("native event record differs from its receipt digest")
    _timestamp(value["occurred_at"])
    return value


class DurableExecutionError(RuntimeError):
    """Declared execution failure; prose is retained in a diagnostic artifact.

    Reconstruction bindings can raise this with references to already committed
    partial contributions. The runner never infers completion from those refs.
    """
    def __init__(self, code, *, affected_refs=(), diagnostic_ref=None, partial_record_refs=()):
        self.failure = {"code": code, "affected_refs": list(affected_refs),
                        "diagnostic_ref": diagnostic_ref,
                        "partial_record_refs": list(partial_record_refs)}
        validate_failure(self.failure)
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


def validate_failure(value):
    _exact(value, "code affected_refs diagnostic_ref partial_record_refs", "failure")
    if value["code"] not in FAILURE_CODES:
        raise ValueError("undeclared durable execution failure code")
    _references(value["affected_refs"], "affected_refs")
    _references(value["partial_record_refs"], "partial_record_refs")
    if value["diagnostic_ref"] is not None:
        _text(value["diagnostic_ref"], "diagnostic_ref")


def read_native_target(root_directory, handle):
    """Read an existing native registration without preparing a backend.

    Metadata discovery must neither create directories/tables nor expose a
    writable store. SQLite's read-only URI also prevents a missing database
    from being created during this lookup.
    """
    _text(handle, "handle")
    database = Path(root_directory).resolve() / "executions.sqlite"
    db = None
    try:
        db = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=30)
        row = db.execute("SELECT registration FROM native_targets WHERE handle=?", (handle,)).fetchone()
    except sqlite3.Error as error:
        raise DurableExecutionError("storage_failure", affected_refs=[str(database)]) from error
    finally:
        if db is not None:
            db.close()
    if row is None:
        raise KeyError(handle)
    return validate_native_registration(json.loads(row[0]))


def validate_commission(spec):
    """Validate generic ownership/identity, leaving semantic Store checks to C1.

    Input bytes, normalized domain scope, frozen receipt inheritance and pinned
    binding code/configuration are verified by the producing and reopening
    application binding. This backend has no application imports or authority
    to substitute newer versions.
    """
    spec = _copy(spec)
    _exact(spec, "version handle operation_key run_id parent child input_versions runtime_binding constraints resource_selection expectation_snapshot_refs", "commission")
    if spec["version"] != "episode_commission_v1":
        raise ValueError("unsupported commission version")
    for name in ("handle", "operation_key", "run_id"):
        _text(spec[name], name)
    parent, child = spec["parent"], spec["child"]
    _exact(parent, "episode_id goal_id path", "parent")
    _exact(child, "episode_id role key path request scope", "child")
    for name in ("episode_id", "goal_id"):
        _text(parent[name], name)
    for name in ("episode_id", "role", "key"):
        _text(child[name], name)
    parent_path = normalize_structural_path(parent["path"])
    child_path = normalize_structural_path(child["path"])
    if (child_path[:-1] != parent_path or child_path[-1] != (child["role"], child["key"])
            or parent["episode_id"] != EpisodeRef(spec["run_id"], parent_path).episode_id
            or child["episode_id"] != EpisodeRef(spec["run_id"], child_path).episode_id):
        raise DurableExecutionError("identity_conflict", affected_refs=[spec["handle"]])
    request = child["request"]
    _exact(request, "goal message report_contract", "request")
    goal = EpisodeGoal.from_record(request["goal"])
    if goal.parent_goal_id != parent["goal_id"]:
        raise DurableExecutionError("identity_conflict", affected_refs=[spec["handle"]])
    if not isinstance(request["message"], dict) or not isinstance(child["scope"], dict):
        raise ValueError("commission message and scope must be JSON objects")
    ReportContract.from_record(request["report_contract"])
    if not isinstance(spec["input_versions"], list):
        raise ValueError("input_versions must be an array")
    for item in spec["input_versions"]:
        _exact(item, "reference version content_sha256", "input version")
        _text(item["reference"], "input reference")
        if item["version"] is not None:
            _text(item["version"], "input version")
        if item["content_sha256"] is not None:
            _digest(item["content_sha256"], "input content digest")
    binding = spec["runtime_binding"]
    _exact(binding, "factory_module factory_name arguments implementation_sha256 settings_sha256", "runtime binding")
    for name in ("factory_module", "factory_name"):
        _text(binding[name], name)
        if any(not part.isidentifier() for part in binding[name].split(".")):
            raise ValueError("factory references must be module/attribute names")
    if not isinstance(binding["arguments"], dict) or not isinstance(spec["constraints"], dict):
        raise ValueError("binding arguments and constraints must be JSON objects")
    _digest(binding["implementation_sha256"], "implementation digest")
    _digest(binding["settings_sha256"], "settings digest")
    selected = spec["resource_selection"]
    if selected is not None:
        _exact(selected, "resource_id kind allocation capability_binding_ref", "resource selection")
        _text(selected["resource_id"], "resource_id")
        _text(selected["capability_binding_ref"], "capability_binding_ref")
        if selected["kind"] not in ("api", "local", "hpc"):
            raise ValueError("unknown resource kind")
        allocation = selected["allocation"]
        _exact(allocation, "cpu memory_bytes scratch_bytes wall_seconds", "allocation")
        for name, value in allocation.items():
            if value is not None and (type(value) not in ((int, float) if name == "wall_seconds" else (int,)) or value <= 0):
                raise ValueError("resource allocations must be positive or null")
    _references(spec["expectation_snapshot_refs"], "expectation_snapshot_refs")
    return spec


def _archive_descriptor(value):
    if value is None:
        return
    _exact(value, "file sha256 index_sha256", "archive descriptor")
    name = _text(value["file"], "archive file")
    if Path(name).name != name or name in (".", ".."):
        raise ValueError("archive descriptor must name a file in its archive")
    _digest(value["sha256"], "archive sha256")
    _digest(value["index_sha256"], "archive index_sha256")


def validate_return(payload, *, spec, commission_sha256):
    payload = _copy(payload)
    _exact(payload, "version handle return_id commission_sha256 returned_at outcome completion episode_archive result_archive form facts_archive pending_handles failure", "returned episode")
    if payload["version"] != "returned_episode_v1" or payload["handle"] != spec["handle"] or payload["commission_sha256"] != commission_sha256:
        raise ValueError("return differs from its commission")
    _timestamp(payload["returned_at"])
    if payload["outcome"] not in ("closed", "execution_failed", "interrupted"):
        raise ValueError("unknown return outcome")
    if payload["completion"] is not None:
        _exact(payload["completion"], "ended_by end_reason units_consumed", "completion")
        EpisodeCompletion(**payload["completion"])
    for name in ("episode_archive", "result_archive", "facts_archive"):
        _archive_descriptor(payload[name])
    if payload["outcome"] == "closed":
        if any(payload[name] is None for name in ("completion", "episode_archive", "result_archive")):
            raise ValueError("closed work requires its completion and archives")
    elif payload["completion"] is not None:
        raise ValueError("failed execution cannot invent an Episode completion")
    if payload["failure"] is not None:
        validate_failure(payload["failure"])
    elif payload["outcome"] != "closed":
        raise ValueError("failed execution requires a typed failure")
    if payload["form"] is not None:
        if payload["outcome"] != "closed":
            raise ValueError("failed execution cannot invent a scientific form")
        if not isinstance(payload["form"], dict):
            raise ValueError("form must be an object or null")
        if set(payload["form"]) != set(spec["child"]["request"]["report_contract"]["information"]):
            raise ValueError("form fields differ from the original reporting contract")
    elif payload["outcome"] == "closed" and payload["failure"] is None:
        raise ValueError("a missing closed form requires a typed delivery failure")
    _references(payload["pending_handles"], "pending_handles")
    expected = content_digest({key: value for key, value in payload.items() if key != "return_id"})
    if payload["return_id"] != expected:
        raise ValueError("return_id differs from its immutable envelope")
    return payload


def process_identity(pid=None):
    """Measure the process incarnation; distinguish absent from unreadable."""
    pid = os.getpid() if pid is None else pid
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        if fields[0] in ("Z", "X"):
            return None, "not_live"
        start_ticks = fields[19]
    except (FileNotFoundError, ProcessLookupError):
        return None, "not_live"
    except (OSError, IndexError, ValueError):
        return None, "unknown"
    try:
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return None, "unknown"
    if not boot:
        return None, "unknown"
    return {"pid": pid, "start_ticks": start_ticks, "boot_id": boot}, "live"


class DurableExecutionStore:
    def __init__(self, root_directory):
        self.root_directory = Path(root_directory).resolve()
        self.root_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.archive_directory = self.root_directory / "archives"
        self.archive_directory.mkdir(mode=0o700, exist_ok=True)
        self._database = self.root_directory / "executions.sqlite"
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS commissions (
                    handle TEXT PRIMARY KEY, operation_key TEXT NOT NULL,
                    parent_episode_id TEXT NOT NULL, commission_sha256 TEXT NOT NULL,
                    spec TEXT NOT NULL, execution_token TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL, execution_identity TEXT,
                    return_id TEXT, acknowledgment TEXT, failure TEXT,
                    UNIQUE(parent_episode_id, operation_key));
                CREATE TABLE IF NOT EXISTS returns (
                    handle TEXT PRIMARY KEY REFERENCES commissions(handle),
                    return_id TEXT NOT NULL UNIQUE, returned_at TEXT NOT NULL,
                    envelope TEXT NOT NULL, cursor INTEGER NOT NULL UNIQUE);
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
            if "failure" not in {row["name"] for row in db.execute("PRAGMA table_info(commissions)")}:
                db.execute("ALTER TABLE commissions ADD COLUMN failure TEXT")

    @contextmanager
    def _connect(self, *, write=False):
        # The storage lock wait is unrelated to a selected execution deadline.
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
            raise DurableExecutionError("storage_failure", affected_refs=[str(self._database)]) from error
        except BaseException:
            if db is not None:
                db.rollback()
            raise
        finally:
            if db is not None:
                db.close()

    @staticmethod
    def _row(db, handle):
        _text(handle, "handle")
        row = db.execute("SELECT * FROM commissions WHERE handle=?", (handle,)).fetchone()
        if row is None:
            raise KeyError(handle)
        return row

    @staticmethod
    def _event(db, handle, event, *, record_ref=None, operation_key=None):
        return db.execute("INSERT INTO events(handle,event,record_ref,operation_key,observed_at) VALUES(?,?,?,?,?)",
                          (handle, event, record_ref, operation_key, utc_now())).lastrowid

    def register_native_target(self, registration):
        registration = validate_native_registration(registration)
        handle, encoded = registration["handle"], canonical(registration)
        with self._connect(write=True) as db:
            if db.execute("SELECT 1 FROM commissions WHERE handle=?", (handle,)).fetchone():
                raise DurableExecutionError("identity_conflict", affected_refs=[handle])
            previous = db.execute("SELECT registration FROM native_targets WHERE handle=?", (handle,)).fetchone()
            if previous:
                if previous["registration"] != encoded:
                    raise DurableExecutionError("identity_conflict", affected_refs=[handle])
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
                    raise DurableExecutionError("identity_conflict", affected_refs=[handle, publication["record_ref"]])
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

    def commission(self, spec):
        spec = validate_commission(spec)
        digest = content_digest(spec)
        with self._connect(write=True) as db:
            if db.execute("SELECT 1 FROM native_targets WHERE handle=?", (spec["handle"],)).fetchone():
                raise DurableExecutionError("identity_conflict", affected_refs=[spec["handle"]])
            previous = db.execute("SELECT * FROM commissions WHERE handle=? OR (parent_episode_id=? AND operation_key=?)",
                (spec["handle"], spec["parent"]["episode_id"], spec["operation_key"])).fetchall()
            if previous:
                if len(previous) != 1 or previous[0]["handle"] != spec["handle"] or previous[0]["commission_sha256"] != digest:
                    raise DurableExecutionError("identity_conflict", affected_refs=[spec["handle"]])
                state = previous[0]["lifecycle_state"]
            else:
                state = "pending"
                db.execute("INSERT INTO commissions(handle,operation_key,parent_episode_id,commission_sha256,spec,execution_token,lifecycle_state) VALUES(?,?,?,?,?,?,?)",
                    (spec["handle"], spec["operation_key"], spec["parent"]["episode_id"], digest,
                     canonical(spec), secrets.token_hex(32), state))
                self._event(db, spec["handle"], "state_changed", record_ref=digest)
        return {"version": "commission_receipt_v1", "handle": spec["handle"],
                "commission_sha256": digest, "lifecycle_state": state}

    def load_commission(self, handle):
        """Return the immutable C1 assignment; no private execution token."""
        with self._connect() as db:
            return json.loads(self._row(db, handle)["spec"])

    def _claim(self, handle, token):
        identity, live = process_identity()
        if live != "live":
            raise DurableExecutionError("unavailable_resource", affected_refs=[handle])
        with self._connect(write=True) as db:
            row = self._row(db, handle)
            if not secrets.compare_digest(row["execution_token"], token):
                raise DurableExecutionError("identity_conflict", affected_refs=[handle])
            if row["execution_identity"] is not None or row["return_id"] is not None:
                return False
            db.execute("UPDATE commissions SET lifecycle_state='executing',execution_identity=?,failure=NULL WHERE handle=?",
                       (canonical(identity), handle))
            self._event(db, handle, "state_changed", record_ref=row["commission_sha256"])
        return True

    def start(self, handle):
        # Serialize normal callers. A parent can die at any instruction: the
        # independently running bootstrap, rather than this lock, owns claim.
        name = hashlib.sha256(_text(handle, "handle").encode()).hexdigest()
        with (self.root_directory / (name + ".start.lock")).open("ab") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            status = self.status(handle)
            if status["execution_identity"] is not None or status["return_available"]:
                return status
            with self._connect() as db:
                row = self._row(db, handle)
                token = row["execution_token"]
            read_fd, write_fd = os.pipe()
            environment = dict(os.environ)
            roots = [str(Path(__file__).resolve().parent.parent),
                     *(str(Path(entry or os.getcwd()).resolve()) for entry in sys.path)]
            environment["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(roots))
            try:
                with (self.root_directory / (name + ".worker.log")).open("ab") as log:
                    child = subprocess.Popen([sys.executable, "-P", "-m", "method_loop.durable_worker",
                        str(self.root_directory), handle, token, str(write_fd)],
                        stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                        start_new_session=True, close_fds=True, pass_fds=(write_fd,), env=environment)
            except OSError as error:
                os.close(read_fd)
                self._record_start_failure(handle, "unavailable_resource", name)
                return self.status(handle)
            finally:
                os.close(write_fd)
            try:
                # Only bootstrap identity readiness, never child completion.
                # EOF also permits inspection after a failed bootstrap.
                readiness = os.read(read_fd, 1)
            finally:
                os.close(read_fd)
            # Popen must never own the worker's lifetime or atexit cancellation.
            child.poll()
            if readiness != b"1":
                self._record_start_failure(handle, "storage_failure", name)
            return self.status(handle)

    def _record_start_failure(self, handle, code, log_name):
        """Persist failed bootstrap setup; selected work has not been claimed."""
        failure = {"code": code, "affected_refs": [handle],
            "diagnostic_ref": str(self.root_directory / (log_name + ".worker.log")),
            "partial_record_refs": []}
        with self._connect(write=True) as db:
            row = self._row(db, handle)
            if row["execution_identity"] is None and row["return_id"] is None:
                db.execute("UPDATE commissions SET failure=? WHERE handle=?", (canonical(failure), handle))
                self._event(db, handle, "state_changed", record_ref=row["commission_sha256"])

    def status(self, handle):
        with self._connect() as db:
            row = self._row(db, handle)
        identity = json.loads(row["execution_identity"]) if row["execution_identity"] else None
        liveness = "unknown"
        if identity is not None:
            observed, liveness = process_identity(identity["pid"])
            if liveness == "live" and observed != identity:
                liveness = "not_live"
        if identity is not None and liveness == "not_live" and row["return_id"] is None:
            # Lost execution is an outcome, never an invitation to rerun it.
            failure = {"code": "interrupted_execution", "affected_refs": [handle],
                       "diagnostic_ref": None, "partial_record_refs": []}
            payload = self._failure_envelope(row, failure, outcome="interrupted")
            try:
                self.publish_return(handle, row["execution_token"], payload)
            except DurableExecutionError as error:
                if error.failure["code"] != "identity_conflict":
                    raise
            with self._connect() as db:
                row = self._row(db, handle)
        failure = json.loads(row["failure"]) if row["failure"] else None
        acknowledgment = json.loads(row["acknowledgment"]) if row["acknowledgment"] else None
        return {"version": "execution_status_v1", "handle": handle,
            "commission_sha256": row["commission_sha256"], "lifecycle_state": row["lifecycle_state"],
            "observed_at": utc_now(), "execution_identity": identity, "liveness": liveness,
            "return_id": row["return_id"], "return_available": row["return_id"] is not None,
            "acknowledgment_id": acknowledgment["admission_id"] if acknowledgment else None,
            "failure": failure}

    @staticmethod
    def _failure_envelope(row, failure, *, outcome="execution_failed"):
        payload = {"version": "returned_episode_v1", "handle": row["handle"],
            "commission_sha256": row["commission_sha256"], "returned_at": utc_now(),
            "outcome": outcome, "completion": None, "episode_archive": None,
            "result_archive": None, "form": None, "facts_archive": None,
            "pending_handles": [], "failure": failure}
        payload["return_id"] = content_digest(payload)
        return payload

    def publish_return(self, handle, execution_token, payload):
        with self._connect(write=True) as db:
            row = self._row(db, handle)
            if (not isinstance(execution_token, str)
                    or not secrets.compare_digest(row["execution_token"], execution_token)
                    or row["execution_identity"] is None):
                raise DurableExecutionError("identity_conflict", affected_refs=[handle])
            try:
                payload = validate_return(payload, spec=json.loads(row["spec"]),
                                          commission_sha256=row["commission_sha256"])
            except (TypeError, ValueError) as error:
                raise DurableExecutionError("invalid_return", affected_refs=[handle]) from error
            old = db.execute("SELECT * FROM returns WHERE handle=?", (handle,)).fetchone()
            if old:
                if old["return_id"] != payload["return_id"] or old["envelope"] != canonical(payload):
                    raise DurableExecutionError("identity_conflict", affected_refs=[handle])
                cursor = old["cursor"]
            else:
                cursor = self._event(db, handle, "returned", record_ref=payload["return_id"])
                db.execute("INSERT INTO returns VALUES(?,?,?,?,?)", (handle, payload["return_id"],
                    payload["returned_at"], canonical(payload), cursor))
                db.execute("UPDATE commissions SET lifecycle_state='returned',return_id=?,failure=? WHERE handle=?",
                           (payload["return_id"], canonical(payload["failure"]) if payload["failure"] else None, handle))
                self._event(db, handle, "state_changed", record_ref=payload["return_id"])
        return {"version": "return_receipt_v1", "handle": handle, "return_id": payload["return_id"],
                "cursor": cursor, "returned_at": payload["returned_at"]}

    def return_page(self, parent_episode_id, after_cursor, limit):
        _text(parent_episode_id, "parent_episode_id")
        if type(after_cursor) is not int or after_cursor < 0 or type(limit) is not int or limit <= 0:
            raise ValueError("return pagination requires a nonnegative cursor and positive limit")
        with self._connect() as db:
            rows = db.execute("SELECT r.cursor,r.handle,r.return_id,r.returned_at FROM returns r JOIN commissions c USING(handle) WHERE c.parent_episode_id=? AND r.cursor>? ORDER BY r.cursor LIMIT ?",
                              (parent_episode_id, after_cursor, limit)).fetchall()
        items = [dict(row) for row in rows]
        return {"version": "return_page_v1", "after_cursor": after_cursor,
                "next_cursor": items[-1]["cursor"] if items else after_cursor, "items": items}

    def load_return(self, handle, return_id):
        with self._connect() as db:
            commission = self._row(db, handle)
            row = db.execute("SELECT envelope FROM returns WHERE handle=? AND return_id=?", (handle, return_id)).fetchone()
        if row is None:
            raise KeyError((handle, return_id))
        return validate_return(json.loads(row["envelope"]), spec=json.loads(commission["spec"]),
                               commission_sha256=commission["commission_sha256"])

    def acknowledge(self, handle, return_id, admission_id):
        _text(admission_id, "admission_id")
        with self._connect(write=True) as db:
            row = self._row(db, handle)
            if row["return_id"] != return_id or return_id is None:
                raise DurableExecutionError("identity_conflict", affected_refs=[handle])
            if row["acknowledgment"]:
                acknowledgment = json.loads(row["acknowledgment"])
                if acknowledgment["admission_id"] != admission_id:
                    raise DurableExecutionError("identity_conflict", affected_refs=[handle])
            else:
                acknowledgment = {"version": "acknowledgment_v1", "handle": handle,
                    "return_id": return_id, "admission_id": admission_id, "acknowledged_at": utc_now()}
                db.execute("UPDATE commissions SET lifecycle_state='admitted',acknowledgment=? WHERE handle=?",
                           (canonical(acknowledgment), handle))
                self._event(db, handle, "state_changed", record_ref=admission_id)
        return acknowledgment

    def record_progress(self, handle, record_ref, operation_key):
        """Notify one already committed exposed progress reference, idempotently.

        The application owns its content, scope and meaningful progress checks.
        Repeated notification does not create another event or a contribution.
        """
        _text(record_ref, "record_ref")
        _text(operation_key, "operation_key")
        with self._connect(write=True) as db:
            self._row(db, handle)
            old = db.execute("SELECT * FROM events WHERE handle=? AND event='progress_committed' AND operation_key=?",
                             (handle, operation_key)).fetchone()
            if old:
                if old["record_ref"] != record_ref:
                    raise DurableExecutionError("identity_conflict", affected_refs=[handle, record_ref])
                cursor = old["cursor"]
            else:
                cursor = self._event(db, handle, "progress_committed", record_ref=record_ref,
                                     operation_key=operation_key)
        return {"cursor": cursor, "handle": handle, "event": "progress_committed", "record_ref": record_ref}

    def _selected_target_kinds(self, condition):
        """Resolve durable identities before any episode-specific observation."""
        with self._connect() as db:
            kinds = {}
            for selected in condition["events"]:
                handle = selected["handle"]
                if handle not in kinds:
                    if db.execute("SELECT 1 FROM native_targets WHERE handle=?", (handle,)).fetchone():
                        kinds[handle] = "native"
                    else:
                        if not db.execute("SELECT 1 FROM commissions WHERE handle=?", (handle,)).fetchone():
                            raise EventTargetError("unknown_wait_target", affected_refs=[handle])
                        kinds[handle] = "commission"
                if kinds[handle] == "native" and selected["event"] != "state_changed":
                    raise EventTargetError("unsupported_wait_event", affected_refs=[handle],
                        detail="native targets support only state_changed")
        return kinds

    def validate_event_targets(self, condition):
        """Check identities/event kinds in an already shape-validated choice.

        This reads registrations only: no status observation, event publication,
        deadline fallback, work dispatch or application ownership decision.
        """
        condition = _copy(condition)
        self._selected_target_kinds(condition)
        return condition

    def _matching_events(self, condition):
        # A selected observation can recover an actually exited incarnation.
        # This does no work or scheduling; dead executions never restart here.
        for handle, kind in self._selected_target_kinds(condition).items():
            if kind == "commission":
                self.status(handle)
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
        if condition["version"] != "event_condition_v1" or not isinstance(condition["events"], list):
            raise ValueError("unsupported event condition")
        for item in condition["events"]:
            _exact(item, "handle event after_cursor", "selected event")
            _text(item["handle"], "event handle")
            if (not isinstance(item["event"], str) or item["event"] not in _EVENTS
                    or type(item["after_cursor"]) is not int or item["after_cursor"] < 0):
                raise ValueError("invalid selected event")
        deadline = _timestamp(condition["reconsider_at"]) if condition["reconsider_at"] is not None else None
        if not condition["events"] and deadline is None:
            raise ValueError("wait requires selected events or reconsideration time")
        # Subscribe BEFORE inspecting the persistent ledger. A commit anywhere
        # in the inspection/subscription boundary therefore remains observable.
        with _DirectoryNotification(self.root_directory) as notification:
            while True:
                events = self._matching_events(condition)
                if events:
                    return {"version": "event_wake_v1", "reason": events[0]["event"],
                        "observed_at": utc_now(), "events": events,
                        "reconsider_at": condition["reconsider_at"]}
                if deadline is not None and datetime.now(timezone.utc) >= deadline:
                    return {"version": "event_wake_v1", "reason": "reconsideration",
                        "observed_at": utc_now(), "events": [], "reconsider_at": condition["reconsider_at"]}
                identities = []
                kinds = self._selected_target_kinds(condition)
                for handle in dict.fromkeys(item["handle"] for item in condition["events"]
                        if item["event"] in ("returned", "state_changed")
                        and kinds[item["handle"]] == "commission"):
                    observed = self.status(handle)
                    if observed["liveness"] == "live":
                        identities.append(observed["execution_identity"])
                    elif observed["return_available"]:
                        # State may have changed after the preceding ledger
                        # read. Recheck once before subscribing or yielding.
                        if self._matching_events(condition):
                            break
                else:
                    await notification.wait(deadline, identities)


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

    async def wait(self, deadline, identities):
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
        process_fds = []
        timer = None
        try:
            for identity in identities:
                try:
                    descriptor = os.pidfd_open(identity["pid"])
                except ProcessLookupError:
                    # The process exited in the observation/subscription gap.
                    return
                process_fds.append(descriptor)
                observed, live = process_identity(identity["pid"])
                if live == "not_live" or (live == "live" and observed != identity):
                    return
                loop.add_reader(descriptor, lambda: None if future.done() else future.set_result(None))
            if deadline is not None:
                delay = max(0, (deadline - datetime.now(timezone.utc)).total_seconds())
                timer = loop.call_later(delay, lambda: None if future.done() else future.set_result(None))
            await future
        finally:
            loop.remove_reader(self.fd)
            for descriptor in process_fds:
                loop.remove_reader(descriptor)
                os.close(descriptor)
            if timer is not None:
                timer.cancel()
