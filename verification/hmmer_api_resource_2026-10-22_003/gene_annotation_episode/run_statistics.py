"""Shared execution statistics, never scientific credit or child yield history.

Infrastructure records measured job phases. Callers report resource conditions.
Children receive immutable, typed expectation snapshots through a read interface.
No episode tree, scientific Store, controller, model or result text is accessible
here. The caller supplies the one history path shared across run workspaces.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3


VERSION = "execution_statistics_v1"
REPORTED_RESULT_VERSION = "reported_result_statistics_v1"
REPORTED_RESULT_PHASE = "remote_protein_homology_search"
REPORTED_RESULT_MEASURE = "hmmer_reported_search_elapsed_seconds"
REPORTED_RESULT_UNIT = "logical_provider_job_reported_result"
CONDITIONS = {"unspecified", "normal", "degraded", "unavailable"}
EXECUTION_PHASE_BACKENDS = {'reference_acquisition': 'https', 'protein_homology_search': 'local',
    'pairwise_sequence_alignment': 'local', 'spreadsheet_selection': 'local',
    REPORTED_RESULT_PHASE: 'https'}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _ref(prefix, value):
    return prefix + "_" + hashlib.sha256(_json(value).encode()).hexdigest()


def _hash(value):
    if type(value) is not str or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValueError("execution_statistic_digest_required")


def _resource(value):
    # A configured resource identity, not a message or a scientific identifier.
    if type(value) is not str or re.fullmatch("[a-z0-9][a-z0-9._:-]{0,191}", value) is None:
        raise ValueError("execution_resource_identity_required")


def _timestamp(value):
    if type(value) is not str:
        raise ValueError("execution_timestamp_required")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("execution_timestamp_must_be_utc")


@dataclass(frozen=True)
class ExecutionClass:
    """Exact compatibility grouping; no inferred cross-size/hardware pooling.

    Unknown fields stay null. Different genes with these same execution
    characteristics can share statistics: gene identities/annotations are absent.
    Additional backends/phases need explicit statistical contracts before use.
    """
    phase: str
    backend: str
    resource_id: str
    implementation_sha256: str | None
    parameters_sha256: str
    memory_bytes: int | None
    scratch_bytes: int | None
    cpu_threads: int | None
    query_residues: int | None
    reference_residues: int | None
    reference_records: int | None
    reference_state: str
    duration_measure: str = "protected_service_wall_seconds"
    wall_seconds: float | None = None

    def __post_init__(self):
        if self.phase not in EXECUTION_PHASE_BACKENDS or EXECUTION_PHASE_BACKENDS[self.phase] != self.backend:
            raise ValueError("unsupported_execution_class")
        _resource(self.resource_id)
        if self.implementation_sha256 is not None:
            _hash(self.implementation_sha256)
        _hash(self.parameters_sha256)
        if self.phase == REPORTED_RESULT_PHASE:
            if (self.duration_measure != REPORTED_RESULT_MEASURE or self.reference_state != 'unknown'
                    or any(getattr(self, name) is not None for name in (
                        'implementation_sha256', 'memory_bytes', 'scratch_bytes', 'cpu_threads',
                        'reference_residues', 'reference_records', 'wall_seconds'))):
                raise ValueError('invalid_reported_result_execution_class')
            if type(self.query_residues) is not int or self.query_residues <= 0:
                raise ValueError('invalid_execution_class_query_residues')
            return
        for name in ("memory_bytes", "scratch_bytes", "cpu_threads", "query_residues",
                     "reference_residues", "reference_records"):
            value = getattr(self, name)
            if value is None and name not in {"memory_bytes", "scratch_bytes"}:
                continue
            if type(value) is not int or value <= 0:
                raise ValueError("invalid_execution_class_" + name)
        if self.reference_state not in {"download_required", "available"}:
            raise ValueError("invalid_execution_reference_state")
        if self.duration_measure not in {"protected_service_wall_seconds", "systemd_service_wall_seconds"}:
            raise ValueError("unsupported_execution_duration_measure")
        if self.wall_seconds is not None and (type(self.wall_seconds) not in (int, float) or
                not math.isfinite(self.wall_seconds) or self.wall_seconds <= 0):
            raise ValueError("invalid_execution_wall_seconds")

    @property
    def ref(self):
        return _ref("execution_class", asdict(self))


@dataclass(frozen=True)
class RunStatistic:
    """One physical phase attempt; repeated polls/replays are not new runs.

    source_sha256 binds the native execution receipt. attempt_sha256 identifies
    the actual attempt separately from its inputs; retry attempts need new IDs.
    condition_ref is captured at execution start, never inferred at ingestion.
    """
    attempt_sha256: str
    source_sha256: str
    observed_at: str
    outcome: str
    duration_kind: str
    elapsed_seconds: float | None
    condition_ref: str | None

    def __post_init__(self):
        _hash(self.attempt_sha256)
        _hash(self.source_sha256)
        _timestamp(self.observed_at)
        if self.outcome not in {"succeeded", "failed", "cancelled", "resource_limit", "unknown"}:
            raise ValueError("invalid_execution_outcome")
        if self.duration_kind not in {"complete", "lower_bound", "unmeasured"}:
            raise ValueError("invalid_execution_duration_kind")
        seconds = self.elapsed_seconds
        if self.duration_kind == "unmeasured":
            if seconds is not None:
                raise ValueError("unmeasured_duration_must_be_null")
        elif type(seconds) not in (float, int) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError("invalid_execution_elapsed_seconds")
        if self.duration_kind == "complete" and self.outcome == "unknown":
            raise ValueError("complete_duration_requires_observed_outcome")
        if self.condition_ref is not None and (type(self.condition_ref) is not str or
                re.fullmatch("execution_condition_[0-9a-f]{64}", self.condition_ref) is None):
            raise ValueError("invalid_execution_condition_reference")


@dataclass(frozen=True)
class ReportedResultStatistic:
    """One logical provider job's completed reported result, not an attempt.

    source_sha256 binds the complete original first witness. Missing internal
    retries, failures and physical execution counts remain unknown.
    condition_ref is the condition actually captured before the winning POST.
    """
    observation_sha256: str
    source_sha256: str
    observed_at: str
    elapsed_seconds: float
    condition_ref: str | None

    def __post_init__(self):
        _hash(self.observation_sha256)
        _hash(self.source_sha256)
        _timestamp(self.observed_at)
        try:
            valid = (type(self.elapsed_seconds) in (float, int)
                and math.isfinite(self.elapsed_seconds) and self.elapsed_seconds >= 0)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('invalid_execution_elapsed_seconds')
        if self.condition_ref is not None and (type(self.condition_ref) is not str or
                re.fullmatch('execution_condition_[0-9a-f]{64}', self.condition_ref) is None):
            raise ValueError('invalid_execution_condition_reference')


class ExpectationReader:
    """Read the statistical snapshots supplied for this child's context."""
    def __init__(self, path, *, snapshot_refs):
        self.snapshot_refs = frozenset(snapshot_refs)
        self.db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)

    def get(self, snapshot_ref):
        if snapshot_ref not in self.snapshot_refs:
            raise ValueError("execution_expectation_not_in_supplied_context")
        row = self.db.execute("SELECT data FROM expectation_snapshots WHERE id=?", (snapshot_ref,)).fetchone()
        if row is None:
            raise ValueError("unknown_execution_expectation")
        return json.loads(row[0])

    def close(self):
        self.db.close()


class RunHistory:
    """Infrastructure-owned writes and caller-owned condition updates.

    The workflow supplies only ExpectationReader to episode tools. RunHistory
    is not an agent capability. No optional text payload or arbitrary numeric
    dictionary is accepted at the shared statistical boundary.
    """
    def __init__(self, path, *, create=True, busy_timeout_seconds=None):
        self.path = Path(path).resolve()
        if busy_timeout_seconds is not None and (type(busy_timeout_seconds) not in (int, float)
                or not math.isfinite(busy_timeout_seconds) or busy_timeout_seconds < 0):
            raise ValueError('invalid_statistics_busy_timeout')
        connection_options = {} if busy_timeout_seconds is None else {'timeout': busy_timeout_seconds}
        if not create:
            self.db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, **connection_options)
            try:
                # Existing-history consumers cannot initialize a missing store
                # or silently add these tables to a different SQLite database.
                self.db.execute("SELECT c.data,r.sequence,r.class_ref,k.resource_id,s.data "
                    "FROM execution_classes c,run_statistics r,execution_conditions k,expectation_snapshots s LIMIT 0")
            except BaseException:
                self.db.close()
                raise
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, **connection_options)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS execution_classes (id TEXT PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS execution_conditions (
          sequence INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, operation_sha256 TEXT UNIQUE NOT NULL,
          resource_id TEXT NOT NULL, data TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS execution_conditions_resource ON execution_conditions(resource_id, sequence);
        CREATE TABLE IF NOT EXISTS run_statistics (
          sequence INTEGER PRIMARY KEY, attempt_sha256 TEXT UNIQUE NOT NULL,
          class_ref TEXT NOT NULL, condition_state TEXT NOT NULL, data TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS run_statistics_class ON run_statistics(class_ref, sequence);
        CREATE TABLE IF NOT EXISTS reported_result_statistics (
          sequence INTEGER PRIMARY KEY, observation_sha256 TEXT UNIQUE NOT NULL,
          class_ref TEXT NOT NULL, condition_state TEXT NOT NULL, data TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS reported_result_statistics_class
          ON reported_result_statistics(class_ref, sequence);
        CREATE TABLE IF NOT EXISTS expectation_snapshots (id TEXT PRIMARY KEY, data TEXT NOT NULL);
        """)

    def close(self):
        self.db.close()

    @contextmanager
    def _write(self):
        # Serialize the check-and-append boundary across history writers.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def set_condition(self, *, operation_sha256, resource_id, state, reason, reported_at):
        """Explicit caller information; does not cancel work or rescore children.

        No automatic expiry. A caller must publish recovery/another condition.
        Measurements preserve the condition recorded at their execution start.
        """
        _hash(operation_sha256)
        _resource(resource_id)
        _timestamp(reported_at)
        if state not in CONDITIONS or reason not in {"operator_report", "outage", "maintenance", "recovered"}:
            raise ValueError("invalid_execution_condition")
        value = dict(resource_id=resource_id, state=state, reason=reason, reported_at=reported_at)
        ref = _ref("execution_condition", {**value, "operation_sha256": operation_sha256})
        with self._write():
            old = self.db.execute("SELECT id FROM execution_conditions WHERE operation_sha256=?",
                                  (operation_sha256,)).fetchone()
            if old and old[0] != ref:
                raise ValueError("execution_condition_operation_conflict")
            if not old:
                self.db.execute("INSERT INTO execution_conditions VALUES(NULL,?,?,?,?)",
                                (ref, operation_sha256, resource_id, _json(value)))
        return ref

    def _condition(self, resource_id, condition_ref=None):
        if condition_ref is None:
            return {"ref": None, "resource_id": resource_id, "state": "unspecified",
                    "reason": None, "reported_at": None}
        row = self.db.execute("SELECT data FROM execution_conditions WHERE id=? AND resource_id=?",
                              (condition_ref, resource_id)).fetchone()
        if row is None:
            raise ValueError("execution_condition_resource_mismatch")
        return {"ref": condition_ref, **json.loads(row[0])}

    def current_condition(self, resource_id):
        _resource(resource_id)
        row = self.db.execute("SELECT id FROM execution_conditions WHERE resource_id=? ORDER BY sequence DESC LIMIT 1",
                              (resource_id,)).fetchone()
        return self._condition(resource_id, row[0] if row else None)

    def record(self, scope: ExecutionClass, statistic: RunStatistic):
        if type(scope) is not ExecutionClass or type(statistic) is not RunStatistic:
            raise TypeError("typed_execution_statistics_required")
        if scope.phase == REPORTED_RESULT_PHASE:
            raise ValueError('reported_result_requires_distinct_statistic')
        # Identity replay preserves the original measurement, including unknowns.
        body = _json(asdict(statistic))
        with self._write():
            condition = self._condition(scope.resource_id, statistic.condition_ref)
            old = self.db.execute("SELECT class_ref,data FROM run_statistics WHERE attempt_sha256=?",
                                  (statistic.attempt_sha256,)).fetchone()
            if old:
                if old != (scope.ref, body):
                    raise ValueError("execution_attempt_measurement_conflict")
                return statistic.attempt_sha256
            self.db.execute("INSERT OR IGNORE INTO execution_classes VALUES(?,?)", (scope.ref, _json(asdict(scope))))
            self.db.execute("INSERT INTO run_statistics VALUES(NULL,?,?,?,?)",
                            (statistic.attempt_sha256, scope.ref, condition["state"], body))
        return statistic.attempt_sha256

    def require_reported_result_schema(self):
        """Check the explicitly installed extension without initializing it."""
        self.db.execute('SELECT sequence,observation_sha256,class_ref,condition_state,data '
                        'FROM reported_result_statistics LIMIT 0')

    def record_reported_result(self, scope: ExecutionClass, statistic: ReportedResultStatistic):
        if type(scope) is not ExecutionClass or type(statistic) is not ReportedResultStatistic:
            raise TypeError('typed_reported_result_statistics_required')
        if scope.phase != REPORTED_RESULT_PHASE or scope.duration_measure != REPORTED_RESULT_MEASURE:
            raise ValueError('reported_result_execution_class_required')
        self.require_reported_result_schema()
        body = _json(asdict(statistic))
        with self._write():
            condition = self._condition(scope.resource_id, statistic.condition_ref)
            old = self.db.execute('SELECT class_ref,data FROM reported_result_statistics '
                'WHERE observation_sha256=?', (statistic.observation_sha256,)).fetchone()
            if old:
                if old != (scope.ref, body):
                    raise ValueError('reported_result_measurement_conflict')
                return statistic.observation_sha256
            self.db.execute('INSERT OR IGNORE INTO execution_classes VALUES(?,?)',
                            (scope.ref, _json(asdict(scope))))
            self.db.execute('INSERT INTO reported_result_statistics VALUES(NULL,?,?,?,?)',
                (statistic.observation_sha256, scope.ref, condition['state'], body))
        return statistic.observation_sha256

    def _capture_reported_result(self, scope):
        self.require_reported_result_schema()
        with self._write():
            condition = self.current_condition(scope.resource_id)
            sequence = self.db.execute('SELECT COALESCE(MAX(sequence),0) '
                'FROM reported_result_statistics WHERE class_ref=?', (scope.ref,)).fetchone()[0]
            rows = self.db.execute('''SELECT condition_state,count(*),
                avg(json_extract(data,'$.elapsed_seconds')),
                min(json_extract(data,'$.elapsed_seconds')),
                max(json_extract(data,'$.elapsed_seconds'))
                FROM reported_result_statistics WHERE class_ref=? AND sequence<=?
                GROUP BY condition_state ORDER BY condition_state''', (scope.ref, sequence)).fetchall()
            keys = ('condition_state', 'reported_result_count', 'mean_seconds', 'min_seconds', 'max_seconds')
            value = {'version': REPORTED_RESULT_VERSION, 'class_ref': scope.ref,
                'execution_class': asdict(scope), 'history_through_sequence': sequence,
                'current_condition': condition, 'observation_unit': REPORTED_RESULT_UNIT,
                'statistics': [dict(zip(keys, row)) for row in rows],
                'expectation_method': 'empirical_reported_result_duration_mean_by_condition_v1'}
            ref = _ref('execution_expectation', value)
            self.db.execute('INSERT OR IGNORE INTO expectation_snapshots VALUES(?,?)', (ref, _json(value)))
            return ref

    def capture(self, scope: ExecutionClass):
        """Freeze descriptive expectations, without updating any episode.

        SQL summaries keep closed histories on disk. Mean/min/max describe
        complete durations for the exact class, condition and outcome. They
        are not calibrated remaining-time forecasts or a continuation policy.
        Censored/missing times cannot masquerade as completed zero-time jobs.
        """
        if type(scope) is not ExecutionClass:
            raise TypeError("typed_execution_class_required")
        if scope.phase == REPORTED_RESULT_PHASE:
            return self._capture_reported_result(scope)
        # A single transaction binds observations and current condition even
        # when another execution process is recording a new observation.
        with self._write():
            condition = self.current_condition(scope.resource_id)
            sequence = self.db.execute("SELECT COALESCE(MAX(sequence),0) FROM run_statistics WHERE class_ref=?",
                                       (scope.ref,)).fetchone()[0]
            rows = self.db.execute("""
                SELECT condition_state, json_extract(data,'$.outcome'), count(*),
                  sum(json_extract(data,'$.duration_kind')='complete'),
                  avg(CASE WHEN json_extract(data,'$.duration_kind')='complete' THEN json_extract(data,'$.elapsed_seconds') END),
                  min(CASE WHEN json_extract(data,'$.duration_kind')='complete' THEN json_extract(data,'$.elapsed_seconds') END),
                  max(CASE WHEN json_extract(data,'$.duration_kind')='complete' THEN json_extract(data,'$.elapsed_seconds') END),
                  sum(json_extract(data,'$.duration_kind')='lower_bound'),
                  max(CASE WHEN json_extract(data,'$.duration_kind')='lower_bound' THEN json_extract(data,'$.elapsed_seconds') END),
                  sum(json_extract(data,'$.duration_kind')='unmeasured')
                FROM run_statistics WHERE class_ref=? AND sequence<=?
                GROUP BY condition_state,json_extract(data,'$.outcome') ORDER BY 1,2
                """, (scope.ref, sequence)).fetchall()
            keys = ("condition_state", "outcome", "attempt_count", "complete_duration_count",
                    "mean_seconds", "min_seconds", "max_seconds", "lower_bound_count",
                    "max_lower_bound_seconds", "unmeasured_count")
            value = {"version": VERSION, "class_ref": scope.ref, "execution_class": asdict(scope),
                     "history_through_sequence": sequence, "current_condition": condition,
                     "statistics": [dict(zip(keys, row)) for row in rows],
                     "expectation_method": "empirical_complete_duration_mean_by_condition_and_outcome_v1"}
            ref = _ref("execution_expectation", value)
            self.db.execute("INSERT OR IGNORE INTO expectation_snapshots VALUES(?,?)", (ref, _json(value)))
            return ref

    def reader(self, *snapshot_refs):
        return ExpectationReader(self.path, snapshot_refs=snapshot_refs)
