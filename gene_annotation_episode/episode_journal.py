"""Durable episode journal, sharing the authoritative Store transaction."""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time

from . import execution_timing
from .journal_metadata import pack_request
from method_loop.durable import canonical


class WorkflowError(RuntimeError):
    """Operational interruption; it does not imply scientific saturation."""


def _digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


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
        self.store, self.db, self.run_id = store, store.db, run_id
        schema = """
        CREATE TABLE IF NOT EXISTS runtime_runs (
          run_id TEXT PRIMARY KEY, settings TEXT NOT NULL, state TEXT NOT NULL,
          summary TEXT, started_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS runtime_episodes (
          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, path TEXT NOT NULL,
          request TEXT NOT NULL, initial_credit ANY NOT NULL, state TEXT NOT NULL,
          completion TEXT, archive TEXT, PRIMARY KEY(run_id,episode_id));
        CREATE TABLE IF NOT EXISTS runtime_model_calls (
          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, call_index INTEGER NOT NULL,
          purpose TEXT NOT NULL, request TEXT NOT NULL, response TEXT, timing TEXT,
          PRIMARY KEY(run_id,episode_id,call_index));
        CREATE TABLE IF NOT EXISTS runtime_actions (
          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, decision_index INTEGER NOT NULL,
          action TEXT NOT NULL, result TEXT, credit ANY, timing TEXT,
          PRIMARY KEY(run_id,episode_id,decision_index));
        CREATE TABLE IF NOT EXISTS runtime_observations (
          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, unit_index INTEGER NOT NULL,
          observation TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,unit_index));
        CREATE TABLE IF NOT EXISTS runtime_forms (
          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, facts TEXT NOT NULL,
          form TEXT, PRIMARY KEY(run_id,episode_id));
        CREATE TABLE IF NOT EXISTS runtime_report_attempts (
          run_id TEXT NOT NULL, parent_episode_id TEXT NOT NULL,
          decision_index INTEGER NOT NULL, delivery_ref TEXT NOT NULL,
          child_episode_id TEXT NOT NULL, contract TEXT NOT NULL,
          form TEXT, failure TEXT, timing_receipts TEXT, report_contract_declaration TEXT,
          PRIMARY KEY(run_id,parent_episode_id,decision_index));
        CREATE TABLE IF NOT EXISTS runtime_estimation_contexts (
          run_id TEXT NOT NULL, episode_id TEXT NOT NULL, decision_index INTEGER NOT NULL,
          data TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,decision_index));
        CREATE TABLE IF NOT EXISTS runtime_timed_commissions (
          run_id TEXT NOT NULL, parent_episode_id TEXT NOT NULL, decision_index INTEGER NOT NULL,
          selection_digest TEXT NOT NULL, child_episode_id TEXT NOT NULL,
          scheduled_at REAL NOT NULL, due_at REAL NOT NULL, fired_at REAL, returned_at REAL,
          PRIMARY KEY(run_id,parent_episode_id,decision_index));
        """
        with self.store.transaction():
            for statement in schema.split(";"):
                if statement.strip():
                    self.db.execute(statement)
            # Declare the native scalar-or-collection storage type explicitly.
            # Existing scalar values retain their SQLite numeric type and all
            # original action identities. No replacement score is introduced.
            for table, column in (('runtime_episodes', 'initial_credit'), ('runtime_actions', 'credit')):
                columns = list(self.db.execute('PRAGMA table_info(' + table + ')'))
                if next(row[2] for row in columns if row[1] == column) == 'REAL':
                    declaration = next(statement.strip() for statement in schema.split(';')
                        if 'CREATE TABLE IF NOT EXISTS ' + table + ' (' in statement)
                    temporary = table + '_credit_migration'
                    self.db.execute(declaration.replace('IF NOT EXISTS ' + table, temporary))
                    names = ','.join(row[1] for row in columns)
                    self.db.execute(f'INSERT INTO {temporary} ({names}) SELECT {names} FROM {table}')
                    self.db.execute('DROP TABLE ' + table)
                    self.db.execute(f'ALTER TABLE {temporary} RENAME TO {table}')
            if 'timing_receipts' not in {row[1] for row in self.db.execute('PRAGMA table_info(runtime_report_attempts)')}:
                self.db.execute('ALTER TABLE runtime_report_attempts ADD COLUMN timing_receipts TEXT')
            if 'report_contract_declaration' not in {row[1] for row in self.db.execute('PRAGMA table_info(runtime_report_attempts)')}:
                self.db.execute('ALTER TABLE runtime_report_attempts ADD COLUMN report_contract_declaration TEXT')

    def row(self, table, episode_id=None, index=None):
        keys, args = ["run_id=?"], [self.run_id]
        if episode_id is not None:
            keys.append("episode_id=?"); args.append(episode_id)
        if index is not None:
            name = {"runtime_model_calls": "call_index", "runtime_actions": "decision_index",
                    "runtime_observations": "unit_index"}[table]
            keys.append(name + "=?"); args.append(index)
        row = self.db.execute(f"SELECT * FROM {table} WHERE " + " AND ".join(keys), args).fetchone()
        if row is None:
            return None
        result = dict(row)
        for name in ('initial_credit', 'credit'):
            if name in result:
                result[name] = decode_credit(result[name])
        return result

    def save(self, table, values):
        values = {"run_id": self.run_id, **values}
        for name in ('initial_credit', 'credit'):
            if name in values and values[name] is not None:
                values[name] = encode_credit(values[name])
        if table=='runtime_model_calls' and values.get('request') is not None:
            values['request']=self.pack_request(values['request'])
        columns = list(values)
        # An outcome update must not replace independently recorded timing.
        # Upsert only supplied fields instead of deleting/recreating the row.
        self.db.execute(f"INSERT INTO {table} ({','.join(columns)}) "
                        f"VALUES ({','.join('?' for _ in columns)}) ON CONFLICT DO UPDATE SET "
                        + ','.join(f'{name}=excluded.{name}' for name in columns), list(values.values()))

    def pack_request(self,text):
        return pack_request(self.store,text)

    def measure(self, table, episode_id, index):
        column = {"runtime_model_calls": "call_index", "runtime_actions": "decision_index"}[table]
        key = (self.run_id, episode_id, index)
        def read():
            row = self.db.execute(f"SELECT timing FROM {table} WHERE run_id=? AND episode_id=? AND {column}=?", key).fetchone()
            if row is None:
                raise WorkflowError("timing_requires_recorded_work")
            return row[0]
        def write(timing):
            self.db.execute(f"UPDATE {table} SET timing=? WHERE run_id=? AND episode_id=? AND {column}=?", (timing, *key))
        return execution_timing.measure(read, write)

    def schedule_child(self, parent_id, index, selection, child_id):
        """Persist one exact parent choice, not a policy for future choices."""
        key = (self.run_id, parent_id, index)
        digest = _digest(selection)
        with self.store.transaction():
            row = self.db.execute('SELECT * FROM runtime_timed_commissions WHERE run_id=? '
                'AND parent_episode_id=? AND decision_index=?', key).fetchone()
            if row is not None:
                if row['selection_digest'] != digest or row['child_episode_id'] != child_id:
                    raise WorkflowError('timed_commission_assignment_conflict')
                return
            scheduled = time.time()
            due = scheduled + selection['delay_seconds']
            if not math.isfinite(due):
                raise ValueError('finite_commission_time_required')
            self.db.execute('INSERT INTO runtime_timed_commissions VALUES(?,?,?,?,?,?,?,NULL,NULL)',
                            (*key, digest, child_id, scheduled, due))

    async def await_child_commission(self, parent_id, index):
        key = (self.run_id, parent_id, index)
        row = self.db.execute('SELECT due_at,fired_at FROM runtime_timed_commissions WHERE run_id=? '
            'AND parent_episode_id=? AND decision_index=?', key).fetchone()
        if row['fired_at'] is not None:
            return
        # Infrastructure timer waiting, not another episode loop or observation.
        while True:
            remaining = row['due_at'] - time.time()
            if remaining <= 0:
                break
            await asyncio.sleep(remaining)
        self.db.execute('UPDATE runtime_timed_commissions SET fired_at=? WHERE run_id=? '
                        'AND parent_episode_id=? AND decision_index=? AND fired_at IS NULL', (time.time(), *key))

    def commission_returned(self, parent_id, index):
        self.db.execute('UPDATE runtime_timed_commissions SET returned_at=? WHERE run_id=? '
            'AND parent_episode_id=? AND decision_index=? AND returned_at IS NULL',
            (time.time(), self.run_id, parent_id, index))

    def elapsed_view(self, episode_id):
        """Compact own-Episode facts, without reading archived work payloads."""
        result = {"version": execution_timing.VERSION, "time_unit": "seconds",
                  "credit_or_controller_effect": "none", "includes_child_wait": True,
                  "sum_across_episode_levels_is_compute_consumption": False}
        for name, table, index in (("decision_calls", "runtime_model_calls", "call_index"),
                                    ("selected_work", "runtime_actions", "decision_index")):
            row = self.db.execute(f"SELECT count(*) AS total, count(timing) AS measured, "
                "coalesce(sum(json_extract(timing,'$.measured_elapsed_seconds')),0) AS elapsed, "
                "coalesce(sum(json_extract(timing,'$.unmeasured_ended_intervals')),0) AS unknown "
                f"FROM {table} WHERE run_id=? AND episode_id=?", (self.run_id, episode_id)).fetchone()
            latest = self.db.execute(f"SELECT {index},timing FROM {table} WHERE run_id=? AND episode_id=? "
                f"ORDER BY {index} DESC LIMIT 1", (self.run_id, episode_id)).fetchone()
            # An interrupted owner may never have written an interval end, even
            # when that row is no longer the newest record. Count only those
            # unresolved spans, reading compact owner identities rather than
            # materializing historical requests/results or all timing arrays.
            dangling = self.db.execute(
                "SELECT json_extract(timing,'$.intervals[#-1].owner') AS owner "
                f"FROM {table} WHERE run_id=? AND episode_id=? "
                "AND json_extract(timing,'$.intervals[#-1].state')='running'",
                (self.run_id, episode_id))
            lost = sum(not execution_timing.owner_is_live(json.loads(item[0]) if item[0] else None)
                       for item in dangling)
            result[name] = {"records": row["total"], "records_with_timing": row["measured"],
                "records_without_timing": row["total"]-row["measured"],
                "measured_elapsed_seconds": row["elapsed"], "unmeasured_ended_intervals": row["unknown"]+lost,
                "latest": {"decision_index": latest[0], "timing": execution_timing.snapshot(latest[1])} if latest else None}
        return result


