"""Durable record of one run, so it can be resumed without repeating work.

The runner writes everything here itself; no episode reads or writes the journal. For each run it records
the run's entry (including any scoped ancestors), the continuation settings and
declared services of each binding, each Episode's commission (request, assignment, selection) and the credit its
yield controller was built from (its initial credit), each unit that
began (label, operation key, digest of its arguments, how often it began), each completed unit's label,
controller input, controller step, outcome and update, each model call (request and response), each record
receipt (custody) and each receipt an abandoned attempt left, each service the run built, each value a decision
read from a service, each Episode's closure (how it ended, its units and its credit) and result, and the runner's
own clock points. On resume
the runner re-links the same entry, rejects any rebuilt commission, setting, service declaration, unit or model
request that differs from its record, builds each Episode's yield controller from its recorded initial credit,
replays recorded units with their outcomes through the method loop's
``resume_units`` (completed child Episodes are therefore not rebuilt), returns recorded model responses instead
of asking again, and reloads every receipt.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import uuid

from method_loop.jsonvalue import canonical, same_json


def same_record(recorded, value):
    """Whether a recorded canonical JSON text holds ``value``.

    Values are compared as decoded JSON, not as text, so a number recorded as
    ``6`` equals a rebuilt ``6.0`` (and ``6.0`` equals ``6``). Booleans never
    equal numbers, and every other difference still disagrees.
    """
    return same_json(json.loads(recorded), json.loads(canonical(value)))


class JournalError(RuntimeError):
    """The recorded run and the current reconstruction disagree."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS journal(identity TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, entry TEXT NOT NULL, state TEXT NOT NULL,
    result TEXT, failure TEXT);
CREATE TABLE IF NOT EXISTS episodes(run_id TEXT NOT NULL, path TEXT NOT NULL, binding_path TEXT NOT NULL,
    commission TEXT NOT NULL, initial_credit TEXT, state TEXT NOT NULL, completion TEXT, result TEXT,
    PRIMARY KEY(run_id, path));
CREATE TABLE IF NOT EXISTS units(run_id TEXT NOT NULL, path TEXT NOT NULL, unit_index INTEGER NOT NULL,
    label TEXT NOT NULL, controller_input TEXT NOT NULL, outcome TEXT NOT NULL, episode_update TEXT,
    controller_step TEXT NOT NULL, PRIMARY KEY(run_id, path, unit_index));
CREATE TABLE IF NOT EXISTS attempts(run_id TEXT NOT NULL, path TEXT NOT NULL, unit_index INTEGER NOT NULL,
    label TEXT NOT NULL, operation_key TEXT NOT NULL, arguments_digest TEXT NOT NULL, state TEXT NOT NULL,
    begun INTEGER NOT NULL, PRIMARY KEY(run_id, path, unit_index));
CREATE TABLE IF NOT EXISTS parent_inputs(run_id TEXT NOT NULL, path TEXT NOT NULL, digest TEXT NOT NULL,
    PRIMARY KEY(run_id, path));
CREATE TABLE IF NOT EXISTS settings(run_id TEXT NOT NULL, binding_path TEXT NOT NULL, value TEXT NOT NULL,
    PRIMARY KEY(run_id, binding_path));
CREATE TABLE IF NOT EXISTS services(run_id TEXT NOT NULL, binding_path TEXT NOT NULL, names TEXT NOT NULL,
    PRIMARY KEY(run_id, binding_path));
CREATE TABLE IF NOT EXISTS service_builds(run_id TEXT NOT NULL, name TEXT NOT NULL, path TEXT NOT NULL,
    unit_index INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS service_reads(run_id TEXT NOT NULL, path TEXT NOT NULL, position INTEGER NOT NULL,
    request TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(run_id, path, position, request));
CREATE TABLE IF NOT EXISTS model_calls(run_id TEXT NOT NULL, path TEXT NOT NULL, position INTEGER NOT NULL,
    call_index INTEGER NOT NULL, request TEXT NOT NULL, response TEXT NOT NULL,
    PRIMARY KEY(run_id, path, position, call_index));
CREATE TABLE IF NOT EXISTS receipts(run_id TEXT NOT NULL, holder TEXT NOT NULL, record_ref TEXT NOT NULL,
    how TEXT NOT NULL, from_path TEXT, unit INTEGER, producer TEXT, producer_unit INTEGER,
    PRIMARY KEY(run_id, holder, record_ref));
CREATE TABLE IF NOT EXISTS abandoned_receipts(run_id TEXT NOT NULL, holder TEXT NOT NULL, unit INTEGER NOT NULL,
    record_ref TEXT NOT NULL, PRIMARY KEY(run_id, holder, unit, record_ref));
CREATE TABLE IF NOT EXISTS progress_points(run_id TEXT NOT NULL, path TEXT NOT NULL, name TEXT NOT NULL,
    value TEXT NOT NULL, PRIMARY KEY(run_id, path, name));
"""


def _path(path):
    return canonical([list(part) for part in path])


def _unpath(text):
    return None if text is None else tuple(tuple(part) for part in json.loads(text))


class RunJournal:
    """One SQLite file holding the durable records of the runs written to it."""

    def __init__(self, path):
        self.path = Path(path)
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self.db.executescript(_SCHEMA)
        # The journal's own identity, made once with the file: a run id is unique within one journal, and the
        # Store a run writes to records which journal owns that run id (``store_ledger.StoreLedger.claim_run``).
        self.db.execute('INSERT INTO journal SELECT ? WHERE NOT EXISTS (SELECT 1 FROM journal)',
                        ('journal_' + uuid.uuid4().hex,))
        self.identity = self.db.execute('SELECT identity FROM journal').fetchone()[0]

    # -- runs -----------------------------------------------------------------
    def open_run(self, run_id, entry):
        if self.db.execute('SELECT 1 FROM runs WHERE run_id=?', (run_id,)).fetchone() is not None:
            raise JournalError('run_already_recorded:' + run_id)
        self.db.execute('INSERT INTO runs VALUES(?,?,?,NULL,NULL)', (run_id, canonical(entry), 'active'))

    def entry(self, run_id):
        row = self.db.execute('SELECT entry FROM runs WHERE run_id=?', (run_id,)).fetchone()
        if row is None:
            raise JournalError('run_not_recorded:' + run_id)
        return json.loads(row[0])

    def close_run(self, run_id, result):
        row = self.db.execute('SELECT state, result FROM runs WHERE run_id=?', (run_id,)).fetchone()
        if row[0] == 'closed':
            if not same_record(row[1], result):
                raise JournalError('recorded_run_result_differs:' + run_id)
            return
        self.db.execute("UPDATE runs SET state='closed', result=? WHERE run_id=?", (canonical(result), run_id))

    def record_run_failure(self, run_id, failure):
        """Record the error that ended a recorded run before it closed. Nothing closes such a run, so its state
        stays ``active``; whether a resume gets further depends on the error (an interruption does, a wrong
        commission raises the same error again)."""
        self.db.execute('UPDATE runs SET failure=? WHERE run_id=?', (failure, run_id))

    def run_failure(self, run_id):
        return self.db.execute('SELECT failure FROM runs WHERE run_id=?', (run_id,)).fetchone()[0]

    def run_state(self, run_id):
        row = self.db.execute('SELECT state, result FROM runs WHERE run_id=?', (run_id,)).fetchone()
        if row is None:
            raise JournalError('run_not_recorded:' + run_id)
        return row[0], None if row[1] is None else json.loads(row[1])

    # -- episodes -------------------------------------------------------------
    def open_episode(self, run_id, path, binding_path, commission):
        """Record a new Episode's commission, or check a rebuilt one against its record."""
        row = self.db.execute('SELECT binding_path, commission FROM episodes WHERE run_id=? AND path=?',
                              (run_id, _path(path))).fetchone()
        if row is None:
            self.db.execute('INSERT INTO episodes VALUES(?,?,?,?,NULL,?,NULL,NULL)',
                            (run_id, _path(path), binding_path, canonical(commission), 'active'))
            return False
        if row[0] != binding_path or not same_record(row[1], commission):
            raise JournalError('reconstructed_episode_differs_from_record:' + _path(path))
        return True

    def initial_credit(self, run_id, path, compute):
        """The credit the yield controller of the Episode at ``path`` is built from: the value recorded when the
        Episode was first entered, or ``compute()`` recorded now. It is computed once. An Episode that is entered
        again (a resumed run) holds by then what its recorded units produced, so ``credit`` of its summary before
        any unit would no longer say what its controller started from."""
        select, where = 'SELECT initial_credit FROM episodes WHERE run_id=? AND path=?', (run_id, _path(path))
        if self.db.execute(select, where).fetchone()[0] is None:
            self.db.execute('UPDATE episodes SET initial_credit=? WHERE run_id=? AND path=?',
                            (canonical(compute()), *where))
        return json.loads(self.db.execute(select, where).fetchone()[0])

    def close_episode(self, run_id, path, completion):
        """Record how an Episode ended: ``{'ended_by', 'units', 'credit'}`` (``credit`` is the cumulative credit
        its yield controller last saw)."""
        row = self.db.execute('SELECT state, completion FROM episodes WHERE run_id=? AND path=?',
                              (run_id, _path(path))).fetchone()
        if row[0] == 'closed':
            if not same_record(row[1], completion):
                raise JournalError('recorded_episode_completion_differs:' + _path(path))
            return
        self.db.execute("UPDATE episodes SET state='closed', completion=? WHERE run_id=? AND path=?",
                        (canonical(completion), run_id, _path(path)))

    def record_result(self, run_id, path, result):
        row = self.db.execute('SELECT result FROM episodes WHERE run_id=? AND path=?',
                              (run_id, _path(path))).fetchone()
        if row[0] is not None and not same_record(row[0], result):
            raise JournalError('recorded_episode_result_differs:' + _path(path))
        self.db.execute('UPDATE episodes SET result=? WHERE run_id=? AND path=?',
                        (canonical(result), run_id, _path(path)))

    def episodes(self, run_id):
        """Each Episode of the run, in the order they were built: ``{'path', 'binding_path', 'state',
        'initial_credit', 'completion'}`` (``initial_credit`` is ``None`` until the Episode is first entered,
        ``completion`` until it is closed)."""
        return [{'path': json.loads(row[0]), 'binding_path': row[1], 'state': row[2],
                 'initial_credit': None if row[3] is None else json.loads(row[3]),
                 'completion': None if row[4] is None else json.loads(row[4])}
                for row in self.db.execute('SELECT path, binding_path, state, initial_credit, completion FROM '
                                           'episodes WHERE run_id=? ORDER BY rowid', (run_id,))]

    # -- units ----------------------------------------------------------------
    def begin_unit(self, run_id, path, unit_index, label, operation_key, arguments_digest):
        """Journal that a unit began. True when an earlier attempt of the same unit began and did not finish
        (the unit is being run again); an earlier attempt of a different unit raises."""
        row = self.db.execute('SELECT label, operation_key, arguments_digest, state FROM attempts WHERE run_id=? '
                              'AND path=? AND unit_index=?', (run_id, _path(path), unit_index)).fetchone()
        if row is None:
            self.db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,1)',
                            (run_id, _path(path), unit_index, label, operation_key, arguments_digest, 'began'))
            return False
        if row[3] != 'began':
            raise JournalError('unit_already_finished:' + _path(path) + ':' + str(unit_index))
        if (row[0], row[1], row[2]) != (label, operation_key, arguments_digest):
            raise JournalError('abandoned_unit_differs:' + _path(path) + ':' + str(unit_index))
        self.db.execute('UPDATE attempts SET begun=begun+1 WHERE run_id=? AND path=? AND unit_index=?',
                        (run_id, _path(path), unit_index))
        return True

    def record_unit(self, run_id, path, unit_index, label, controller_input, outcome, episode_update,
                    controller_step):
        """Record a completed unit (with the controller's step for it) and mark its attempt finished, together."""
        row = self.db.execute('SELECT label, controller_input, outcome, episode_update FROM units WHERE run_id=? '
                              'AND path=? AND unit_index=?', (run_id, _path(path), unit_index)).fetchone()
        if row is not None:
            if (row[0] != label or not same_record(row[1], controller_input) or not same_record(row[2], outcome)
                    or (row[3] is None) != (episode_update is None)
                    or (episode_update is not None and not same_record(row[3], episode_update))):
                raise JournalError('recorded_unit_differs:' + _path(path) + ':' + str(unit_index))
            return
        self.db.execute('BEGIN')
        try:
            began = self.db.execute('SELECT label, state FROM attempts WHERE run_id=? AND path=? AND unit_index=?',
                                    (run_id, _path(path), unit_index)).fetchone()
            if began is None or began[0] != label or began[1] != 'began':
                raise JournalError('unit_finished_without_beginning:' + _path(path) + ':' + str(unit_index))
            self.db.execute('INSERT INTO units VALUES(?,?,?,?,?,?,?,?)', (
                run_id, _path(path), unit_index, label, canonical(controller_input), canonical(outcome),
                None if episode_update is None else canonical(episode_update), canonical(controller_step)))
            self.db.execute("UPDATE attempts SET state='finished' WHERE run_id=? AND path=? AND unit_index=?",
                            (run_id, _path(path), unit_index))
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def units(self, run_id, path):
        """``(label, controller_input, outcome, episode_update)`` of each recorded unit, in order."""
        rows = self.db.execute('SELECT unit_index, label, controller_input, outcome, episode_update FROM units '
                               'WHERE run_id=? AND path=? ORDER BY unit_index', (run_id, _path(path))).fetchall()
        if [row[0] for row in rows] != list(range(len(rows))):
            raise JournalError('recorded_units_not_contiguous:' + _path(path))
        return [(row[1], json.loads(row[2]), json.loads(row[3]), None if row[4] is None else json.loads(row[4]))
                for row in rows]

    def controller_steps(self, run_id, path):
        """The controller's recorded step for each completed unit, in order (why the Episode went on or stopped)."""
        return [json.loads(row[0]) for row in self.db.execute(
            'SELECT controller_step FROM units WHERE run_id=? AND path=? ORDER BY unit_index',
            (run_id, _path(path)))]

    def attempts(self, run_id, path):
        """``(unit_index, label, operation_key, state)`` of each unit that began, in order."""
        return [tuple(row) for row in self.db.execute(
            'SELECT unit_index, label, operation_key, state FROM attempts WHERE run_id=? AND path=? '
            'ORDER BY unit_index', (run_id, _path(path)))]

    def times_begun(self, run_id, path, unit_index):
        """How often unit ``unit_index`` began (1 unless an attempt was abandoned and the unit ran again)."""
        row = self.db.execute('SELECT begun FROM attempts WHERE run_id=? AND path=? AND unit_index=?',
                              (run_id, _path(path), unit_index)).fetchone()
        return 0 if row is None else row[0]

    # -- settings and services ------------------------------------------------------
    def record_settings(self, run_id, binding_path, settings):
        """Record the continuation settings a run uses for ``binding_path``; a recorded run must be given the
        same settings again."""
        row = self.db.execute('SELECT value FROM settings WHERE run_id=? AND binding_path=?',
                              (run_id, binding_path)).fetchone()
        if row is None:
            self.db.execute('INSERT INTO settings VALUES(?,?,?)', (run_id, binding_path, canonical(settings)))
        elif not same_record(row[0], settings):
            raise JournalError('recorded_continuation_settings_differ:' + binding_path)

    def record_services(self, run_id, binding_path, names):
        """Record the service names ``binding_path`` declares; a recorded run must be linked with the same."""
        row = self.db.execute('SELECT names FROM services WHERE run_id=? AND binding_path=?',
                              (run_id, binding_path)).fetchone()
        if row is None:
            self.db.execute('INSERT INTO services VALUES(?,?,?)', (run_id, binding_path, canonical(list(names))))
        elif json.loads(row[0]) != list(names):
            raise JournalError('recorded_services_differ:' + binding_path)

    def services(self, run_id):
        return {row[0]: json.loads(row[1]) for row in self.db.execute(
            'SELECT binding_path, names FROM services WHERE run_id=? ORDER BY binding_path', (run_id,))}

    def record_service_build(self, run_id, name, path, unit_index):
        """Record that the run built service ``name`` (its first use, by the Episode at ``path`` choosing or
        running unit ``unit_index``). A resumed run builds its services again, which adds a row."""
        self.db.execute('INSERT INTO service_builds VALUES(?,?,?,?)', (run_id, name, _path(path), unit_index))

    def service_builds(self, run_id):
        return [{'name': row[0], 'path': _unpath(row[1]), 'unit': row[2]} for row in self.db.execute(
            'SELECT name, path, unit_index FROM service_builds WHERE run_id=? ORDER BY rowid', (run_id,))]

    def service_read(self, run_id, path, position, request, ask):
        """What a decision of the Episode at ``path`` read from a service while choosing unit ``position``:
        the value recorded for ``request`` (``{'service', 'member', 'arguments'}``), or ``ask()`` recorded now.
        One value per request and unit position: a decision made again is given what it first read."""
        key = (run_id, _path(path), position, canonical(request))
        row = self.db.execute('SELECT value FROM service_reads WHERE run_id=? AND path=? AND position=? AND '
                              'request=?', key).fetchone()
        if row is None:
            value = canonical(ask())
            self.db.execute('INSERT INTO service_reads VALUES(?,?,?,?,?)', (*key, value))
            return json.loads(value)
        return json.loads(row[0])

    def service_reads(self, run_id, path):
        """``{'position', 'request', 'value'}`` of each recorded service read of the Episode, in order."""
        return [{'position': row[0], 'request': json.loads(row[1]), 'value': json.loads(row[2])}
                for row in self.db.execute('SELECT position, request, value FROM service_reads WHERE run_id=? AND '
                                           'path=? ORDER BY rowid', (run_id, _path(path)))]

    def record_parent_input(self, run_id, path, digest):
        """Record the digest of the parent input an Episode's yield controller was built from; a resumed
        Episode must rebuild the same one."""
        row = self.db.execute('SELECT digest FROM parent_inputs WHERE run_id=? AND path=?',
                              (run_id, _path(path))).fetchone()
        if row is None:
            self.db.execute('INSERT INTO parent_inputs VALUES(?,?,?)', (run_id, _path(path), digest))
        elif row[0] != digest:
            raise JournalError('recorded_parent_input_differs:' + _path(path))

    def settings(self, run_id):
        return {row[0]: json.loads(row[1]) for row in self.db.execute(
            'SELECT binding_path, value FROM settings WHERE run_id=? ORDER BY binding_path', (run_id,))}

    # -- model calls ------------------------------------------------------------
    def recorded_model_call(self, run_id, path, position, call_index, request):
        """The recorded response of this call, or ``None``; a recorded call with another request raises."""
        row = self.db.execute('SELECT request, response FROM model_calls WHERE run_id=? AND path=? AND position=? '
                              'AND call_index=?', (run_id, _path(path), position, call_index)).fetchone()
        if row is None:
            return None
        if not same_record(row[0], request):
            raise JournalError('recorded_model_call_differs:' + _path(path) + ':' + str(position) + ':'
                               + str(call_index))
        return json.loads(row[1])

    def record_model_call(self, run_id, path, position, call_index, request, response):
        self.db.execute('INSERT INTO model_calls VALUES(?,?,?,?,?,?)',
                        (run_id, _path(path), position, call_index, canonical(request), canonical(response)))
        return json.loads(canonical(response))

    def model_calls(self, run_id, path):
        rows = self.db.execute('SELECT position, call_index, request, response FROM model_calls WHERE run_id=? '
                               'AND path=? ORDER BY position, call_index', (run_id, _path(path))).fetchall()
        return [{'position': row[0], 'call_index': row[1], 'request': json.loads(row[2]),
                 'response': json.loads(row[3])} for row in rows]

    # -- receipts (custody) -------------------------------------------------------
    def record_receipt(self, run_id, holder, receipt):
        """Record that ``holder`` holds ``receipt['ref']``; the first receipt of a record stands."""
        row = self.db.execute('SELECT 1 FROM receipts WHERE run_id=? AND holder=? AND record_ref=?',
                              (run_id, _path(holder), receipt['ref'])).fetchone()
        if row is not None:
            return False
        self.db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?,?,?)', (
            run_id, _path(holder), receipt['ref'], receipt['how'],
            None if receipt['from'] is None else _path(receipt['from']), receipt['unit'],
            None if receipt['producer'] is None else _path(receipt['producer']), receipt['producer_unit']))
        return True

    def abandon_receipt(self, run_id, holder, unit, ref):
        """``holder`` produced ``ref`` at ``unit`` in an attempt that did not finish: its receipt leaves
        ``receipts`` and stays, as trace, in ``abandoned_receipts``. Doing it again changes nothing."""
        self.db.execute('BEGIN')
        try:
            self.db.execute('INSERT OR IGNORE INTO abandoned_receipts VALUES(?,?,?,?)',
                            (run_id, _path(holder), unit, ref))
            self.db.execute("DELETE FROM receipts WHERE run_id=? AND holder=? AND record_ref=? AND how='produced' "
                            "AND unit=?", (run_id, _path(holder), ref, unit))
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def drop_unfinished_returns(self, run_id, holder, position):
        """Remove the ``returned`` receipts of ``holder``'s units from ``position`` on (units that did not
        finish): the child unit runs again and its return is receipted again."""
        self.db.execute("DELETE FROM receipts WHERE run_id=? AND holder=? AND how='returned' AND unit>=?",
                        (run_id, _path(holder), position))

    def abandoned(self, run_id, holder, unit):
        """The records abandoned attempts of ``unit`` produced, in order."""
        return [row[0] for row in self.db.execute(
            'SELECT record_ref FROM abandoned_receipts WHERE run_id=? AND holder=? AND unit=? ORDER BY rowid',
            (run_id, _path(holder), unit))]

    def receipts(self, run_id, holder):
        rows = self.db.execute('SELECT record_ref, how, from_path, unit, producer, producer_unit FROM receipts '
                               'WHERE run_id=? AND holder=? ORDER BY rowid', (run_id, _path(holder))).fetchall()
        return [{'ref': row[0], 'how': row[1], 'from': _unpath(row[2]), 'to': tuple(holder), 'unit': row[3],
                 'producer': _unpath(row[4]), 'producer_unit': row[5]} for row in rows]

    # -- the runner's own named points (progress clock) ----------------------------
    def recorded_point(self, run_id, path, name):
        """The recorded value of the clock point ``name`` as ``(True, value)``, or ``(False, None)``."""
        row = self.db.execute('SELECT value FROM progress_points WHERE run_id=? AND path=? AND name=?',
                              (run_id, _path(path), name)).fetchone()
        return (False, None) if row is None else (True, json.loads(row[0]))

    def point(self, run_id, path, name, compute):
        found, value = self.recorded_point(run_id, path, name)
        if found:
            return value
        self.db.execute('INSERT INTO progress_points VALUES(?,?,?,?)', (run_id, _path(path), name, canonical(compute())))
        return self.recorded_point(run_id, path, name)[1]


class EpisodeRecorder:
    """The runner's named records for one Episode (its clock points). Not given to episodes."""

    def __init__(self, journal, run_id, path):
        self._journal, self.run_id, self.path = journal, run_id, tuple(path)

    def recorded(self, name, compute):
        """The recorded value of ``name``; computed and recorded once."""
        if type(name) is not str or not name:
            raise ValueError('record_name_required')
        return self._journal.point(self.run_id, self.path, name, compute)

    def lookup(self, name):
        """``(True, value)`` when ``name`` is recorded, else ``(False, None)``; never computes."""
        return self._journal.recorded_point(self.run_id, self.path, name)
