"""Read-only transport for byte-pinned original049 controls.

Logical paths and all original runtime/receipt identities remain unchanged.
Only filesystem reads are transported to declared immutable fixture copies.
No validator, context, authority decision, receipt or selected result is mocked.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import tarfile
from types import SimpleNamespace

from gene_annotation_episode.episodic_workflow.root.a104.state import Store

FIXTURES = Path(__file__).parent / 'fixtures/fluorescence_original049'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unpack(directory):
    manifest = json.loads((FIXTURES / 'manifest.json').read_bytes())
    assert manifest['version'] == 'a104_original049_fluorescence_read_fixture_v1'
    assert manifest['original_controls_rewritten'] is False
    result = []
    for case in manifest['cases']:
        archive = FIXTURES / case['archive']
        assert digest(archive.read_bytes()) == case['archive_sha256']
        destination = Path(directory) / case['operation']
        destination.mkdir()
        with tarfile.open(archive, 'r:gz') as stream:
            members = stream.getmembers()
            assert len(members) == len(case['files'])
            assert {row.name for row in members} == set(case['files'])
            for row in members:
                assert row.isfile() and not row.issym() and not row.islnk()
                relative = Path(row.name)
                assert not relative.is_absolute() and '..' not in relative.parts
                raw = stream.extractfile(row).read()
                pin = case['files'][row.name]
                assert digest(raw) == pin['sha256'] and len(raw) == pin['size_bytes']
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                target.chmod(0o444)
        result.append(RetainedCase(destination, case, manifest['qualified_recovered_sheet']))
    return result


class RetainedCase:
    def __init__(self, directory, manifest, recovered):
        self.directory, self.manifest, self.recovered = Path(directory), manifest, recovered
        self.logical_root = Path(manifest['logical_root'])
        self.allowed = manifest['files']
        self.absent = set(manifest['required_absent_control_files'])
        self.transported_reads = []

    def verify_unchanged(self):
        for relative, pin in self.allowed.items():
            file = self.directory / relative
            assert file.is_file() and not file.is_symlink()
            assert digest(file.read_bytes()) == pin['sha256']

    def transport_control(self, logical):
        logical = Path(logical)
        assert logical.is_absolute() and '..' not in logical.parts
        assert logical.is_relative_to(self.logical_root / 'run/execution-results')
        relative = str(logical.relative_to(self.logical_root))
        assert relative in self.allowed or relative in self.absent, 'undeclared historical path'
        actual = self.directory / relative
        if relative in self.absent:
            assert not actual.exists()
        else:
            assert actual.is_file() and not actual.is_symlink()
            assert digest(actual.read_bytes()) == self.allowed[relative]['sha256'], 'historical control digest mismatch'
        self.transported_reads.append(relative)
        return actual

    @contextmanager
    def open_store(self, *, overlay=None):
        # Keep the original logical Store path for authenticated worker-plan
        # comparisons. SQLite and artifact byte reads use declared copies.
        store = Store.__new__(Store)
        store.path = self.logical_root / 'state'
        store._savepoint = 0
        database = self.directory / 'state/state.sqlite3'
        assert digest(database.read_bytes()) == self.allowed['state/state.sqlite3']['sha256']
        store.db = sqlite3.connect(database.as_uri() + '?mode=ro&immutable=1', uri=True, isolation_level=None)
        store.db.row_factory = store._row
        store.db.execute('PRAGMA query_only=ON')
        store.db.create_function('library_scope_record', 2, store._scope_filter_record)

        def get_artifact(reference):
            row = store.db.execute('SELECT sha256 FROM artifacts WHERE id=?', (reference,)).fetchone()
            if row is None:
                # The actual Store error and digest semantics stay authoritative.
                return Store.get_artifact(SimpleNamespace(db=store.db, path=self.directory / 'state'), reference)
            relative = 'state/artifacts/' + row['sha256'][:2] + '/' + row['sha256']
            physical = self.directory / 'state'
            if relative in self.allowed:
                actual = self.directory / relative
                assert digest(actual.read_bytes()) == self.allowed[relative]['sha256']
            elif overlay is not None and row['sha256'] == self.recovered['sha256']:
                physical = Path(overlay)
                body = physical / 'artifacts' / row['sha256'][:2] / row['sha256']
                assert digest(body.read_bytes()) == self.recovered['sha256']
            else:
                # Only the original declared artifact identity may be absent.
                assert not (self.directory / relative).exists()
            return Store.get_artifact(SimpleNamespace(db=store.db, path=physical), reference)

        store.get_artifact = get_artifact
        try:
            yield store
            assert store.db.total_changes == 0
        finally:
            store.close()
            assert digest(database.read_bytes()) == self.allowed['state/state.sqlite3']['sha256']

    @contextmanager
    def control_transport(self, monkeypatch):
        from gene_annotation_episode.episodic_workflow.root.a104.library import fluorescence_result_receipts
        original = fluorescence_result_receipts.read_control

        def read(logical):
            return original(self.transport_control(logical))

        with monkeypatch.context() as patch:
            patch.setattr(fluorescence_result_receipts, 'read_control', read)
            yield

    def recovered_overlay(self, directory):
        root = Path(__file__).resolve().parents[1].parent
        source = root / 'tests/fixtures/fluorescence/retained_complete_sheet.json'
        raw = source.read_bytes()
        assert digest(raw) == self.recovered['sha256']
        provenance = source.with_name('retained_complete_sheet.provenance.json')
        assert digest(provenance.read_bytes()) == self.recovered['provenance_sha256']
        target = Path(directory) / 'artifacts' / self.recovered['sha256'][:2] / self.recovered['sha256']
        target.parent.mkdir(parents=True)
        target.write_bytes(raw)
        target.chmod(0o444)
        return Path(directory)
