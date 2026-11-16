"""Exposed progress and recursive monitoring in the ordinary Episode loop.

Progress is a typed runtime observation, not a scientific finding. Owners expose
committed references and direct relationships explicitly. Observing a target
never inspects its model calls, instructions, trace or yield history, and never
walks its descendants. The binding supplies choices to the shared source and,
when configured, binds this monitor's information-yield rule.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.a107.method_loop.durable import FAILURE_CODES, canonical, content_digest

from .communication import plain, validate_form
from .domain import ContractError, REF, RECORD_SCHEMAS, identity, obj, validate_schema
from .episode_bindings import native_observation_options, reference_in_context
from .progress_records import RESOURCE_STATUS_SCHEMA, validate_resource_status


VERSION = "monitor_episode_binding_v1"
PROGRESS_VERSION = "progress_snapshot_v1"
FIELDS = ("execution_status", "measurements", "log_windows", "committed_record_refs",
          "dependencies", "result_available")
_STATES = ("pending", "executing", "returned", "admitted")
_REFS = {"type": "array", "items": REF, "uniqueItems": True}
_FIELDS = {"type": "array", "items": {"enum": list(FIELDS)}, "uniqueItems": True}
_TEXT = {"type": "string", "minLength": 1}
_RUNTIME_REFS = {"type": "array", "items": _TEXT, "uniqueItems": True}
_FAILURE = obj({"code": {"enum": sorted(FAILURE_CODES)}, "affected_refs": _RUNTIME_REFS,
    "diagnostic_ref": {"type": ["string", "null"]}, "partial_record_refs": _RUNTIME_REFS})
_SUSPENSION = {'oneOf': [{'type': 'null'},
    obj({'episode_id': _TEXT, 'dependency': {'type': 'object', 'required': ['kind'],
        'properties': {'kind': {'enum': ['scheduled_external_job', 'selected_external_event',
            'owned_child_return']}}}}),
    obj({'kind': {'const': 'receiver_reconstruction'}, 'pending_handles': _RUNTIME_REFS,
        'checkpoint': _TEXT, 'failure': _FAILURE})]}
_EPISODE_STATUS = obj({"version": {"const": "execution_status_v2"}, "handle": _TEXT,
    "commission_sha256": _TEXT, "lifecycle_state": {"enum": list(_STATES)},
    "observed_at": _TEXT, "execution_identity": {**obj({"pid": {"type": "integer", "minimum": 1},
        "start_ticks": _TEXT, "boot_id": _TEXT}), "type": ["object", "null"]},
    "liveness": {"enum": ["live", "not_live", "unknown"]},
    "return_id": {"type": ["string", "null"]}, "return_available": {"type": "boolean"},
    "acknowledgment_id": {"type": ["string", "null"]},
    "failure": {**_FAILURE, "type": ["object", "null"]}, "suspension": _SUSPENSION})
_STATUS = {"oneOf": [_EPISODE_STATUS, deepcopy(RESOURCE_STATUS_SCHEMA)]}
_DEPENDENCY = obj({"handle": _TEXT, "kind": {"enum": ["episode", "job"]},
    "relation_ref": _TEXT, "observed_at": _TEXT, "state": {"enum": list(_STATES)}})
_MEASUREMENT = obj({"name": _TEXT, "value": {"type": ["number", "null"]},
    "unit": _TEXT, "measured_at": _TEXT, "provenance_ref": _TEXT})
_LOG = obj({"source_ref": REF, "artifact_ref": REF,
    "start_byte": {"type": "integer", "minimum": 0},
    "end_byte": {"type": "integer", "minimum": 0}, "observed_at": _TEXT,
    "content_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}})
_SNAPSHOT = obj({"version": {"const": PROGRESS_VERSION}, "progress_ref": _TEXT,
    "target_handle": _TEXT, "observed_at": _TEXT, "provenance_refs": _RUNTIME_REFS,
    "execution_status": _STATUS, "measurements": {"type": "array", "items": _MEASUREMENT},
    "log_windows": {"type": "array", "items": _LOG}, "committed_record_refs": _REFS,
    "dependencies": {"type": "array", "items": _DEPENDENCY},
    "result_available": {"type": "boolean"}})
_ASSIGNMENT = obj({"version": {"const": "monitor_assignment_v1"}, "target_handle": _TEXT,
    "requested_fields": _FIELDS, "known_progress_refs": _REFS,
    "permitted_committed_record_types": {"type": "array", "uniqueItems": True,
        "items": {"enum": sorted(RECORD_SCHEMAS)}}})


def _now():
    return datetime.now(timezone.utc).isoformat()


def _timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
            raise ValueError
    except (ValueError, AttributeError) as error:
        raise ContractError("progress_utc_timestamp_required") from error
    return result


def _unique(values):
    return list(dict.fromkeys(values))


def _same_observation(value):
    """New read timestamps alone do not create a new observed contribution."""
    result = deepcopy(value)
    result.pop("progress_ref", None)
    result.pop("observed_at", None)
    result["execution_status"].pop("observed_at", None)
    for field, stamp in (("dependencies", "observed_at"), ("log_windows", "observed_at"),
                         ("measurements", "measured_at")):
        for row in result.get(field, ()):
            row.pop(stamp, None)
    return result


def read_progress(store, run_id, reference, scope=None):
    """Read a saved C8 observation without constructing a writing provider."""
    installed = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='runtime_progress_observations'").fetchone()
    row = (store.db.execute("SELECT scope,snapshot FROM runtime_progress_observations "
        "WHERE run_id=? AND progress_ref=?", (run_id, reference)).fetchone()
        if installed else None)
    if row is None:
        raise ContractError("progress_reference_unavailable")
    if scope is not None and not store.scope_contains(plain(scope), json.loads(row["scope"])):
        raise ContractError("progress_reference_outside_scope")
    return json.loads(row["snapshot"])


class ProgressProvider:
    """C8 provider over an actual Store and the public C2 execution interface.

    Optional ``job_provider`` supplies ``scope(handle)``, ``observe(handle,
    requested_fields, scope, *, operation_key=None) -> ProgressSnapshotV1`` and
    ``direct_dependencies(handle, scope)``. Its observations must carry actual
    status/measurement/log provenance; this class neither invents availability
    nor invokes a job. A missing durable handle is delegated only to this bound
    provider. Explicit exposure and observations share the scientific Store's
    transaction, in separate runtime tables. Durable episode exposure also
    retains an outbox intent; ``flush_notifications`` publishes it after commit.
    A target's explicit selected_observation_schema can additionally require a
    native_operation. Only that selection forwards the original BindingContext
    through observation_context; old providers receive neither new keyword.
    """

    def __init__(self, store, durable_store, *, run_id, job_provider=None):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("progress_run_identity_required")
        self.store, self.durable_store = store, durable_store
        self.run_id, self.job_provider = run_id, job_provider
        with store.transaction():
            store.db.execute("""CREATE TABLE IF NOT EXISTS runtime_progress_exposures (
                run_id TEXT NOT NULL, target_handle TEXT NOT NULL, operation_key TEXT NOT NULL,
                signature TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(run_id,target_handle,operation_key))""")
            store.db.execute("""CREATE TABLE IF NOT EXISTS runtime_progress_notifications (
                run_id TEXT NOT NULL, target_handle TEXT NOT NULL, operation_key TEXT NOT NULL,
                publication_ref TEXT NOT NULL, published INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(run_id,target_handle,operation_key), UNIQUE(run_id,publication_ref))""")
            store.db.execute("""CREATE TABLE IF NOT EXISTS runtime_progress_observations (
                run_id TEXT NOT NULL, progress_ref TEXT NOT NULL, target_handle TEXT NOT NULL,
                scope TEXT NOT NULL, signature TEXT NOT NULL, snapshot TEXT NOT NULL,
                observation_identity TEXT NOT NULL,
                PRIMARY KEY(run_id,progress_ref), UNIQUE(run_id,target_handle,scope,signature))""")
            store.db.execute("""CREATE TABLE IF NOT EXISTS runtime_progress_selections (
                run_id TEXT NOT NULL, operation_key TEXT NOT NULL, signature TEXT NOT NULL,
                selection TEXT NOT NULL, progress_ref TEXT NOT NULL,
                PRIMARY KEY(run_id,operation_key))""")
            store.db.execute("""CREATE TABLE IF NOT EXISTS runtime_progress_receipts (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, progress_ref TEXT NOT NULL,
                operation_key TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,progress_ref))""")
            store.db.execute("""CREATE TABLE IF NOT EXISTS runtime_progress_deliveries (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL, operation_key TEXT NOT NULL,
                signature TEXT NOT NULL, progress_refs TEXT NOT NULL,
                PRIMARY KEY(run_id,episode_id,operation_key))""")

    def _target(self, handle, scope=None):
        if not isinstance(handle, str) or not handle:
            raise ContractError("progress_target_handle_required")
        try:
            spec = self.durable_store.load_commission(handle)
        except KeyError:
            if self.job_provider is None:
                raise ContractError("progress_target_unavailable") from None
            try:
                target_scope = self.store.validate_scope(self.job_provider.scope(handle))
            except KeyError:
                raise ContractError("progress_target_unavailable") from None
            spec = None
        else:
            if spec["run_id"] != self.run_id:
                raise ContractError("progress_target_outside_run")
            target_scope = self.store.validate_scope(spec["child"]["scope"])
        if scope is not None and not self.store.scope_contains(plain(scope), target_scope):
            raise ContractError("progress_target_outside_scope")
        return spec, target_scope

    def _record(self, reference, scope, kind=None):
        if not self.store.reference_subset([reference], scope):
            raise ContractError("progress_reference_outside_scope")
        value = self.store.get(reference)
        if kind is not None and value["record_type"] != kind:
            raise ContractError("progress_reference_type_mismatch")
        return value

    def describe_target(self, handle, scope):
        """Original commission/target metadata only; do not observe live work."""
        spec, target_scope = self._target(handle, scope)
        if spec is not None:
            return {'resource_kind': 'episode', 'service_or_program': spec['child']['role'],
                    'operation': None, 'output_format': 'typed_episode_return'}
        callback = getattr(self.job_provider, 'describe_target', None)
        return callback(handle, target_scope) if callback is not None else None

    def _validate_dependency(self, target, dependency, scope):
        validate_schema(dependency, _DEPENDENCY)
        _timestamp(dependency["observed_at"])
        spec, _ = self._target(dependency["handle"], scope)
        parent, _ = self._target(target, scope)
        if dependency["kind"] == "episode":
            if (spec is None or parent is None
                    or spec["parent"]["episode_id"] != parent["child"]["episode_id"]
                    or dependency["relation_ref"] != content_digest(spec)):
                raise ContractError("progress_dependency_relationship_mismatch")
        elif spec is not None:
            raise ContractError("progress_dependency_kind_mismatch")
        else:
            # Job relationships are published by the owning execution binding,
            # with a real committed relation reference, not inferred ancestry.
            self._record(dependency["relation_ref"], scope)

    def _validate_exposed(self, target, fields, scope):
        for reference in fields["committed_record_refs"]:
            self._record(reference, scope)
        for dependency in fields["dependencies"]:
            self._validate_dependency(target, dependency, scope)
        for measurement in fields["measurements"]:
            validate_schema(measurement, _MEASUREMENT)
            _timestamp(measurement["measured_at"])
            if not self.resolve(measurement["provenance_ref"], scope, None):
                raise ContractError("progress_measurement_provenance_unavailable")
        for window in fields["log_windows"]:
            validate_schema(window, _LOG)
            _timestamp(window["observed_at"])
            source = self._record(window["source_ref"], scope, "source")
            self._record(window["artifact_ref"], scope, "artifact")
            if window["artifact_ref"] not in {source.get(key) for key in
                    ("artifact_ref", "text_ref", "stdout_ref", "stderr_ref")}:
                raise ContractError("progress_log_source_artifact_mismatch")
            data = self.store.get_artifact(window["artifact_ref"])
            start, end = window["start_byte"], window["end_byte"]
            if not 0 <= start <= end <= len(data):
                raise ContractError("progress_log_window_out_of_bounds")
            if hashlib.sha256(data[start:end]).hexdigest() != window["content_sha256"]:
                raise ContractError("progress_log_window_digest_mismatch")
        spec, _ = self._target(target, scope)
        own_provenance = {content_digest(spec)} if spec is not None else set()
        for reference in fields["provenance_refs"]:
            if reference not in own_provenance and not self.resolve(reference, scope, None):
                raise ContractError("progress_provenance_unavailable")

    def expose(self, target_handle, *, operation_key, committed_record_refs=(),
               dependencies=(), measurements=(), log_windows=(), provenance_refs=()):
        """Publish actual committed exposed information, retaining operation identity.

        Episode relationships are checked against C1. A caller publishing job
        relationships owns their actual relation record. This records no model
        intention and discovers no dependency by reading private execution state.
        The returned ``publication_ref`` identifies this saved exposure under
        ``progress_provenance``; it is not a delivered C8 snapshot reference.
        """
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("progress_operation_key_required")
        spec, scope = self._target(target_handle)
        payload = {"version": "progress_exposure_v1", "target_handle": target_handle,
            "committed_record_refs": _unique(committed_record_refs),
            "dependencies": plain(dependencies), "measurements": plain(measurements),
            "log_windows": plain(log_windows), "provenance_refs": _unique(provenance_refs)}
        signature = content_digest(payload)
        publication_ref = "progress_publication_" + content_digest({"run_id": self.run_id,
            "target_handle": target_handle, "operation_key": operation_key, "signature": signature})
        with self.store.transaction():
            row = self.store.db.execute("SELECT signature,payload FROM runtime_progress_exposures "
                "WHERE run_id=? AND target_handle=? AND operation_key=?",
                (self.run_id, target_handle, operation_key)).fetchone()
            if row:
                if row["signature"] != signature:
                    raise ContractError("progress_operation_identity_conflict")
                payload = json.loads(row["payload"])
                # Replayed pre-outbox exposures acquire the same deterministic
                # identity without changing their original observation time.
                if "publication_ref" not in payload:
                    payload["publication_ref"] = publication_ref
                    self.store.db.execute("UPDATE runtime_progress_exposures SET payload=? "
                        "WHERE run_id=? AND target_handle=? AND operation_key=?",
                        (canonical(payload), self.run_id, target_handle, operation_key))
            else:
                self._validate_exposed(target_handle, payload, scope)
                payload.update(observed_at=_now(), publication_ref=publication_ref)
                self.store.db.execute("INSERT INTO runtime_progress_exposures VALUES(?,?,?,?,?)",
                    (self.run_id, target_handle, operation_key, signature, canonical(payload)))
            # C2 events address durable episode commissions only. The bound
            # job provider has no event publication port; its saved exposures
            # remain observable without asserting a delivered notification.
            if spec is not None:
                self.store.db.execute("INSERT OR IGNORE INTO runtime_progress_notifications "
                    "(run_id,target_handle,operation_key,publication_ref) VALUES(?,?,?,?)",
                    (self.run_id, target_handle, operation_key, publication_ref))
        return payload

    def flush_notifications(self):
        """Notify committed durable-episode exposures through the public C2 port.

        This explicit transport operation supplies no observation or polling
        policy. A failed publication or interruption before acknowledgment
        retains the intent; replay uses the original operation key and ref.
        """
        if self.store.db.in_transaction:
            raise ContractError("progress_notifications_require_committed_transaction")
        rows = self.store.db.execute("SELECT target_handle,operation_key,publication_ref "
            "FROM runtime_progress_notifications WHERE run_id=? AND published=0 ORDER BY rowid",
            (self.run_id,)).fetchall()
        published = 0
        for row in rows:
            # Never place the cross-store event before the authoritative Store
            # commit, including when expose joined a caller-owned transaction.
            self.durable_store.record_progress(row["target_handle"], row["publication_ref"], row["operation_key"])
            with self.store.transaction():
                updated = self.store.db.execute("UPDATE runtime_progress_notifications SET published=1 "
                    "WHERE run_id=? AND target_handle=? AND operation_key=? AND published=0",
                    (self.run_id, row["target_handle"], row["operation_key"]))
                published += updated.rowcount
        pending = self.store.db.execute("SELECT count(*) FROM runtime_progress_notifications "
            "WHERE run_id=? AND published=0", (self.run_id,)).fetchone()[0]
        return {"published": published, "pending": pending}

    def _exposures(self, target):
        rows = self.store.db.execute("SELECT payload FROM runtime_progress_exposures "
            "WHERE run_id=? AND target_handle=? ORDER BY rowid", (self.run_id, target))
        return [json.loads(row[0]) for row in rows]

    def direct_dependencies(self, target_handle, scope):
        spec, target_scope = self._target(target_handle, scope)
        values = [dependency for row in self._exposures(target_handle) for dependency in row["dependencies"]]
        if spec is None:
            values.extend(plain(self.job_provider.direct_dependencies(target_handle, target_scope)))
        by_handle = {}
        for dependency in values:
            self._validate_dependency(target_handle, dependency, target_scope)
            previous = by_handle.get(dependency["handle"])
            if previous is None or {key: item for key, item in previous.items() if key != "observed_at"} != {
                    key: item for key, item in dependency.items() if key != "observed_at"}:
                by_handle[dependency["handle"]] = dependency
        return list(by_handle.values())

    def _selected_observation(self, operation_key, signature, scope):
        if operation_key is None:
            return None
        row = self.store.db.execute("SELECT signature,progress_ref FROM runtime_progress_selections "
            "WHERE run_id=? AND operation_key=?", (self.run_id, operation_key)).fetchone()
        if row is None:
            return None
        if row["signature"] != signature:
            raise ContractError("progress_operation_identity_conflict")
        return self.read_progress(row["progress_ref"], scope)

    def observe(self, target_handle, requested_fields, scope, *,
                permitted_committed_record_types=(), operation_key=None,
                native_operation=None, observation_context=None):
        requested_fields = plain(requested_fields)
        permitted_committed_record_types = plain(permitted_committed_record_types)
        validate_schema(permitted_committed_record_types, _ASSIGNMENT["properties"]["permitted_committed_record_types"])
        validate_schema(requested_fields, _FIELDS)
        if operation_key is not None and (not isinstance(operation_key, str) or not operation_key):
            raise ContractError("progress_operation_key_required")
        selection = {"target_handle": target_handle, "requested_fields": requested_fields,
            "scope": plain(scope), "permitted_committed_record_types": permitted_committed_record_types}
        native_options = native_observation_options(native_operation, observation_context)
        if native_options:
            selection.update(native_operation=native_operation,
                observation_context=observation_context.as_record())
        selection_signature = content_digest(selection)
        # A selected observation is an immutable action outcome. Recovery must
        # restore it before consulting the current commission, status or files.
        replay = self._selected_observation(operation_key, selection_signature, scope)
        if replay is not None:
            return replay
        spec, target_scope = self._target(target_handle, scope)
        if native_options:
            descriptor = self.describe_target(target_handle, target_scope)
            selected_schema = (descriptor or {}).get('selected_observation_schema')
            if spec is not None or selected_schema is None:
                raise ContractError('progress_native_operation_not_supported')
            validate_schema({'native_operation': native_operation}, selected_schema)
        captured = _now()
        if spec is not None:
            status = self.durable_store.status(target_handle)
            validate_schema(status, _EPISODE_STATUS)
            if (status["return_available"] != (status["return_id"] is not None)
                    or status["return_available"] != (status["lifecycle_state"] in {"returned", "admitted"})
                    or (status["acknowledgment_id"] is not None) != (status["lifecycle_state"] == "admitted")):
                raise ContractError("progress_status_relationship_mismatch")
            result_available = status["return_available"]
            base = {"provenance_refs": [content_digest(spec)], "measurements": [],
                    "log_windows": [], "committed_record_refs": []}
        else:
            # Let the adapter retain its valid capture before opening the C8
            # publication transaction below. Validation/publication failure
            # here must not discard an already-committed native observation.
            raw = plain(self.job_provider.observe(target_handle, requested_fields, target_scope,
                operation_key=operation_key, **native_options))
            validate_schema(raw, _SNAPSHOT)
            if raw["target_handle"] != target_handle:
                raise ContractError("progress_job_target_mismatch")
            captured = raw["observed_at"]
            status = validate_resource_status(raw["execution_status"])
            result_available = raw["result_available"]
            if result_available != status["result_available"]:
                raise ContractError("progress_job_result_relationship_mismatch")
            base = {field: raw[field] for field in
                    ("provenance_refs", "measurements", "log_windows", "committed_record_refs")}
        if status["handle"] != target_handle:
            raise ContractError("progress_status_target_mismatch")
        _timestamp(captured)
        _timestamp(status["observed_at"])
        for exposed in self._exposures(target_handle):
            for field in base:
                base[field].extend(exposed[field])
        base["provenance_refs"] = _unique(base["provenance_refs"])
        base["committed_record_refs"] = _unique(base["committed_record_refs"])
        for field, stamp in (("measurements", "measured_at"), ("log_windows", "observed_at")):
            original_rows = {}
            for row in base[field]:
                key = canonical({name: item for name, item in row.items() if name != stamp})
                original_rows.setdefault(key, row)
            base[field] = list(original_rows.values())
        all_dependencies = self.direct_dependencies(target_handle, target_scope)
        original = {"target_handle": target_handle, "execution_status": status,
            **base, "dependencies": all_dependencies, "result_available": result_available}
        observation_identity = "progress_observation_" + content_digest(_same_observation(original))
        base["provenance_refs"].append(observation_identity)
        base["committed_record_refs"] = [ref for ref in base["committed_record_refs"]
            if self.store.get(ref)["record_type"] in permitted_committed_record_types]
        dependencies = all_dependencies if "dependencies" in requested_fields else []
        value = {"version": PROGRESS_VERSION, "target_handle": target_handle,
            "observed_at": captured, "execution_status": status,
            **{field: rows if field == "provenance_refs" or field in requested_fields else []
               for field, rows in base.items()}, "dependencies": dependencies,
            "result_available": result_available}
        # This identity names the observation without exposing a broader
        # unrequested projection. It is validated by construction, then stored.
        checked = {**value, "provenance_refs": [ref for ref in value["provenance_refs"] if ref != observation_identity]}
        self._validate_exposed(target_handle, checked, target_scope)
        signature = content_digest(_same_observation(value))
        serialized_scope = canonical(target_scope)
        with self.store.transaction():
            replay = self._selected_observation(operation_key, selection_signature, scope)
            if replay is not None:
                return replay
            old = self.store.db.execute("SELECT snapshot FROM runtime_progress_observations "
                "WHERE run_id=? AND target_handle=? AND scope=? AND signature=?",
                (self.run_id, target_handle, serialized_scope, signature)).fetchone()
            if old:
                value = json.loads(old[0])
            else:
                value["progress_ref"] = "progress_" + content_digest({"run_id": self.run_id,
                    "target_handle": target_handle, "scope": target_scope, "signature": signature})
                validate_schema(value, _SNAPSHOT)
                self.store.db.execute("INSERT INTO runtime_progress_observations VALUES(?,?,?,?,?,?,?)",
                    (self.run_id, value["progress_ref"], target_handle, serialized_scope, signature, canonical(value), observation_identity))
            if operation_key is not None:
                self.store.db.execute("INSERT INTO runtime_progress_selections VALUES(?,?,?,?,?)",
                    (self.run_id, operation_key, selection_signature, canonical(selection), value["progress_ref"]))
        return value

    def read_progress(self, reference, scope=None):
        return read_progress(self.store, self.run_id, reference, scope)

    def observation_identity(self, reference, scope=None):
        self.read_progress(reference, scope)
        return self.store.db.execute("SELECT observation_identity FROM runtime_progress_observations "
            "WHERE run_id=? AND progress_ref=?", (self.run_id, reference)).fetchone()[0]

    def resolve(self, reference, scope, namespace=None):
        if namespace in (None, "progress_provenance"):
            rows = self.store.db.execute("SELECT target_handle FROM runtime_progress_exposures "
                "WHERE run_id=? AND json_extract(payload,'$.publication_ref')=?",
                (self.run_id, reference))
            for row in rows:
                try:
                    self._target(row[0], scope)
                except ContractError:
                    continue
                return True
        if namespace in (None, "progress_observation", "progress_provenance"):
            rows = self.store.db.execute("SELECT progress_ref FROM runtime_progress_observations "
                "WHERE run_id=? AND observation_identity=?", (self.run_id, reference))
            for row in rows:
                try:
                    self.read_progress(row[0], scope)
                except ContractError:
                    continue
                return True
        if namespace in (None, "episode_progress", "progress", "progress_snapshot"):
            try:
                self.read_progress(reference, scope)
            except ContractError:
                pass
            else:
                return True
        if namespace in (None, "execution_handle", "execution", "progress_provenance"):
            try:
                spec, _ = self._target(reference, scope)
            except ContractError:
                pass
            else:
                return True
            # Commission digests are actual public provenance, not process IDs.
            if namespace in (None, "progress_provenance"):
                rows = self.store.db.execute("SELECT DISTINCT target_handle FROM runtime_progress_exposures "
                    "WHERE run_id=? UNION SELECT DISTINCT target_handle FROM runtime_progress_observations WHERE run_id=?",
                    (self.run_id, self.run_id))
                for row in rows:
                    try:
                        spec, _ = self._target(row[0], scope)
                    except ContractError:
                        continue
                    if spec is not None and content_digest(spec) == reference:
                        return True
        if namespace in (None, "progress_provenance"):
            return bool(self.store.reference_subset([reference], plain(scope)))
        return False

    def _progress_delivery_replay(self, episode_id, signature, operation_key):
        old = self.store.db.execute("SELECT signature,progress_refs FROM runtime_progress_deliveries "
            "WHERE run_id=? AND episode_id=? AND operation_key=?",
            (self.run_id, episode_id, operation_key)).fetchone()
        if old is None:
            return None
        if old["signature"] != signature:
            raise ContractError("progress_delivery_identity_conflict")
        return json.loads(old["progress_refs"])

    def _receive_progress(self, episode_id, references, signature, operation_key):
        """Publish either delivery channel in the same first-receipt index."""
        with self.store.transaction():
            replay = self._progress_delivery_replay(episode_id, signature, operation_key)
            if replay is not None:
                return replay
            self.store.db.execute("INSERT INTO runtime_progress_deliveries VALUES(?,?,?,?,?)",
                (self.run_id, episode_id, operation_key, signature, canonical(references)))
            for reference in references:
                self.store.db.execute("INSERT OR IGNORE INTO runtime_progress_receipts VALUES(?,?,?,?)",
                    (self.run_id, episode_id, reference, operation_key))
        return references

    def receive_outcome(self, episode_id, outcome, scope, operation_key):
        """Receive explicit saved C8 refs from an executed own action.

        The owner records the actual outcome first and calls this within its
        receipt/credit/completion transaction. The complete finite outcome and
        scope bind the operation, including fields unrelated to progress. This
        reads saved observations only; it never refreshes a target's state.
        """
        if not isinstance(episode_id, str) or not episode_id or not isinstance(operation_key, str) or not operation_key:
            raise ContractError("progress_delivery_identity_required")
        if not isinstance(outcome, Mapping):
            raise ContractError("progress_completed_outcome_required")
        outcome, scope = plain(outcome), plain(scope)
        # Canonicalization rejects nonfinite values, non-string keys and values
        # outside JSON anywhere in the outcome or supplied scope.
        signature = content_digest({"channel": "own_outcome", "outcome": outcome, "scope": scope})
        with self.store.transaction():
            replay = self._progress_delivery_replay(episode_id, signature, operation_key)
            if replay is not None:
                return replay
            # A dispatched action can return invalid arguments or references.
            # Its original iterator still observes that executed attempt; only
            # explicitly saved, authenticated progress refs can contribute here.
            if outcome.get("status") not in ("completed", "partial", "invalid", "failed", "unavailable"):
                raise ContractError("progress_completed_outcome_required")
            references = outcome.get("progress_refs", [])
            if not isinstance(references, list) or any(not isinstance(ref, str) or not ref for ref in references):
                raise ContractError("progress_outcome_references_required")
            validated_scope = self.store.validate_scope(scope)
            references = _unique(references)
            for reference in references:
                self.read_progress(reference, validated_scope)
            return self._receive_progress(episode_id, references, signature, operation_key)

    def receive_form(self, episode_id, form, schema, scope, operation_key):
        """Receive only progress references explicitly requested by this form.

        The composition owner first admits the original typed form and calls
        this inside its admission transaction. Repetition retains the original
        delivery and does not manufacture observations or scientific receipts.
        """
        if not isinstance(episode_id, str) or not episode_id or not isinstance(operation_key, str) or not operation_key:
            raise ContractError("progress_delivery_identity_required")
        references = []
        def declared_reference(reference, namespace):
            if namespace == "episode_progress":
                self.read_progress(reference, scope)
                references.append(reference)
            # Scientific references were checked at the original typed
            # admission. This collector confers only declared C8 progress.
            return True
        validate_form(form, schema, declared_reference)
        references = _unique(references)
        # Preserve the original form signature for markerless saved deliveries.
        signature = content_digest({"form": plain(form), "schema": plain(schema), "scope": plain(scope)})
        return self._receive_progress(episode_id, references, signature, operation_key)

    def received_progress_refs(self, episode_id, scope=None):
        """Return first receipts across own outcomes and typed forms in order."""
        rows = self.store.db.execute("SELECT progress_ref FROM runtime_progress_receipts "
            "WHERE run_id=? AND episode_id=? ORDER BY rowid", (self.run_id, episode_id))
        references = [row[0] for row in rows]
        if scope is not None:
            for reference in references:
                self.read_progress(reference, scope)
        return references

    def validate_monitor_child(self, assignment, selected_target_handle, scope):
        validate_schema(plain(assignment), _ASSIGNMENT)
        if selected_target_handle not in {row["handle"] for row in
                self.direct_dependencies(assignment["target_handle"], scope)}:
            raise ContractError("monitor_child_target_not_exposed_direct_dependency")


def _monitor_information_yield(scores, parameters, contexts):
    """Estimate another newly informative snapshot from this monitor's actions."""
    from .numerical import estimate_nonnegative_yield
    if any(score < 0 for score in scores):
        raise ValueError('monitor_information_credit_cannot_decrease')
    result = estimate_nonnegative_yield(scores, parameters, contexts=contexts)
    return replace(result, estimator_binding={
        'kind': 'monitor_information_accumulation_v1',
        'credit': 'newly_informative_received_snapshot_count_times_information_unit',
        'forecast': 'next_monitor_action_information_credit',
        'decision': 'predicted_upper_gain_at_or_below_monitor_cutoff'})


__all__ = ["ProgressProvider", "read_progress", "PROGRESS_VERSION", "FIELDS"]


