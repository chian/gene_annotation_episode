"""Shared operational memory. Observations expire; original receipts do not.

This is infrastructure data, never scientific evidence or earned credit. Short
SQLite transactions share measurements between windows without serializing
their workflows. No service is contacted while reading this library.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class ForgettingPolicy:
    capacity_seconds: float = 15
    queue_seconds: float = 120
    inventory_seconds: float = 86400
    history_seconds: float = 90 * 86400
    history_half_life_seconds: float = 14 * 86400
    queue_history_seconds: float = 7 * 86400
    queue_half_life_seconds: float = 86400

    def __post_init__(self):
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
               for v in asdict(self).values()):
            raise ValueError('positive_finite_forgetting_intervals_required')


def validate_profile(value):
    """Hard compatibility boundaries; sizes/allocation belong in features.

    Fingerprints must be known before transferring work-time expectations.
    Labels must describe software/hardware, never a gene's scientific result.
    """
    fields = {'resource_id', 'backend', 'tool', 'implementation', 'parameters', 'hardware'}
    if (not isinstance(value, dict) or set(value) != fields
            or value['backend'] not in ('local', 'hpc', 'api')
            or any(not isinstance(v, str) or not v.strip() or len(v) > 512 for v in value.values())):
        raise ValueError('explicit_execution_compatibility_profile_required')
    return json.loads(canonical(value))


class ExecutionMemory:
    def __init__(self, path, *, policy=None):
        self.path = Path(path).expanduser().resolve()
        self.policy = ForgettingPolicy(**(policy or {}))

    @classmethod
    def configured(cls):
        default = Path(__file__).resolve().parents[1]/'runs'/'shared-execution'/'memory.sqlite3'
        return cls(os.environ.get('GENE_EPISODE_EXECUTION_MEMORY', str(default)))

    def as_record(self):
        return {'path': str(self.path), 'policy': asdict(self.policy)}

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=2)
        db.execute('CREATE TABLE IF NOT EXISTS resource_observations '
            '(id TEXT PRIMARY KEY, resource TEXT, kind TEXT, observed REAL, body TEXT)')
        db.execute('CREATE INDEX IF NOT EXISTS resource_observation_latest '
            'ON resource_observations(resource,kind,observed DESC)')
        db.execute('CREATE TABLE IF NOT EXISTS execution_measurements '
            '(attempt TEXT PRIMARY KEY, compatibility TEXT, resource TEXT, observed REAL, body TEXT)')
        db.execute('CREATE INDEX IF NOT EXISTS execution_measurement_class '
            'ON execution_measurements(compatibility,observed DESC)')
        db.execute('CREATE INDEX IF NOT EXISTS execution_measurement_resource '
            'ON execution_measurements(resource,observed DESC)')
        return db

    def observe(self, resource, kind, data, *, observed_at, provenance):
        if kind not in ('capacity', 'queue', 'inventory') or not resource or not provenance:
            raise ValueError('typed_resource_observation_with_provenance_required')
        if not math.isfinite(observed_at):
            raise ValueError('finite_observation_time_required')
        body = {'resource_id': resource, 'kind': kind, 'observed_at': observed_at,
                'data': data, 'provenance': provenance}
        reference = 'resource:'+digest(body)
        db = self._connect()
        try:
            with db:
                db.execute('INSERT OR IGNORE INTO resource_observations VALUES(?,?,?,?,?)',
                    (reference, resource, kind, observed_at, canonical(body)))
        finally:
            db.close()
        return reference

    def latest(self, resource, kind, *, now=None):
        if kind not in ('capacity', 'queue', 'inventory'):
            raise ValueError('unknown_resource_observation_kind')
        now = time.time() if now is None else now
        empty = {'resource_id': resource, 'kind': kind, 'state': 'unknown', 'data': None}
        if not self.path.exists():
            return empty
        db = self._connect()
        try:
            row = db.execute('SELECT id,body FROM resource_observations '
                'WHERE resource=? AND kind=? AND observed<=? ORDER BY observed DESC,id LIMIT 1',
                (resource, kind, now)).fetchone()
        finally:
            db.close()
        if row is None:
            return empty
        body = json.loads(row[1])
        age = now-body['observed_at']
        fresh = age <= getattr(self.policy, kind+'_seconds')
        return {**body, 'reference': row[0], 'age_seconds': age,
                'state': 'fresh' if fresh else 'stale', 'data': body['data'] if fresh else None}

    def record(self, *, attempt_id, profile, observation):
        """One final physical attempt, including failures and censored times.

        Polls update the owning ledger. Only closure exports here. Replaying a
        receipt is idempotent; conflicting outcomes cannot overwrite history.
        """
        profile = validate_profile(profile)
        if (not attempt_id or not observation.get('provenance')
                or not math.isfinite(observation['observed_at'])
                or type(observation.get('success')) not in (bool, type(None))):
            raise ValueError('measured_attempt_with_provenance_required')
        if any(type(v) not in (int, float) and v is not None or
               type(v) in (int, float) and not math.isfinite(v)
               for v in observation['features'].values()):
            raise ValueError('numeric_execution_features_required')
        from .hpc_resource_prediction import RESOURCE_UNITS, measured_value
        for metric, item in observation['metrics'].items():
            if (metric not in ('queue', 'setup', 'work', 'return', *RESOURCE_UNITS)
                    or type(item.get('censored')) is not bool):
                raise ValueError('measured_duration_or_censored_bound_required')
            measured_value(metric, item)
        body = canonical({'profile': profile, 'observation': observation})
        db = self._connect()
        try:
            with db:
                old = db.execute('SELECT body FROM execution_measurements WHERE attempt=?', (attempt_id,)).fetchone()
                if old and old[0] != body:
                    raise ValueError('physical_attempt_measurement_conflict')
                db.execute('INSERT OR IGNORE INTO execution_measurements VALUES(?,?,?,?,?)',
                    (attempt_id, digest(profile), profile['resource_id'], observation['observed_at'], body))
        finally:
            db.close()

    def history(self, profile, *, now=None, queue_only=False, limit=2000):
        profile = validate_profile(profile)
        if type(limit) is not int or not 1 <= limit <= 2000:
            raise ValueError('bounded_execution_history_required')
        now = time.time() if now is None else now
        if not self.path.exists():
            return []
        window = self.policy.queue_history_seconds if queue_only else self.policy.history_seconds
        column, key = ('resource', profile['resource_id']) if queue_only else ('compatibility', digest(profile))
        db = self._connect()
        try:
            rows = db.execute(f'SELECT attempt,body FROM execution_measurements WHERE {column}=? '
                'AND observed>=? AND observed<=? ORDER BY observed DESC,attempt LIMIT ?',
                (key, now-window, now, limit)).fetchall()
        finally:
            db.close()
        result = []
        for attempt, raw in rows:
            body = json.loads(raw)
            row = body['observation']
            metrics = {}
            for name, item in row['metrics'].items():
                if queue_only and name != 'queue':
                    continue
                age = now-item.get('observed_at', row['observed_at'])
                horizon = self.policy.queue_history_seconds if name == 'queue' else self.policy.history_seconds
                half_life = self.policy.queue_half_life_seconds if name == 'queue' else self.policy.history_half_life_seconds
                if 0 <= age <= horizon:
                    metrics[name] = {**item, 'weight': 2**(-age/half_life)}
            if not metrics and (queue_only or row['success'] is None):
                continue
            result.append({**row, 'id': 'shared:'+attempt, 'metrics': metrics,
                'success': None if queue_only else row['success'],
                'weight': 2**(-(now-row['observed_at'])/self.policy.history_half_life_seconds)})
        return result

    def profiles(self, *, tools=None, now=None, limit=32):
        """Discover existing compatibility keys without guessing fingerprints."""
        if type(limit) is not int or not 1 <= limit <= 128:
            raise ValueError('bounded_execution_profile_selection_required')
        now = time.time() if now is None else now
        if not self.path.exists():
            return []
        db = self._connect()
        try:
            query = ('SELECT compatibility,MAX(observed),COUNT(*),json_extract(body,\'$.profile\') '
                'FROM execution_measurements WHERE observed>=? AND observed<=?')
            operands = [now-self.policy.history_seconds, now]
            if tools:
                query += ' AND json_extract(body,\'$.profile.tool\') IN ('+','.join('?' for _ in tools)+')'
                operands.extend(tools)
            rows = db.execute(query+' GROUP BY compatibility ORDER BY MAX(observed) DESC LIMIT ?',
                              (*operands, limit)).fetchall()
        finally:
            db.close()
        return [{'profile': json.loads(raw), 'latest_observed_at': observed, 'attempt_count': count}
                for _, observed, count, raw in rows]

    def import_native_statistic(self, scope, statistic):
        """Bridge the existing native receipt exporter; no second measurement."""
        profile = {'resource_id': scope.resource_id, 'backend': 'local', 'tool': scope.phase,
            'implementation': scope.implementation_sha256 or 'unknown:'+scope.ref,
            'parameters': scope.parameters_sha256, 'hardware': scope.resource_id}
        observed = datetime.fromisoformat(statistic.observed_at).timestamp()
        metrics = {} if statistic.elapsed_seconds is None else {'work': {
            'seconds': statistic.elapsed_seconds, 'censored': statistic.duration_kind == 'lower_bound'}}
        self.record(attempt_id='native:'+statistic.attempt_sha256, profile=profile,
            observation={'observed_at': observed, 'features': {key: getattr(scope, key) for key in
                ('memory_bytes', 'scratch_bytes', 'cpu_threads', 'query_residues', 'reference_residues',
                 'reference_records', 'wall_seconds')}, 'metrics': metrics,
                'success': None if statistic.outcome == 'unknown' else statistic.outcome == 'succeeded',
                'provenance': [statistic.source_sha256, scope.ref]})
