"""Real constructor migration on a disposable copy, sealed before saved reads.

Original archives, extracted controls, contexts and authority methods stay intact.
Added empty tables are initialization state, never historical evidence.
"""
from contextlib import contextmanager
from pathlib import Path
import shutil
import sqlite3
import tempfile

from gene_annotation_episode.episodic_workflow.root.a104.state import Store
from gene_annotation_episode.episodic_workflow.root.a104.tests.retained_fluorescence_fixture import (
    RetainedCase, digest, unpack as original_fluorescence_unpack)
from gene_annotation_episode.episodic_workflow.root.a104.tests.retained_protein_fixture import (
    ProteinRetainedCase, unpack as original_protein_unpack)


def _quote(name):
    return '"' + name.replace('"', '""') + '"'


def _snapshot(connection):
    # Raw SQLite values avoid Store's request-artifact materialization changing
    # what is compared. Neither row values nor schema declarations are rewritten.
    cursor = connection.cursor()
    cursor.row_factory = None
    try:
        schema = tuple(cursor.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name").fetchall())
        table_modes = {row[1]: bool(row[4]) for row in cursor.execute('PRAGMA table_list').fetchall()
            if row[0] == 'main'}
        tables = {}
        for kind, name, table, sql in schema:
            if kind != 'table':
                continue
            columns = tuple(cursor.execute('PRAGMA table_info(' + _quote(name) + ')').fetchall())
            if table_modes[name]:
                # WITHOUT ROWID tables retain their actual primary key in the
                # original columns/schema; there is no synthetic row identity.
                row_identity = 'WITHOUT ROWID'
                rows = tuple(sorted(cursor.execute('SELECT * FROM ' + _quote(name)).fetchall(), key=repr))
            else:
                names = {column[1].lower() for column in columns}
                aliases = [alias for alias in ('rowid', '_rowid_', 'oid') if alias not in names]
                assert aliases, ('hidden_rowid_shadowed_by_all_aliases', name)
                row_identity = aliases[0]
                rows = tuple(cursor.execute('SELECT ' + _quote(row_identity) + ', * FROM '
                    + _quote(name) + ' ORDER BY ' + _quote(row_identity)).fetchall())
            tables[name] = {'columns': columns, 'row_identity': row_identity, 'rows': rows}
        return {'schema': schema, 'tables': tables}
    finally:
        cursor.close()


def _read_snapshot(database, *, immutable=False):
    uri = Path(database).resolve().as_uri() + '?mode=ro' + ('&immutable=1' if immutable else '')
    connection = sqlite3.connect(uri, uri=True, isolation_level=None)
    try:
        connection.execute('PRAGMA query_only=ON')
        return _snapshot(connection)
    finally:
        connection.close()


def _assert_original_preserved(original, current):
    for declaration in original['schema']:
        assert declaration in current['schema'], ('original_schema_changed', declaration[:3])
    for name, content in original['tables'].items():
        assert current['tables'].get(name) == content, ('original_rows_or_columns_changed', name)
    added = set(current['tables']) - set(original['tables'])
    for name in added:
        assert current['tables'][name]['rows'] == (), ('constructor_added_evidence_rows', name)
    return tuple(sorted(added))


class _DisposableStore:
    def seal_store(self, store):
        assert store is self._active_store and self._active_sealed is False
        assert not store.db.in_transaction
        current = _snapshot(store.db)
        added = _assert_original_preserved(self._original_snapshot, current)
        store.db.execute('PRAGMA query_only=ON')
        assert store.db.execute('PRAGMA query_only').fetchone()[0] == 1
        self._active_sealed = True
        self._sealed_snapshot = current
        self._sealed_total_changes = store.db.total_changes
        self.store_copy_observations.append({'phase': 'constructor_then_query_only',
            'original_table_count': len(self._original_snapshot['tables']),
            'added_empty_tables': added, 'historical_rows_changed': False})

    @contextmanager
    def open_store(self, *, overlay=None):
        self.verify_unchanged()
        original_database = self.directory / 'state/state.sqlite3'
        assert digest(original_database.read_bytes()) == self.allowed['state/state.sqlite3']['sha256']
        original = _read_snapshot(original_database, immutable=True)
        if not hasattr(self, '_disposable_state'):
            directory = Path(tempfile.mkdtemp(prefix='retained-store-copy-', dir=self.directory.parent))
            self._disposable_state = directory / 'state'
            shutil.copytree(self.directory / 'state', self._disposable_state)
            for name in ('state.sqlite3', 'state.sqlite3-wal', 'state.sqlite3-shm'):
                writable = self._disposable_state / name
                assert not writable.is_symlink(), ('disposable_sqlite_symlink', name)
                if name == 'state.sqlite3':
                    assert writable.exists(), 'disposable_database_missing'
                if writable.exists():
                    assert writable.is_file(), ('disposable_sqlite_not_regular', name)
                    assert writable.resolve().parent == self._disposable_state.resolve()
                    writable.chmod(0o600)
            self.store_copy_observations = []
            assert _read_snapshot(self._disposable_state / 'state.sqlite3') == original
        else:
            assert _read_snapshot(self._disposable_state / 'state.sqlite3') == self._sealed_snapshot
        assert getattr(self, '_active_store', None) is None
        # The real Store installs its own schema. The real owner constructor
        # subsequently installs progress tables before seal_store is called.
        store = Store(self._disposable_state)
        self._active_store, self._active_sealed = store, False
        self._original_snapshot = original
        store.path = self.logical_root / 'state'

        def get_artifact(reference):
            row = store.db.execute('SELECT sha256 FROM artifacts WHERE id=?', (reference,)).fetchone()
            physical = self._disposable_state
            if row is not None:
                relative = 'state/artifacts/' + row['sha256'][:2] + '/' + row['sha256']
                if relative in self.allowed:
                    actual = self.directory / relative
                    assert digest(actual.read_bytes()) == self.allowed[relative]['sha256']
                    assert digest((physical / 'artifacts' / row['sha256'][:2] / row['sha256']).read_bytes()) == self.allowed[relative]['sha256']
                elif overlay is not None and row['sha256'] == self.recovered['sha256']:
                    physical = Path(overlay)
                    body = physical / 'artifacts' / row['sha256'][:2] / row['sha256']
                    assert digest(body.read_bytes()) == self.recovered['sha256']
                else:
                    assert not (self.directory / relative).exists()
            logical_path = store.path
            try:
                store.path = physical
                return Store.get_artifact(store, reference)
            finally:
                store.path = logical_path

        store.get_artifact = get_artifact
        completed = False
        try:
            _assert_original_preserved(original, _snapshot(store.db))
            yield store
            completed = True
        finally:
            try:
                current = _snapshot(store.db)
                _assert_original_preserved(original, current)
                if completed:
                    assert self._active_sealed is True, 'authentication phase must follow constructor seal'
                if self._active_sealed:
                    assert store.db.execute('PRAGMA query_only').fetchone()[0] == 1
                    assert current == self._sealed_snapshot
                    assert store.db.total_changes == self._sealed_total_changes
            finally:
                store.close()
                self._active_store = None
                self.verify_unchanged()
                assert digest(original_database.read_bytes()) == self.allowed['state/state.sqlite3']['sha256']
            if self._active_sealed:
                assert _read_snapshot(self._disposable_state / 'state.sqlite3') == self._sealed_snapshot
                self.store_copy_observations.append({'phase': 'closed_copy_reopened_read_only',
                    'query_only_read_phase': True, 'historical_rows_changed': False})


class DisposableRetainedCase(_DisposableStore, RetainedCase):
    pass


class DisposableProteinRetainedCase(_DisposableStore, ProteinRetainedCase):
    pass


def unpack_fluorescence(directory):
    return [DisposableRetainedCase(case.directory, case.manifest, case.recovered)
        for case in original_fluorescence_unpack(directory)]


def unpack_protein(directory):
    original = original_protein_unpack(directory)
    case = DisposableProteinRetainedCase(original.directory, original.manifest, original.recovered)
    case.workflow_proof = original.workflow_proof
    return case
