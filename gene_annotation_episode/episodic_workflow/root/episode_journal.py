"""Durable episode journal, sharing the authoritative Store transaction."""
from __future__ import annotations
import asyncio
import hashlib
import json
import math
import time
from . import execution_timing
from gene_annotation_episode.journal_metadata import pack_request
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical

class WorkflowError(RuntimeError):
    """Operational interruption; it does not imply scientific saturation."""

def _digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()

def decode_credit(value):
    """Scalar REAL or the explicitly serialized collection in an ANY column."""
    return json.loads(value) if isinstance(value, str) else value

def encode_credit(value):
    from .numerical import validate_task_credit
    validated = validate_task_credit(value)
    return canonical(validated) if isinstance(validated, dict) else validated

class Journal:
    """Durable local runtime state in the same database as biological records."""

    def __init__(self, store, run_id):
        self.store, self.db, self.run_id = (store, store.db, run_id)
        schema = '\n        CREATE TABLE IF NOT EXISTS runtime_runs (\n          run_id TEXT PRIMARY KEY, settings TEXT NOT NULL, state TEXT NOT NULL,\n          summary TEXT, started_at TEXT NOT NULL, updated_at TEXT NOT NULL);\n        CREATE TABLE IF NOT EXISTS runtime_episodes (\n          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, path TEXT NOT NULL,\n          request TEXT NOT NULL, initial_credit ANY NOT NULL, state TEXT NOT NULL,\n          completion TEXT, archive TEXT, PRIMARY KEY(run_id,episode_id));\n        CREATE TABLE IF NOT EXISTS runtime_model_calls (\n          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, call_index INTEGER NOT NULL,\n          purpose TEXT NOT NULL, request TEXT NOT NULL, response TEXT, timing TEXT,\n          PRIMARY KEY(run_id,episode_id,call_index));\n        CREATE TABLE IF NOT EXISTS runtime_actions (\n          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, decision_index INTEGER NOT NULL,\n          action TEXT NOT NULL, result TEXT, credit ANY, timing TEXT,\n          PRIMARY KEY(run_id,episode_id,decision_index));\n        CREATE TABLE IF NOT EXISTS runtime_observations (\n          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, unit_index INTEGER NOT NULL,\n          observation TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,unit_index));\n        CREATE TABLE IF NOT EXISTS runtime_forms (\n          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, facts TEXT NOT NULL,\n          form TEXT, PRIMARY KEY(run_id,episode_id));\n        CREATE TABLE IF NOT EXISTS runtime_report_attempts (\n          run_id TEXT NOT NULL, parent_episode_id TEXT NOT NULL,\n          decision_index INTEGER NOT NULL, delivery_ref TEXT NOT NULL,\n          child_episode_id TEXT NOT NULL, contract TEXT NOT NULL,\n          form TEXT, failure TEXT, timing_receipts TEXT, report_contract_declaration TEXT,\n          PRIMARY KEY(run_id,parent_episode_id,decision_index));\n        CREATE TABLE IF NOT EXISTS runtime_estimation_contexts (\n          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, decision_index INTEGER NOT NULL,\n          data TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,decision_index));\n        CREATE TABLE IF NOT EXISTS runtime_timed_commissions (\n          run_id TEXT NOT NULL, parent_episode_id TEXT NOT NULL, decision_index INTEGER NOT NULL,\n          selection_digest TEXT NOT NULL, child_episode_id TEXT NOT NULL,\n          scheduled_at REAL NOT NULL, due_at REAL NOT NULL, fired_at REAL, returned_at REAL,\n          PRIMARY KEY(run_id,parent_episode_id,decision_index));\n        '
        with self.store.transaction():
            for statement in schema.split(';'):
                if statement.strip():
                    self.db.execute(statement)

    def row(self, table, episode_id=None, index=None):
        keys, args = (['run_id=?'], [self.run_id])
        if episode_id is not None:
            keys.append('episode_id=?')
            args.append(episode_id)
        if index is not None:
            name = {'runtime_model_calls': 'call_index', 'runtime_actions': 'decision_index', 'runtime_observations': 'unit_index'}[table]
            keys.append(name + '=?')
            args.append(index)
        row = self.db.execute(f'SELECT * FROM {table} WHERE ' + ' AND '.join(keys), args).fetchone()
        if row is None:
            return None
        result = dict(row)
        for name in ('initial_credit', 'credit'):
            if name in result:
                result[name] = decode_credit(result[name])
        return result

    def save(self, table, values):
        values = {'run_id': self.run_id, **values}
        for name in ('initial_credit', 'credit'):
            if name in values and values[name] is not None:
                values[name] = encode_credit(values[name])
        if table == 'runtime_model_calls' and values.get('request') is not None:
            values['request'] = self.pack_request(values['request'])
        columns = list(values)
        self.db.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join(('?' for _ in columns))}) ON CONFLICT DO UPDATE SET " + ','.join((f'{name}=excluded.{name}' for name in columns)), list(values.values()))

    def pack_request(self, text):
        return pack_request(self.store, text)

    def measure(self, table, episode_id, index):
        column = {'runtime_model_calls': 'call_index', 'runtime_actions': 'decision_index'}[table]
        key = (self.run_id, episode_id, index)

        def read():
            row = self.db.execute(f'SELECT timing FROM {table} WHERE run_id=? AND episode_id=? AND {column}=?', key).fetchone()
            if row is None:
                raise WorkflowError('timing_requires_recorded_work')
            return row[0]

        def write(timing):
            self.db.execute(f'UPDATE {table} SET timing=? WHERE run_id=? AND episode_id=? AND {column}=?', (timing, *key))
        return execution_timing.measure(read, write)

    def schedule_child(self, parent_id, index, selection, child_id):
        """Persist one exact parent choice, not a policy for future choices."""
        key = (self.run_id, parent_id, index)
        digest = _digest(selection)
        with self.store.transaction():
            row = self.db.execute('SELECT * FROM runtime_timed_commissions WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key).fetchone()
            if row is not None:
                if row['selection_digest'] != digest or row['child_episode_id'] != child_id:
                    raise WorkflowError('timed_commission_assignment_conflict')
                return
            scheduled = time.time()
            due = scheduled + selection['delay_seconds']
            if not math.isfinite(due):
                raise ValueError('finite_commission_time_required')
            self.db.execute('INSERT INTO runtime_timed_commissions VALUES(?,?,?,?,?,?,?,NULL,NULL)', (*key, digest, child_id, scheduled, due))

    async def await_child_commission(self, parent_id, index):
        key = (self.run_id, parent_id, index)
        row = self.db.execute('SELECT due_at,fired_at FROM runtime_timed_commissions WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key).fetchone()
        if row['fired_at'] is not None:
            return
        while True:
            remaining = row['due_at'] - time.time()
            if remaining <= 0:
                break
            await asyncio.sleep(remaining)
        self.db.execute('UPDATE runtime_timed_commissions SET fired_at=? WHERE run_id=? AND parent_episode_id=? AND decision_index=? AND fired_at IS NULL', (time.time(), *key))

    def commission_returned(self, parent_id, index):
        self.db.execute('UPDATE runtime_timed_commissions SET returned_at=? WHERE run_id=? AND parent_episode_id=? AND decision_index=? AND returned_at IS NULL', (time.time(), self.run_id, parent_id, index))

    def elapsed_view(self, episode_id):
        """Compact own-Episode facts, without reading archived work payloads."""
        result = {'version': execution_timing.VERSION, 'time_unit': 'seconds', 'credit_or_controller_effect': 'none', 'includes_child_wait': True, 'sum_across_episode_levels_is_compute_consumption': False}
        for name, table, index in (('decision_calls', 'runtime_model_calls', 'call_index'), ('selected_work', 'runtime_actions', 'decision_index')):
            row = self.db.execute(f"SELECT count(*) AS total, count(timing) AS measured, coalesce(sum(json_extract(timing,'$.measured_elapsed_seconds')),0) AS elapsed, coalesce(sum(json_extract(timing,'$.unmeasured_ended_intervals')),0) AS unknown FROM {table} WHERE run_id=? AND episode_id=?", (self.run_id, episode_id)).fetchone()
            latest = self.db.execute(f'SELECT {index},timing FROM {table} WHERE run_id=? AND episode_id=? ORDER BY {index} DESC LIMIT 1', (self.run_id, episode_id)).fetchone()
            dangling = self.db.execute(f"SELECT json_extract(timing,'$.intervals[#-1].owner') AS owner FROM {table} WHERE run_id=? AND episode_id=? AND json_extract(timing,'$.intervals[#-1].state')='running'", (self.run_id, episode_id))
            lost = sum((not execution_timing.owner_is_live(json.loads(item[0]) if item[0] else None) for item in dangling))
            result[name] = {'records': row['total'], 'records_with_timing': row['measured'], 'records_without_timing': row['total'] - row['measured'], 'measured_elapsed_seconds': row['elapsed'], 'unmeasured_ended_intervals': row['unknown'] + lost, 'latest': {'decision_index': latest[0], 'timing': execution_timing.snapshot(latest[1])} if latest else None}
        return result
