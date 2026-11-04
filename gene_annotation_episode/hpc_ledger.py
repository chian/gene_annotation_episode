"""Immutable HPC evidence and replaceable, deduplicated credit projections.

One database per commissioned HPC parent, shared with its prediction child.
Forecasts precede their outcomes; revisions are new records. A scoring slot is
fixed by the caller, so polling and splitting jobs cannot manufacture credit.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time

from .hpc_queue import canonical, digest
from .hpc_prediction import log_score


class HPCLedger:
    @classmethod
    def open_existing(cls, directory):
        path = Path(directory)/'hpc.sqlite'
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True) as db:
            row = db.execute("SELECT body FROM evidence WHERE id='commission'").fetchone()
        if row is None:
            raise ValueError('original_hpc_commission_missing')
        return cls(directory, json.loads(row[0]))

    def __init__(self, directory, commission):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory/'hpc.sqlite'
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, recorded REAL NOT NULL,
                    body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS actions (
                    operation_key TEXT PRIMARY KEY, signature TEXT NOT NULL, result TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS credits (
                    slot TEXT PRIMARY KEY, kind TEXT NOT NULL, value REAL NOT NULL,
                    evidence_id TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS forecast_slots (
                    slot TEXT PRIMARY KEY, forecast_id TEXT NOT NULL);
            ''')
            self._put(db, 'commission', 'commission', commission)
        self.commission = json.loads(canonical(commission))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _put(db, identity, kind, body):
        serialized = canonical(body)
        prior = db.execute('SELECT kind,body FROM evidence WHERE id=?', (identity,)).fetchone()
        if prior is not None and prior != (kind, serialized):
            raise ValueError('immutable_hpc_evidence_conflict:'+identity)
        db.execute('INSERT OR IGNORE INTO evidence VALUES (?,?,?,?)', (identity, kind, time.time(), serialized))
        return identity

    def put(self, kind, body, *, identity=None):
        with self.connection() as db:
            return self._put(db, identity or kind+'_'+digest(body), kind, body)

    def read(self, identity):
        with self.connection() as db:
            row = db.execute('SELECT body FROM evidence WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise ValueError('unknown_hpc_evidence:'+identity)
        return json.loads(row[0])

    def records(self, kind):
        with self.connection() as db:
            rows = db.execute('SELECT id,body FROM evidence WHERE kind=? ORDER BY recorded,id', (kind,)).fetchall()
        return [{'id': row[0], 'body': json.loads(row[1])} for row in rows]

    def once(self, identity, kind, calculate):
        """Recover a committed step without another observation or calculation."""
        with self.connection() as db:
            row = db.execute('SELECT body FROM evidence WHERE id=?', (identity,)).fetchone()
        if row is not None:
            return json.loads(row[0])
        value = calculate()
        self.put(kind, value, identity=identity)
        return value

    def cached(self, operation_key, selection):
        with self.connection() as db:
            row = db.execute('SELECT signature,result FROM actions WHERE operation_key=?', (operation_key,)).fetchone()
        if row is None:
            return None
        if row[0] != digest(selection):
            raise ValueError('hpc_action_identity_conflict')
        return json.loads(row[1])

    def save_action(self, operation_key, selection, result):
        old = self.cached(operation_key, selection)
        if old is not None:
            if canonical(old) != canonical(result):
                raise ValueError('hpc_action_result_conflict')
            return old
        with self.connection() as db:
            db.execute('INSERT INTO actions VALUES (?,?,?)', (operation_key, digest(selection), canonical(result)))
        return result

    def model_credit(self, model_ref, improvement):
        # A new model replaces the projection, including negative corrections.
        with self.connection() as db:
            db.execute('INSERT OR REPLACE INTO credits VALUES (?,?,?,?)',
                ('model', 'model', self.commission['credit']['model_scale']*improvement, model_ref))

    def freeze(self, body, eligible_slots):
        """Freeze a forecast then reserve each original slot at most once."""
        with self.connection() as db:
            identity = self._put(db, 'forecast_'+digest(body), 'forecast', body)
            for slot in eligible_slots:
                db.execute('INSERT OR IGNORE INTO forecast_slots VALUES (?,?)', (slot, identity))
        return identity

    def score(self, measured_ref):
        measured = self.read(measured_ref)
        with self.connection() as db:
            for slot in self.commission['credit']['validation_slots']:
                row = db.execute('SELECT forecast_id FROM forecast_slots WHERE slot=?', (slot['id'],)).fetchone()
                if row is None or slot['metric'] not in measured['metrics']:
                    continue
                forecast_id = row[0]
                forecast = json.loads(db.execute('SELECT body FROM evidence WHERE id=?', (forecast_id,)).fetchone()[0])
                if forecast['plan_id'] != measured['plan_id']:
                    continue
                metric = slot['metric']
                observation = measured['metrics'][metric]
                if observation['observed_at'] <= forecast['issued_at']:
                    continue  # never validate a forecast against an already known event
                baseline = forecast['reference']['times'][metric]
                predicted = forecast['prediction']['times'][metric]
                if predicted is None or baseline is None:
                    continue
                elapsed = forecast['elapsed'].get(metric, 0.)
                remaining = observation['seconds']-elapsed
                if remaining < 0:
                    continue
                censored = observation.get('censored', False)
                gain = log_score(predicted, remaining, censored=censored)-log_score(baseline, remaining, censored=censored)
                value = self.commission['credit']['validation_scale']*slot['weight']*gain
                evidence = {'forecast_id': forecast_id, 'measured_ref': measured_ref, 'slot': slot['id'],
                            'value': value, 'censored': censored}
                evidence_id = self._put(db, 'score_'+digest(evidence), 'score', evidence)
                # A later actual finish replaces a censored interim score.
                prior = db.execute('SELECT evidence_id FROM credits WHERE slot=?', ('validation:'+slot['id'],)).fetchone()
                if prior:
                    previous = json.loads(db.execute('SELECT body FROM evidence WHERE id=?', (prior[0],)).fetchone()[0])
                    prior_measure = json.loads(db.execute('SELECT body FROM evidence WHERE id=?',
                        (previous['measured_ref'],)).fetchone()[0])['metrics'][metric]
                    if prior_measure['observed_at'] > observation['observed_at']:
                        continue
                    if not prior_measure.get('censored', False) and censored:
                        continue
                db.execute('INSERT OR REPLACE INTO credits VALUES (?,?,?,?)',
                    ('validation:'+slot['id'], 'validation', value, evidence_id))

    def accept(self, obligation_id, result_ref):
        # Called only after the owning parser checks the frozen accomplishment
        # predicate against bytes from the authenticated physical attempt.
        value = self.commission['obligations'][obligation_id]['credit']
        with self.connection() as db:
            db.execute('INSERT OR IGNORE INTO credits VALUES (?,?,?,?)',
                       ('actual:'+obligation_id, 'actual', value, result_ref))

    def credit_view(self):
        with self.connection() as db:
            rows = db.execute('SELECT slot,kind,value,evidence_id FROM credits ORDER BY slot').fetchall()
        components = {kind: sum(row[2] for row in rows if row[1] == kind)
                      for kind in ('actual', 'model', 'validation')}
        return {'credit': sum(components.values()), 'components': components,
                'contributions': [dict(zip(('slot', 'kind', 'credit', 'evidence_id'), row)) for row in rows]}
