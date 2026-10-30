"""Copy the authorized closed fixture verbatim; inspect only copied SQLite."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import stat
from urllib.parse import quote


SOURCE = Path('/tmp/pytest-of-chia/pytest-901/test_actual_scientific_worker_0')
DESTINATION = Path('/tmp/api-planning-root-final-20261022-004/detached-fixture-001')
CHECKOUT = Path('/tmp/gene-annotation-hmmer-api-20261022-004')
INPUTS = Path('/tmp/api-planning-root-final-20261022-004/INPUTS.json')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        assert not path.is_symlink(), str(path)
        if path.is_file():
            result[str(path.relative_to(root))] = {'sha256': digest(path),
                'bytes': path.stat().st_size, 'mode': f'{stat.S_IMODE(path.stat().st_mode):04o}',
                'mtime_ns': path.stat().st_mtime_ns}
    return result


def source_guard():
    expected = json.loads(INPUTS.read_text())
    actual = {}
    for prefix in ('gene_annotation_episode', 'method_loop', 'tests'):
        for path in (CHECKOUT/prefix).rglob('*.py'):
            if '__pycache__' not in path.parts:
                actual[str(path.relative_to(CHECKOUT))] = {'sha256': digest(path), 'bytes': path.stat().st_size}
    assert actual == expected['files']
    assert len(actual) == 344
    return {'input_file_sha256': digest(INPUTS), 'runtime_pin': expected['runtime_pin'],
        'runtime_files': 133, 'test_files': 211, 'all344_members_and_bytes_unchanged': True}


guard_before = source_guard()
original = inventory(SOURCE)
assert len(original) == 69
assert not [name for name in original if name.endswith(('-wal', '-shm', '-journal'))]
DESTINATION.mkdir(mode=0o700)
raw = DESTINATION/'raw-tree'
shutil.copytree(SOURCE, raw, copy_function=shutil.copy2)
copied = inventory(raw)
assert copied == original
after = inventory(SOURCE)
assert after == original
schema = {}
for relative in original:
    path = raw/relative
    if path.suffix not in {'.sqlite', '.sqlite3'}:
        continue
    uri = 'file:'+quote(str(path), safe='/')+'?mode=ro&immutable=1'
    db = sqlite3.connect(uri, uri=True, isolation_level=None)
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        shape = {}
        for table in tables:
            assert table.replace('_', '').isalnum()
            shape[table] = {'columns': [row[1] for row in db.execute('PRAGMA table_info("'+table+'")')],
                'rows': db.execute('SELECT count(*) FROM "'+table+'"').fetchone()[0]}
        schema[relative] = shape
        db.rollback()
    finally:
        db.close()
assert inventory(SOURCE) == original
assert inventory(raw) == original
guard_after = source_guard()
for name, value in (
    ('ORIGINAL_INVENTORY.json', {'version': 'original_passed_fixture_inventory_v1',
        'source_root': str(SOURCE), 'files': original, 'file_count': len(original),
        'total_bytes': sum(row['bytes'] for row in original.values())}),
    ('COPY_MAPPING.json', {'version': 'passed_detached_fixture_exact_copy_v1',
        'source_root': str(SOURCE), 'raw_copy_root': str(raw),
        'file_count': len(original), 'source_file_hash_size_mode_mtime_unchanged': True,
        'raw_copy_file_hash_size_mode_mtime_equal': True,
        'source_and_raw_no_wal_shm_or_journal_files': True,
        'database_strategy': 'Closed fixture contained no WAL/SHM/journal. Exact raw file copies preserve original database bytes; no SQLite backup/checkpoint/constructor was needed. Only copies opened mode=ro&immutable=1/query_only with short read transactions.',
        'new_backup_aliases': [], 'source_guard_before': guard_before, 'source_guard_after': guard_after,
        'relocation_limit': 'Records retain original absolute source/run/fixture paths and content references. No path/reference/content-address rewrite. Raw copied databases are retained evidence, not a self-contained resumable relocated application.'}),
    ('SQLITE_SCHEMAS_AND_COUNTS.json', {'version': 'copied_fixture_schema_counts_v1',
        'read_only_copy_only': True, 'databases': schema})):
    with (DESTINATION/name).open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True)+'\n')
(DESTINATION/'README.md').write_text('''# Passed API004 detached scientific-worker fixture

Exact root-scripted isolated fixture from /tmp/pytest-of-chia/pytest-901/test_actual_scientific_worker_0. The original tree remains unchanged. raw-tree preserves every original file, byte hash, size, executable/file mode and modification time, including saved caller/policy, transport/bootstrap, synthetic A/P assets, original run state and immutable artifacts, model-protocol fixture turns, backend process identity/return and worker archives. No real configured model, public provider or native computation is claimed.

The fixture was closed and had no WAL/SHM/journal sidecars at preservation. Exact raw database copies are retained under their original relative names. Only copied databases are opened with sqlite3 mode=ro&immutable=1, PRAGMA query_only and short read transactions; no original Store/Workflow/ledger, checkpoint or recovery is constructed. Any later derived export is separately named and hashed. No original content address, reference or absolute path is rewritten. These retained bytes are not claimed to be a self-contained resumable application at the new path.

Root's complete final log/XML/count ledger remains separate. This preservation starts no test, worker, application operation or transport and changes no source or active scientific state.
''')
print(json.dumps({'destination': str(DESTINATION), 'raw_files': len(original),
    'raw_bytes': sum(row['bytes'] for row in original.values()),
    'database_paths': list(schema), 'source_unchanged': True, 'source_guard': guard_after}, indent=2))
