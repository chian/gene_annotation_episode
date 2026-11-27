"""The system's own tables in the run's Store file: which journal owns a run id, and what each Episode's units
produced.

Built by the runner; never given to episodes or to the library.

**Run claims** (``episode_runs``). A run id is unique within one journal, and work-table rows, operation keys and
interpretation accounts in the Store are keyed by it. A run therefore claims its id in the Store it writes to,
under its journal's identity; the same run id from another journal over the same Store is refused when the run is
linked (the runner raises ``LinkError``).

**Produced receipts** (``episode_produced``). The receipt of a record a unit wrote is written here, on the Store's
own connection and in the transaction that wrote the record, so the record and its receipt commit or roll back
together. The run journal's copy is written after the commit; when a process is cut between the two, the journal
copy is written from this table the next time the Episode is built (``recording.Custody``). The receipts of the
three passes between Episodes (entry, commissioned, returned) are only in the journal: they write nothing to the
Store.

**Feature changes** (``episode_feature_changes``). Each change of a feature record in place (``changed``) is written
here in the transaction that made it: the unit, the record, and its data before and after.

**Unfinished units.** ``abandon_unfinished`` marks, in one Store transaction, what an Episode's units from a
position on produced as abandoned, puts back the feature records they changed and takes back their work-table row
writes (``work_tables.WorkRows``). It then
removes the scratch directories a cut process left for the Episode (``scratch.ScratchRoot``): no unit of an Episode
that is being built is running, so nothing of its scratch is in use.
"""
from __future__ import annotations

import json

from method_loop.jsonvalue import canonical

from .scratch import ScratchRoot

_SCHEMA = """
CREATE TABLE IF NOT EXISTS episode_runs(run_id TEXT PRIMARY KEY, journal_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS episode_produced(run_id TEXT NOT NULL, holder TEXT NOT NULL, record_ref TEXT NOT NULL,
    unit INTEGER NOT NULL, abandoned INTEGER NOT NULL, PRIMARY KEY(run_id, holder, record_ref));
CREATE TABLE IF NOT EXISTS episode_feature_changes(run_id TEXT NOT NULL, holder TEXT NOT NULL, unit INTEGER NOT NULL,
    record_ref TEXT NOT NULL, before TEXT NOT NULL, after TEXT NOT NULL, abandoned INTEGER NOT NULL);
"""


def _path(path):
    return canonical([list(part) for part in path])


class StoreLedger:
    """Run claims and produced receipts in one Store's SQLite file (see the module docstring)."""

    def __init__(self, store, rows):
        self._store, self._db, self._rows = store, store._db, rows
        self._scratch = ScratchRoot(store)
        self._db.executescript(_SCHEMA)

    def claim_run(self, run_id, journal_id):
        """Claim ``run_id`` in this Store for the journal ``journal_id``. False when another journal holds it."""
        self._db.execute('INSERT OR IGNORE INTO episode_runs VALUES(?,?)', (run_id, journal_id))
        owner = self._db.execute('SELECT journal_id FROM episode_runs WHERE run_id=?', (run_id,)).fetchone()[0]
        return owner == journal_id

    def produced(self, run_id, holder, ref, unit):
        """``holder`` produced ``ref`` at ``unit``; called inside the Store transaction that wrote ``ref``."""
        self._db.execute(
            'INSERT INTO episode_produced VALUES(?,?,?,?,0) ON CONFLICT(run_id, holder, record_ref) '
            'DO UPDATE SET unit=excluded.unit, abandoned=0', (run_id, _path(holder), ref, unit))

    def changed(self, run_id, holder, ref, unit, before, after):
        """``holder`` changed the feature record ``ref`` at ``unit`` from ``before`` to ``after``; called inside the
        Store transaction that changed it."""
        self._db.execute('INSERT INTO episode_feature_changes VALUES(?,?,?,?,?,?,0)',
                         (run_id, _path(holder), unit, ref, canonical(before), canonical(after)))

    def feature_changes(self, ref):
        """Every change of the feature record ``ref``, in order: ``{'run_id', 'holder', 'unit', 'before', 'after',
        'abandoned'}``; an abandoned change was put back."""
        return [{'run_id': row[0], 'holder': json.loads(row[1]), 'unit': row[2], 'before': json.loads(row[3]),
                 'after': json.loads(row[4]), 'abandoned': bool(row[5])} for row in self._db.execute(
                     'SELECT run_id, holder, unit, before, after, abandoned FROM episode_feature_changes '
                     'WHERE record_ref=? ORDER BY rowid', (ref,)).fetchall()]

    def receipts(self, run_id, holder):
        """``(ref, unit, abandoned)`` of everything ``holder``'s units produced, in order."""
        return [(row[0], row[1], bool(row[2])) for row in self._db.execute(
            'SELECT record_ref, unit, abandoned FROM episode_produced WHERE run_id=? AND holder=? ORDER BY rowid',
            (run_id, _path(holder))).fetchall()]

    def abandon_unfinished(self, run_id, holder, owner, position):
        """What ``holder``'s units from ``position`` on produced is abandoned, the feature records they changed are
        put back field by field (a field changed again since is left), and their row writes are taken back; ``owner`` is the Episode's ``(run_id,
        episode_id)``, the key of its rows and of its scratch directories, which are removed."""
        with self._store.transaction():
            self._db.execute('UPDATE episode_produced SET abandoned=1 WHERE run_id=? AND holder=? AND unit>=? '
                             'AND abandoned=0', (run_id, _path(holder), position))
            for ref, before, after in self._db.execute(
                    'SELECT record_ref, before, after FROM episode_feature_changes WHERE run_id=? AND holder=? '
                    'AND unit>=? AND abandoned=0 ORDER BY rowid DESC', (run_id, _path(holder), position)).fetchall():
                before, after, current = json.loads(before), json.loads(after), self._store.get(ref)
                # a field another holder changed since keeps that later change
                self._store.change_feature(ref, {key: before.get(key) for key in {*before, *after}
                                                 if before.get(key) != after.get(key)
                                                 and current.get(key) == after.get(key)})
            self._db.execute('UPDATE episode_feature_changes SET abandoned=1 WHERE run_id=? AND holder=? AND unit>=? '
                             'AND abandoned=0', (run_id, _path(holder), position))
            self._rows.abandon_unfinished(owner, position)
        self._scratch.clear(owner)

    def abandoned_rows(self, owner, unit):
        return self._rows.abandoned(owner, unit)

    def write_abandoned_row(self, owner, unit, ref, operation_key):
        return self._rows.write_abandoned(owner, unit, ref, operation_key)


__all__ = ['StoreLedger']
