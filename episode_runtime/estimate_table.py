"""The estimate table: the run's memory of what was expected of costly actions and what happened.

``EstimateTable`` is a service of the run (``ctx.services['estimate_table']``). It is the one thing that outlasts
a run on purpose: the next run's decisions read what earlier runs expected and obtained. So it is outside the
Store and outside custody, in one SQLite file of its own that the run's caller names. It holds no Store record
and no scientific evidence; its numbers never enter an Episode's credit.

It keeps two things.

**Actions.** One row per costly action (a job launch, a child commission), under the acting unit's
``ctx.operation_key``:

- ``expect(kind, expectation, key=..., at=...)`` records, **before the action runs**, what is expected of it: its
  gain band (``{'value', 'lower', 'upper'}``, in the acting Episode's own credit units), its cost and anything else
  the caller predicts (a duration, the outcome probabilities);
- ``resolve(key, actual, at=...)`` records what happened: the gain obtained, the cost, the outcome, the scores of
  the estimates;
- ``kind_statistics(kind)`` is what the action-value calculation reads: for the resolved actions of the kind, the
  band of the gains obtained, the typical cost and duration, and the correction (gain obtained over gain expected:
  how far earlier predictions of this kind were off).

A key is written once. A unit that runs again repeats its ``expect`` or ``resolve`` with the same content and is
given the stored row; other content under the same key raises ``EstimateTableError('identity_conflict')``. The
first recorded time stands.

**Observations of resources and attempts** (the operational memory the HPC planning functions read):
``observe`` and ``latest`` keep the latest capacity, queue or inventory observation of a resource, which goes
stale after the policy's interval; ``record`` and ``history`` keep one final measurement per physical attempt,
weighted by age; ``profiles`` lists the compatibility classes that have measurements.

**Decisions read through the system.** ``decide`` and ``action`` hold only the read handle:
``ctx.services['estimate_table'].read('kind_statistics', kind)``. The system records the value with the decision
and gives the same value when the decision is made again, whatever the table says by then. A tool is handed the
table itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import sqlite3
import time

from method_loop.jsonvalue import canonical, closed_copy, content_digest

OBSERVATION_KINDS = ('capacity', 'queue', 'inventory')
DURATION_METRICS = ('queue', 'setup', 'work', 'return')
RESOURCE_UNITS = {'cpu_seconds': 'cpu_seconds', 'memory_bytes': 'bytes'}
PROFILE_FIELDS = ('resource_id', 'backend', 'tool', 'implementation', 'parameters', 'hardware')
_SCHEMA = """
CREATE TABLE IF NOT EXISTS actions(key TEXT PRIMARY KEY, kind TEXT NOT NULL, expected TEXT NOT NULL,
    expected_at TEXT NOT NULL, actual TEXT, resolved_at TEXT);
CREATE INDEX IF NOT EXISTS actions_by_kind ON actions(kind, expected_at DESC);
CREATE TABLE IF NOT EXISTS resource_observations(id TEXT PRIMARY KEY, resource TEXT, kind TEXT, observed REAL,
    body TEXT);
CREATE INDEX IF NOT EXISTS resource_observation_latest ON resource_observations(resource, kind, observed DESC);
CREATE TABLE IF NOT EXISTS execution_measurements(attempt TEXT PRIMARY KEY, compatibility TEXT, resource TEXT,
    observed REAL, body TEXT);
CREATE INDEX IF NOT EXISTS execution_measurement_class ON execution_measurements(compatibility, observed DESC);
CREATE INDEX IF NOT EXISTS execution_measurement_resource ON execution_measurements(resource, observed DESC);
"""


class EstimateTableError(ValueError):
    """A row was written against the table's rules (``identity_conflict``, an invalid row)."""


@dataclass(frozen=True)
class ForgettingPolicy:
    """After how long an observation is stale and a measurement leaves the history, in seconds."""
    capacity_seconds: float = 15
    queue_seconds: float = 120
    inventory_seconds: float = 86400
    history_seconds: float = 90 * 86400
    history_half_life_seconds: float = 14 * 86400
    queue_history_seconds: float = 7 * 86400
    queue_half_life_seconds: float = 86400

    def __post_init__(self):
        if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0
               for value in asdict(self).values()):
            raise EstimateTableError('positive_finite_forgetting_intervals_required')


def _number(value, what):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise EstimateTableError(what + '_must_be_a_finite_number')
    return value


def _text(value, what):
    if type(value) is not str or not value:
        raise EstimateTableError(what + '_must_be_text')
    return value


def _quantile(values, fraction):
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _band(values):
    """The band of a list of numbers: its 10th percentile, median and 90th percentile; ``None`` when empty."""
    if not values:
        return None
    return {'low': _quantile(values, 0.1), 'typical': _quantile(values, 0.5), 'high': _quantile(values, 0.9)}


def validate_profile(value):
    """The compatibility class of a measurement: exactly resource, backend, tool, implementation, parameters and
    hardware, each short text. Sizes and allocations belong in the measurement's features."""
    if (not isinstance(value, dict) or set(value) != set(PROFILE_FIELDS)
            or value['backend'] not in ('local', 'hpc', 'api')
            or any(type(item) is not str or not item.strip() or len(item) > 512 for item in value.values())):
        raise EstimateTableError('explicit_execution_compatibility_profile_required')
    return closed_copy(value, 'execution_profile', EstimateTableError)


def measured_value(metric, item):
    """The number of one measured metric: seconds of a duration, or the value of a resource in its unit."""
    if metric in RESOURCE_UNITS:
        if item['unit'] != RESOURCE_UNITS[metric]:
            raise EstimateTableError('resource_measurement_unit_conflict:' + metric)
        value = item['value']
    elif metric in DURATION_METRICS:
        value = item['seconds']
    else:
        raise EstimateTableError('measured_metric_unknown:' + str(metric))
    if _number(value, 'measured_value') < 0:
        raise EstimateTableError('nonnegative_measured_value_required:' + metric)
    return value


class EstimateTable:
    """The table in the SQLite file ``path``. No connection is kept open between calls."""

    def __init__(self, path, *, policy=None):
        self.path = Path(path).expanduser().resolve()
        self._policy = ForgettingPolicy(**({} if policy is None else policy))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.executescript(_SCHEMA)

    def _connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def _all(self, query, operands=()):
        db = self._connection()
        try:
            return db.execute(query, tuple(operands)).fetchall()
        finally:
            db.close()

    def as_record(self):
        return {'path': str(self.path), 'policy': asdict(self._policy)}

    def policy(self):
        return asdict(self._policy)

    # -- actions: what was expected, then what happened -------------------------------------------------------
    @staticmethod
    def _action(row):
        return {'key': row['key'], 'kind': row['kind'], 'expected': json.loads(row['expected']),
                'expected_at': row['expected_at'],
                'actual': None if row['actual'] is None else json.loads(row['actual']),
                'resolved_at': row['resolved_at']}

    def expect(self, kind, expectation, *, key, at):
        """Record what is expected of the action ``key`` of ``kind`` before it runs; the stored row. The
        expectation names at least its gain band and its cost."""
        _text(kind, 'estimate_kind'), _text(key, 'estimate_key'), _text(at, 'estimate_time')
        expectation = closed_copy(expectation, 'expectation', EstimateTableError)
        if not isinstance(expectation, dict) or not {'gain', 'cost'} <= set(expectation):
            raise EstimateTableError('expectation_requires_gain_and_cost')
        gain = expectation['gain']
        if not isinstance(gain, dict) or set(gain) != {'value', 'lower', 'upper'}:
            raise EstimateTableError('expected_gain_requires_value_lower_upper')
        if not (_number(gain['lower'], 'expected_gain_lower') <= _number(gain['value'], 'expected_gain_value')
                <= _number(gain['upper'], 'expected_gain_upper')):
            raise EstimateTableError('expected_gain_band_must_be_ordered')
        _number(expectation['cost'], 'expected_cost')
        db = self._connection()
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                stored = db.execute('SELECT * FROM actions WHERE key=?', (key,)).fetchone()
                if stored is None:
                    db.execute('INSERT INTO actions VALUES(?,?,?,?,NULL,NULL)',
                               (key, kind, canonical(expectation), at))
                elif stored['kind'] != kind or stored['expected'] != canonical(expectation):
                    raise EstimateTableError('identity_conflict:expectation:' + key)
                return self._action(db.execute('SELECT * FROM actions WHERE key=?', (key,)).fetchone())
        finally:
            db.close()

    def resolve(self, key, actual, *, at):
        """Record what happened to the action ``key``: at least the gain obtained, the cost and the outcome."""
        _text(key, 'estimate_key'), _text(at, 'estimate_time')
        actual = closed_copy(actual, 'actual', EstimateTableError)
        if not isinstance(actual, dict) or not {'gain', 'cost', 'outcome'} <= set(actual):
            raise EstimateTableError('actual_requires_gain_cost_and_outcome')
        _number(actual['gain'], 'actual_gain'), _number(actual['cost'], 'actual_cost')
        _text(actual['outcome'], 'actual_outcome')
        if 'duration_seconds' in actual:
            _number(actual['duration_seconds'], 'actual_duration_seconds')
        db = self._connection()
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                stored = db.execute('SELECT * FROM actions WHERE key=?', (key,)).fetchone()
                if stored is None:
                    raise EstimateTableError('no_expectation_recorded_before_the_action:' + key)
                if stored['actual'] is None:
                    db.execute('UPDATE actions SET actual=?, resolved_at=? WHERE key=?', (canonical(actual), at, key))
                elif stored['actual'] != canonical(actual):
                    raise EstimateTableError('identity_conflict:actual:' + key)
                return self._action(db.execute('SELECT * FROM actions WHERE key=?', (key,)).fetchone())
        finally:
            db.close()

    def expectation(self, key):
        """The row of the action ``key``, or ``None``."""
        rows = self._all('SELECT * FROM actions WHERE key=?', (_text(key, 'estimate_key'),))
        return self._action(rows[0]) if rows else None

    def kinds(self):
        return [row['kind'] for row in self._all('SELECT DISTINCT kind FROM actions ORDER BY kind')]

    def rows(self, kind, limit=100):
        """The actions of ``kind``, the latest expectation first; at most ``limit``."""
        if type(limit) is not int or limit < 1:
            raise EstimateTableError('estimate_rows_limit_must_be_a_positive_integer')
        return [self._action(row) for row in self._all(
            'SELECT * FROM actions WHERE kind=? ORDER BY expected_at DESC, key LIMIT ?',
            (_text(kind, 'estimate_kind'), limit))]

    def kind_statistics(self, kind):
        """What earlier actions of ``kind`` say, for the action-value calculation: how many were resolved and how
        many are open; the band (10th percentile, median, 90th percentile) of the gains obtained, of the costs and
        of the durations; and the correction, the sum of the gains obtained over the sum of the gains expected
        (``None`` while nothing is resolved or the expected gains sum to nothing)."""
        rows = [self._action(row) for row in self._all('SELECT * FROM actions WHERE kind=? ORDER BY key',
                                                       (_text(kind, 'estimate_kind'),))]
        resolved = [row for row in rows if row['actual'] is not None]
        expected = math.fsum(row['expected']['gain']['value'] for row in resolved)
        obtained = math.fsum(row['actual']['gain'] for row in resolved)
        return {'kind': kind, 'resolved': len(resolved), 'open': len(rows) - len(resolved),
                'gain': _band([row['actual']['gain'] for row in resolved]),
                'cost': _band([row['actual']['cost'] for row in resolved]),
                'duration_seconds': _band([row['actual']['duration_seconds'] for row in resolved
                                           if 'duration_seconds' in row['actual']]),
                'expected_gain': expected, 'obtained_gain': obtained,
                'correction': obtained / expected if resolved and expected > 0 else None}

    # -- observations of a resource ---------------------------------------------------------------------------
    def observe(self, resource, kind, data, *, observed_at, provenance):
        """Keep one observation of a resource (its capacity, queue or inventory); its reference."""
        if kind not in OBSERVATION_KINDS or not resource or not provenance:
            raise EstimateTableError('typed_resource_observation_with_provenance_required')
        body = closed_copy({'resource_id': resource, 'kind': kind,
                            'observed_at': _number(observed_at, 'observation_time'), 'data': data,
                            'provenance': provenance}, 'resource_observation', EstimateTableError)
        reference = 'resource:' + content_digest(body)
        db = self._connection()
        try:
            with db:
                db.execute('INSERT OR IGNORE INTO resource_observations VALUES(?,?,?,?,?)',
                           (reference, resource, kind, observed_at, canonical(body)))
        finally:
            db.close()
        return reference

    def latest(self, resource, kind, now=None):
        """The latest observation of the resource at ``now`` (the real clock when ``None``): ``state`` is
        ``fresh``, ``stale`` (its data withheld) or ``unknown`` (none was made)."""
        if kind not in OBSERVATION_KINDS:
            raise EstimateTableError('unknown_resource_observation_kind')
        now = time.time() if now is None else _number(now, 'observation_time')
        rows = self._all('SELECT id, body FROM resource_observations WHERE resource=? AND kind=? AND observed<=? '
                         'ORDER BY observed DESC, id LIMIT 1', (resource, kind, now))
        if not rows:
            return {'resource_id': resource, 'kind': kind, 'state': 'unknown', 'data': None}
        body = json.loads(rows[0]['body'])
        age = now - body['observed_at']
        fresh = age <= getattr(self._policy, kind + '_seconds')
        return {**body, 'reference': rows[0]['id'], 'age_seconds': age, 'state': 'fresh' if fresh else 'stale',
                'data': body['data'] if fresh else None}

    # -- measurements of physical attempts --------------------------------------------------------------------
    def record(self, *, attempt_id, profile, observation):
        """Keep the final measurement of one physical attempt (failures and censored times included). The same
        measurement again changes nothing; another one for the same attempt raises."""
        profile = validate_profile(profile)
        observation = closed_copy(observation, 'attempt_observation', EstimateTableError)
        if (not attempt_id or not observation['provenance'] or type(observation['success']) not in (bool, type(None))):
            raise EstimateTableError('measured_attempt_with_provenance_required')
        _number(observation['observed_at'], 'attempt_observation_time')
        for value in observation['features'].values():
            if value is not None:
                _number(value, 'execution_feature')
        for metric, item in observation['metrics'].items():
            if type(item['censored']) is not bool:
                raise EstimateTableError('measured_duration_or_censored_bound_required')
            measured_value(metric, item)
        body = canonical({'profile': profile, 'observation': observation})
        db = self._connection()
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                stored = db.execute('SELECT body FROM execution_measurements WHERE attempt=?',
                                    (attempt_id,)).fetchone()
                if stored is None:
                    db.execute('INSERT INTO execution_measurements VALUES(?,?,?,?,?)', (
                        attempt_id, content_digest(profile), profile['resource_id'], observation['observed_at'],
                        body))
                elif stored['body'] != body:
                    raise EstimateTableError('identity_conflict:attempt:' + str(attempt_id))
        finally:
            db.close()

    def history(self, profile, now=None, queue_only=False, limit=2000):
        """The measurements of the profile's compatibility class (of its resource, with ``queue_only``) that are
        within the policy's window at ``now``, the latest first, each metric weighted by its age."""
        profile = validate_profile(profile)
        if type(limit) is not int or not 1 <= limit <= 2000:
            raise EstimateTableError('execution_history_limit_must_be_1_to_2000')
        now = time.time() if now is None else _number(now, 'history_time')
        policy = self._policy
        window = policy.queue_history_seconds if queue_only else policy.history_seconds
        column, key = (('resource', profile['resource_id']) if queue_only
                       else ('compatibility', content_digest(profile)))
        rows = self._all('SELECT attempt, body FROM execution_measurements WHERE ' + column + '=? AND observed>=? '
                         'AND observed<=? ORDER BY observed DESC, attempt LIMIT ?', (key, now - window, now, limit))
        result = []
        for found in rows:
            row = json.loads(found['body'])['observation']
            metrics = {}
            for name, item in row['metrics'].items():
                if queue_only and name != 'queue':
                    continue
                age = now - (item['observed_at'] if 'observed_at' in item else row['observed_at'])
                queue = name == 'queue'
                horizon = policy.queue_history_seconds if queue else policy.history_seconds
                half_life = policy.queue_half_life_seconds if queue else policy.history_half_life_seconds
                if 0 <= age <= horizon:
                    metrics[name] = {**item, 'weight': 2 ** (-age / half_life)}
            if not metrics and (queue_only or row['success'] is None):
                continue
            result.append({**row, 'id': 'shared:' + found['attempt'], 'metrics': metrics,
                           'success': None if queue_only else row['success'],
                           'weight': 2 ** (-(now - row['observed_at']) / policy.history_half_life_seconds)})
        return result

    def profiles(self, tools=None, now=None, limit=32):
        """The compatibility classes that have a measurement within the history window, the latest first."""
        if type(limit) is not int or not 1 <= limit <= 128:
            raise EstimateTableError('execution_profile_limit_must_be_1_to_128')
        now = time.time() if now is None else _number(now, 'history_time')
        query = ("SELECT compatibility, MAX(observed) AS latest, COUNT(*) AS attempts, "
                 "json_extract(body, '$.profile') AS profile FROM execution_measurements "
                 "WHERE observed>=? AND observed<=?")
        operands = [now - self._policy.history_seconds, now]
        if tools:
            query += " AND json_extract(body, '$.profile.tool') IN (" + ','.join('?' for _ in tools) + ')'
            operands.extend(tools)
        rows = self._all(query + ' GROUP BY compatibility ORDER BY MAX(observed) DESC LIMIT ?', (*operands, limit))
        return [{'profile': json.loads(row['profile']), 'latest_observed_at': row['latest'],
                 'attempt_count': row['attempts']} for row in rows]


__all__ = ['DURATION_METRICS', 'EstimateTable', 'EstimateTableError', 'ForgettingPolicy', 'OBSERVATION_KINDS',
           'RESOURCE_UNITS', 'measured_value', 'validate_profile']
