"""Work tables: rows of an Episode's work that a library function keeps as a table, under custody.

A support-library function that used to keep its own SQL table in the Store's file (a sheet and its cells, an
operation ledger, a projection) declares the table instead (``TableDeclaration``) and
reaches it only through the custody-scoped store: ``ctx.store.table(DECLARATION)`` in a tool,
``records.table(DECLARATION)`` in ``credit``, ``action``, ``read_from_child`` and ``internal_summary``. No
library function runs SQL.

Every row is a custody item like a Store record:

- it has a reference (``row_...``) derived from the table, the writing Episode and the row's declared key, so the
  same Episode writing the same key again writes the same row (a new revision of it);
- the system fills ``run_id``, ``episode_id``, ``unit`` and ``operation_key`` itself; a library function cannot
  write them;
- writing a row is receipted as produced by the unit (on commit, inside a transaction), and a row can be read
  only by an Episode that holds it; it is passed to a child or returned to a parent by naming its reference in a
  ``record_refs`` field, like any record;
- the references a row names in its declared ``record_refs`` columns must be readable by the writing unit;
- what a unit that did not finish wrote is taken back when the run is resumed: a row it created is removed and a
  row it rewrote is put back as it stood before the unit. The unit's rerun is told in ``ctx.abandoned`` what the
  abandoned attempt wrote (``written``) and how the row stands again (``prior``), and ``ctx.store.reclaim(ref)``
  writes the abandoned row again as the rerun's own.

The rows of every declared table live in one system table of the Store's SQLite file (``episode_work_rows``), on
the Store's own connection, so a row written inside ``ctx.store.transaction()`` commits or rolls back with the
records written beside it. The declaration of each table is recorded on first use (``episode_work_tables``); a
later use with another declaration raises.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import re

from method_loop.jsonvalue import canonical, closed_copy, content_digest, same_json

from .recording import CustodyError

ROW_PREFIX = 'row_'
SYSTEM_COLUMNS = ('id', 'record_type', 'table', 'run_id', 'episode_id', 'unit', 'operation_key', 'revision')
_NAME = re.compile(r'^[a-z][a-z0-9_]*$')
_SCHEMA = """
CREATE TABLE IF NOT EXISTS episode_work_tables(name TEXT PRIMARY KEY, declaration TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS episode_work_rows(row_ref TEXT PRIMARY KEY, table_name TEXT NOT NULL,
    run_id TEXT NOT NULL, episode_id TEXT NOT NULL, row_key TEXT NOT NULL, unit INTEGER NOT NULL,
    operation_key TEXT NOT NULL, revision INTEGER NOT NULL, data TEXT NOT NULL, prior TEXT,
    UNIQUE(table_name, run_id, episode_id, row_key));
CREATE TABLE IF NOT EXISTS episode_abandoned_rows(row_ref TEXT NOT NULL, unit INTEGER NOT NULL,
    table_name TEXT NOT NULL, run_id TEXT NOT NULL, episode_id TEXT NOT NULL, row_key TEXT NOT NULL,
    data TEXT NOT NULL, written TEXT NOT NULL, PRIMARY KEY(row_ref, unit));
"""


class WorkTableError(ValueError):
    """A work table was declared or used against its declaration."""


@dataclass(frozen=True)
class TableDeclaration:
    """One work table, declared by the library module that owns it.

    ``name`` names the table; ``columns`` are the value columns of a row (closed JSON values); ``key`` is the
    subset of columns that identifies one row among those one Episode writes; ``record_refs`` is the subset of
    columns whose value is a record reference or a list of record references."""
    name: str
    columns: tuple
    key: tuple
    record_refs: tuple = ()

    def __post_init__(self):
        if type(self.name) is not str or not _NAME.fullmatch(self.name):
            raise WorkTableError('work_table_name_must_be_a_lowercase_identifier:' + repr(self.name))
        for field in ('columns', 'key', 'record_refs'):
            value = getattr(self, field)
            if (not isinstance(value, tuple) or len(set(value)) != len(value)
                    or any(type(name) is not str or not _NAME.fullmatch(name) for name in value)):
                raise WorkTableError('work_table_' + field + '_must_be_a_tuple_of_distinct_names:' + self.name)
        if not self.columns or not self.key:
            raise WorkTableError('work_table_requires_columns_and_a_key:' + self.name)
        reserved = sorted(set(self.columns) & set(SYSTEM_COLUMNS))
        if reserved:
            raise WorkTableError('work_table_columns_are_system_columns:' + self.name + ':' + ','.join(reserved))
        outside = sorted((set(self.key) | set(self.record_refs)) - set(self.columns))
        if outside:
            raise WorkTableError('work_table_key_and_record_refs_must_be_columns:' + self.name + ':'
                                 + ','.join(outside))

    def as_record(self):
        return {'name': self.name, 'columns': list(self.columns), 'key': list(self.key),
                'record_refs': list(self.record_refs)}


def is_row_ref(ref):
    return type(ref) is str and ref.startswith(ROW_PREFIX)


class WorkRows:
    """The system table of work rows in one Store's SQLite file. Built by the runner; never given to episodes.

    Besides its values a row keeps ``prior``: the row as it stood before the unit that last wrote it first touched
    it (nothing when that unit created the row). ``abandon_unfinished`` uses it to put back what an unfinished
    unit's attempt wrote, and keeps what the attempt wrote in ``episode_abandoned_rows`` for the rerun."""

    _COLUMNS = 'row_ref, table_name, run_id, episode_id, row_key, unit, operation_key, revision, data, prior'

    def __init__(self, store):
        self._db = store.db
        self._db.executescript(_SCHEMA)
        self._declared = {}

    def declare(self, declaration):
        """Record the declaration on first use; another declaration under the same name raises."""
        if not isinstance(declaration, TableDeclaration):
            raise WorkTableError('work_table_requires_a_TableDeclaration')
        known = self._declared.get(declaration.name)
        if known is None:
            text = canonical(declaration.as_record())
            self._db.execute('INSERT OR IGNORE INTO episode_work_tables VALUES(?,?)', (declaration.name, text))
            recorded = self._db.execute('SELECT declaration FROM episode_work_tables WHERE name=?',
                                        (declaration.name,)).fetchone()[0]
            known = json.loads(recorded)
            if not self._db.in_transaction:      # a rolled-back first use must record the declaration again
                self._declared[declaration.name] = known
        if known != declaration.as_record():
            raise WorkTableError('work_table_declaration_differs:' + declaration.name)

    @staticmethod
    def _row(values):
        ref, table, run_id, episode_id, _, unit, operation_key, revision, data, _ = values
        return {'id': ref, 'record_type': 'work_row', 'table': table, 'run_id': run_id, 'episode_id': episode_id,
                'unit': unit, 'operation_key': operation_key, 'revision': revision, **json.loads(data)}

    def _stored(self, ref):
        found = self._db.execute('SELECT ' + self._COLUMNS + ' FROM episode_work_rows WHERE row_ref=?',
                                 (ref,)).fetchone()
        return None if found is None else tuple(found)

    def row(self, ref):
        """The row ``ref`` whatever its table, or ``None``."""
        found = self._stored(ref)
        return None if found is None else self._row(found)

    def exists(self, ref):
        return self.row(ref) is not None

    def references(self, declaration, values):
        """Every record reference the declared ``record_refs`` columns of ``values`` name."""
        refs = []
        for column in declaration.record_refs:
            value = values[column]
            for ref in ([] if value is None else value if isinstance(value, list) else [value]):
                if type(ref) is not str or not ref:
                    raise WorkTableError('work_table_record_reference_must_be_text:' + declaration.name + ':'
                                         + column)
                refs.append(ref)
        return refs

    def _put(self, ref, table, run_id, episode_id, row_key, unit, operation_key, data):
        """Store the values ``data`` (canonical JSON text) as the row ``ref``: a new row, nothing when the values
        are the stored ones, otherwise the next revision."""
        current = self._stored(ref)
        if current is None:
            self._db.execute('INSERT INTO episode_work_rows VALUES(?,?,?,?,?,?,?,?,?,NULL)', (
                ref, table, run_id, episode_id, row_key, unit, operation_key, 1, data))
        elif not same_json(json.loads(current[8]), json.loads(data)):
            # The first write of a unit to a row an earlier unit wrote keeps that earlier row.
            prior = current[9] if current[5] == unit else canonical({
                'unit': current[5], 'operation_key': current[6], 'revision': current[7],
                'data': json.loads(current[8])})
            self._db.execute('UPDATE episode_work_rows SET unit=?, operation_key=?, revision=?, data=?, prior=? '
                             'WHERE row_ref=?', (unit, operation_key, current[7] + 1, data, prior, ref))
        return self.row(ref)

    def write(self, declaration, owner, unit, operation_key, values):
        """Write the row of ``owner`` (run id, episode id) with the key in ``values``; returns the stored row.
        Writing equal values again changes nothing; other values make the next revision."""
        self.declare(declaration)
        if not isinstance(values, Mapping) or set(values) != set(declaration.columns):
            raise WorkTableError('work_table_row_must_have_exactly_its_columns:' + declaration.name + ':'
                                 + ','.join(declaration.columns))
        values = closed_copy(dict(values), 'work_table_row', WorkTableError)
        run_id, episode_id = owner
        row_key = canonical([values[name] for name in declaration.key])
        ref = ROW_PREFIX + content_digest([declaration.name, run_id, episode_id, row_key])
        return self._put(ref, declaration.name, run_id, episode_id, row_key, unit, operation_key, canonical(values))

    # -- what an unfinished unit's attempt wrote --------------------------------------------
    def abandon_unfinished(self, owner, position):
        """Take back every row write of ``owner``'s units from ``position`` on (units that did not finish): a row
        such a unit created is removed, a row it rewrote is put back as it stood before the unit, and what the
        attempt wrote is kept for the rerun (``abandoned``). Runs inside the caller's Store transaction."""
        run_id, episode_id = owner
        for stored in [tuple(found) for found in self._db.execute(
                'SELECT ' + self._COLUMNS + ' FROM episode_work_rows WHERE run_id=? AND episode_id=? AND unit>=? '
                'ORDER BY rowid', (run_id, episode_id, position))]:
            ref, table, _, _, row_key, unit, _, _, data, prior = stored
            self._db.execute('INSERT OR REPLACE INTO episode_abandoned_rows VALUES(?,?,?,?,?,?,?,?)', (
                ref, unit, table, run_id, episode_id, row_key, data, canonical(self._row(stored))))
            if prior is None:
                self._db.execute('DELETE FROM episode_work_rows WHERE row_ref=?', (ref,))
            else:
                before = json.loads(prior)
                self._db.execute('UPDATE episode_work_rows SET unit=?, operation_key=?, revision=?, data=?, '
                                 'prior=NULL WHERE row_ref=?', (before['unit'], before['operation_key'],
                                                                before['revision'], canonical(before['data']), ref))

    def abandoned(self, owner, unit):
        """The rows the abandoned attempts of ``owner``'s ``unit`` wrote, in order: ``{'ref', 'written' (the row as
        the last such attempt left it), 'prior' (the row as it stands again; ``None`` when the attempt created
        it)}``."""
        run_id, episode_id = owner
        return [{'ref': found[0], 'written': json.loads(found[1]), 'prior': self.row(found[0])}
                for found in self._db.execute(
                    'SELECT row_ref, written FROM episode_abandoned_rows WHERE run_id=? AND episode_id=? AND unit=? '
                    'ORDER BY rowid', (run_id, episode_id, unit)).fetchall()]

    def write_abandoned(self, owner, unit, ref, operation_key):
        """Write the row ``ref`` again as the abandoned attempt of ``owner``'s ``unit`` left it (a reclaim)."""
        run_id, episode_id = owner
        found = self._db.execute('SELECT table_name, row_key, data FROM episode_abandoned_rows WHERE row_ref=? '
                                 'AND unit=? AND run_id=? AND episode_id=?', (ref, unit, run_id, episode_id)).fetchone()
        if found is None:
            raise WorkTableError('work_table_row_not_abandoned_by_this_unit:' + str(ref))
        return self._put(ref, found[0], run_id, episode_id, found[1], unit, operation_key, found[2])


class TableReader:
    """The rows of one declared work table that an Episode holds (read-only)."""

    def __init__(self, rows, custody, declaration):
        rows.declare(declaration)
        self.__rows, self.__custody, self.__declaration = rows, custody, declaration

    def get(self, row_ref):
        """The row ``row_ref`` of this table, only when the Episode holds it."""
        self.__custody.require_readable(row_ref)
        row = self.__rows.row(row_ref)
        if row is None or row['table'] != self.__declaration.name:
            raise WorkTableError('work_table_row_not_in_this_table:' + self.__declaration.name + ':'
                                 + str(row_ref))
        return row

    def select(self, where=None, limit=None, offset=0):
        """The held rows of this table, in receipt order, whose columns equal ``where`` ({column: value}; value or
        system columns). ``limit`` and ``offset`` cut the page after the custody limit and the filter; without a
        ``limit`` every such row is returned."""
        where = {} if where is None else dict(where)
        unknown = sorted(set(where) - set(self.__declaration.columns) - set(SYSTEM_COLUMNS))
        if unknown:
            raise WorkTableError('work_table_filter_names_unknown_columns:' + self.__declaration.name + ':'
                                 + ','.join(unknown))
        if type(offset) is not int or offset < 0 or (limit is not None and (type(limit) is not int or limit < 0)):
            raise WorkTableError('work_table_page_must_be_nonnegative_integers')
        found = []
        for ref in self.__custody.refs():
            if not is_row_ref(ref):
                continue
            row = self.__rows.row(ref)
            if (row is not None and row['table'] == self.__declaration.name
                    and all(same_json(row[name], value) for name, value in where.items())):
                found.append(row)
        return found[offset:] if limit is None else found[offset:offset + limit]


class ScopedTable(TableReader):
    """One declared work table as a tool sees it: the held rows, and the writing unit's own rows."""

    def __init__(self, rows, custody, declaration, owner, transaction, readable):
        super().__init__(rows, custody, declaration)
        self.__rows, self.__custody, self.__declaration = rows, custody, declaration
        self.__owner, self.__transaction, self.__readable = owner, transaction, readable

    def put(self, values):
        """Write this Episode's row with the key in ``values`` (all declared columns); the Episode holds the row as
        produced by this unit. Every reference in the declared ``record_refs`` columns must be readable by the
        writing unit."""
        self.__rows.declare(self.__declaration)
        if isinstance(values, Mapping) and set(values) == set(self.__declaration.columns):
            for ref in self.__rows.references(self.__declaration, values):
                self.__readable(ref)
        with self.__transaction():
            if self.__custody.operation_key is None:
                raise CustodyError('record_written_outside_a_tool_unit:' + repr(self.__custody.path))
            row = self.__rows.write(self.__declaration, self.__owner, self.__custody.unit,
                                    self.__custody.operation_key, values)
            self.__custody.produced(row['id'])
        return row


__all__ = ['ROW_PREFIX', 'SYSTEM_COLUMNS', 'ScopedTable', 'TableDeclaration', 'TableReader', 'WorkRows',
           'WorkTableError', 'is_row_ref']
