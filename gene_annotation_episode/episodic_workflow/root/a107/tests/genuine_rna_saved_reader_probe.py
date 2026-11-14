"""Observe the actual current A107 Store and pure saved comparison validator.

No compatibility repair, constructor bypass, policy construction or native work.
The original successful historical worker is evidence only for its own request.
"""
from __future__ import annotations
import argparse
import base64
import gc
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sqlite3
import traceback

PIN = '0c14f71018292f2f2add7d5f82f0894902e2022d0050f81c4745eb567c6957c4'
INTENT_PIN = 'be47b6e2bcb6bd0201b5c9149a077ebeb046fff16f9d1b65fe444e227313aee7'
PREPARED_PIN = '911dfd2f1d401852d4b3afd1a698067e21a106bfa3b2d597925a4789713d219c'
CUSTODY_GUARD_SHA256 = '455e27b7ce71c3495a85aa6a648a9047af642f0c239830d08c807fbeb30fca51'
GRADE = Path('run/execution-results/e01ac1a94537cb83a5619707a7cdd652994ca7ce3289b0a3fd09312b34def7c7/rna-structure-comparison-actions/8c6478e1fed876dcfdee62621a44560f4138eb8b4f5680b23c9e862c50e497fa/grading')


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
def cell(value): return {'sqlite_blob_base64': base64.b64encode(value).decode('ascii')} if isinstance(value, bytes) else value
def failure(error): return {'type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error), 'traceback': traceback.format_exc()}
def save(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def inventory(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        assert not path.is_symlink(), ('unexpected_symlink', str(path))
        if path.is_file():
            raw = path.read_bytes()
            result[str(path.relative_to(directory))] = {'sha256': sha(raw), 'size_bytes': len(raw)}
    return result


def snapshot(connection):
    # Observe exact stored cells without Store._row's logical restoration.
    cursor = connection.cursor()
    cursor.row_factory = sqlite3.Row
    try:
        schema = [dict(row) for row in cursor.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE type IN ('table','index','trigger','view') ORDER BY type,name")]
        tables = {}
        for entry in schema:
            if entry['type'] != 'table': continue
            name = entry['name']
            rows = [{key: cell(row[key]) for key in row.keys()} for row in cursor.execute('SELECT * FROM "' + name.replace('"', '""') + '"')]
            rows.sort(key=canonical)
            tables[name] = {'count': len(rows), 'raw_rows_sha256': sha(canonical(rows).encode()), 'raw_rows': rows}
        return {'schema': schema, 'tables': tables,
            'connection_pragmas': {name: cursor.execute('PRAGMA ' + name).fetchone()[0] for name in ('foreign_keys', 'journal_mode', 'synchronous', 'query_only', 'locking_mode')},
            'integrity_check': [list(row) for row in cursor.execute('PRAGMA integrity_check')],
            'foreign_key_check': [list(row) for row in cursor.execute('PRAGMA foreign_key_check')],
            'connection_total_changes': connection.total_changes}
    finally: cursor.close()


def readonly(path):
    # Ordinary read-only WAL handling must see constructor-created commits.
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try: return snapshot(connection)
    finally: connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[5]
    output = args.output.resolve()
    assert output.is_relative_to(root / 'runs')
    output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).parent / 'fixtures/genuine_rna_one_structure385'
    destination = output / 'actual-store'
    record = {'version': 'a107_genuine_rna_saved_reader_v2', 'status': 'not_started',
        'helper_sha256': sha(Path(__file__).read_bytes()), 'original_database_sha256': PIN,
        'constructor_called': 'gene_annotation_episode.episodic_workflow.root.a107.state.Store',
        'reader_called': 'gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_publication.validate_prepared_rna_comparison',
        'constructor_attempted': False, 'reader_attempted': False, 'reader_validated': False,
        'constructor_returned': False, 'fixture_authenticated': False, 'copy_verified': False,
        'before_snapshot_complete': False, 'saved_arguments_authenticated': False,
        'after_constructor_snapshot_complete': False, 'after_reader_snapshot_complete': False,
        'after_close_snapshot_complete': False, 'fixture_after_complete': False,
        'policy_constructed': False, 'native_work': False, 'constructor_bypass': False,
        'compatibility_repair': False, 'typed_workflow_restored': False,
        'historical_policy_or_worker_rewritten': False}
    stage, store, before, original, guard = 'custody_guard', None, None, None, None
    try:
        guard_raw = Path(__file__).with_name('genuine_rna_saved_reader_custody.json').read_bytes()
        assert sha(guard_raw) == CUSTODY_GUARD_SHA256
        guard = json.loads(guard_raw)
        assert guard['version'] == 'a107_rna_saved_reader_custody_v2'
        (output / 'authenticated-custody.json').write_bytes(guard_raw)
        record.update(custody_guard_sha256=CUSTODY_GUARD_SHA256,
            custody_manifest_sha256=guard['fixture_manifest_sha256'],
            custody_applied_audit_sha256=guard['applied_custody_audit_sha256'])
        stage = 'fixture_preflight'
        original = inventory(fixture)
        save(output / 'fixture-before.json', original)
        assert original == guard['inventory'], 'fixture_custody_inventory_mismatch'
        assert original['store/state.sqlite3']['sha256'] == PIN
        for suffix in ('-wal', '-journal'):
            path = fixture / ('store/state.sqlite3' + suffix)
            assert not path.exists() or path.stat().st_size == 0
        provenance = json.loads((fixture / 'provenance.json').read_text())
        assert provenance['historical_database_sha256'] == PIN
        assert provenance['historical_check004_returncode'] == 0
        record['fixture_authenticated'] = True
        stage = 'copy'
        shutil.copytree(fixture / 'store', destination)
        record['copied_database_before_constructor_sha256'] = sha((destination / 'state.sqlite3').read_bytes())
        assert record['copied_database_before_constructor_sha256'] == PIN
        assert inventory(destination) == {name.removeprefix('store/'): value for name, value in original.items() if name.startswith('store/')}
        record['copy_verified'] = True
        stage = 'before_snapshot'
        before = readonly(destination / 'state.sqlite3')
        save(output / 'before.json', before)
        save(output / 'artifacts-before.json', inventory(destination / 'artifacts'))
        record['before_snapshot_complete'] = True
        stage = 'saved_arguments'
        grade = fixture / 'case' / GRADE
        intent_raw = (grade / 'intent.json').read_bytes()
        prepared_raw = (grade / 'prepared.json').read_bytes()
        record['saved_intent_sha256'] = sha(intent_raw)
        record['saved_prepared_sha256'] = sha(prepared_raw)
        assert record['saved_intent_sha256'] == INTENT_PIN, 'historical_intent_pin_mismatch'
        assert record['saved_prepared_sha256'] == PREPARED_PIN, 'historical_prepared_pin_mismatch'
        intent = json.loads(intent_raw)
        prepared = json.loads(prepared_raw)
        assert intent['result_receipt_key'] == prepared['result_receipt_key']
        arguments = {'prepared': prepared, 'selector': intent['selector'],
            'operands': intent['operands'], 'result_receipt_key': intent['result_receipt_key']}
        save(output / 'exact-reader-arguments.json', arguments)
        record['saved_arguments_authenticated'] = True
        stage = 'state_import'
        state = importlib.import_module('gene_annotation_episode.episodic_workflow.root.a107.state')
        record['actual_constructor_source_sha256'] = sha(Path(state.__file__).read_bytes())
        assert record['actual_constructor_source_sha256'] == guard['observed_sources'][
            'gene_annotation_episode/episodic_workflow/root/a107/state.py']
        stage = 'constructor'
        record['constructor_attempted'] = True
        store = state.Store(destination)
        record['constructor_returned'] = True
        stage = 'after_constructor_snapshot'
        save(output / 'after-constructor.json', snapshot(store.db))
        save(output / 'artifacts-after-constructor.json', inventory(destination / 'artifacts'))
        record['after_constructor_snapshot_complete'] = True
        stage = 'reader_import'
        publication = importlib.import_module('gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_publication')
        record['actual_reader_source_sha256'] = sha(Path(publication.__file__).read_bytes())
        assert record['actual_reader_source_sha256'] == guard['observed_sources'][
            'gene_annotation_episode/episodic_workflow/root/a107/rna_structure_comparison_publication.py']
        stage = 'reader'
        record['reader_attempted'] = True
        checked = publication.validate_prepared_rna_comparison(store, **arguments)
        record['reader_validated'] = True
        stage = 'reader_return'
        save(output / 'reader-return.json', checked)
        record['status'] = 'reader_returned'
    except Exception as error:
        record.update(status='raised', first_failure_stage=stage, first_failure=failure(error))
    finally:
        if store is not None:
            try:
                save(output / 'after-reader.json', snapshot(store.db))
                save(output / 'artifacts-after-reader.json', inventory(destination / 'artifacts'))
                record['after_reader_snapshot_complete'] = True
            except Exception as error: record['after_reader_snapshot_failure'] = failure(error)
        record['close_attempted'] = store is not None
        try:
            if store is not None:
                store.close()
                record['close_status'] = 'closed'
        except Exception as error: record['close_failure'] = failure(error)
        try:
            gc.collect()
            record['collection_status'] = 'collected'
        except Exception as error: record['collection_failure'] = failure(error)
        save(output / 'reader-observation.json', record)
    try:
        if (destination / 'state.sqlite3').exists():
            closed = readonly(destination / 'state.sqlite3')
            save(output / 'after-close.json', closed)
            save(output / 'artifacts-after-close.json', inventory(destination / 'artifacts'))
            record['after_close_snapshot_complete'] = True
            if before is not None:
                changed = [name for name, rows in before['tables'].items() if closed['tables'].get(name) != rows]
                old_schema = {(row['type'], row['name']): row for row in before['schema']}
                new_schema = {(row['type'], row['name']): row for row in closed['schema']}
                record.update(changed_original_tables=changed,
                    added_tables=sorted(set(closed['tables']) - set(before['tables'])),
                    changed_original_schema=[list(key) for key, value in old_schema.items() if new_schema.get(key) != value],
                    added_schema=[list(key) for key in new_schema if key not in old_schema],
                    all_original_rows_unchanged=not changed,
                    artifact_bytes_unchanged=inventory(destination / 'artifacts') == json.loads((output / 'artifacts-before.json').read_text()),
                    after_close_integrity=closed['integrity_check'])
    except Exception as error: record['after_close_failure'] = failure(error)
    try:
        final = inventory(fixture)
        save(output / 'fixture-after.json', final)
        record['fixture_after_complete'] = True
        record['original_fixture_unchanged'] = original is not None and final == original
    except Exception as error: record['fixture_after_failure'] = failure(error)
    # A legacy rejection remains a nonzero baseline, even with intact custody.
    passed = (record['reader_validated'] and record['status'] == 'reader_returned'
        and all(record[name] for name in ('fixture_authenticated', 'copy_verified', 'before_snapshot_complete',
            'saved_arguments_authenticated', 'constructor_returned', 'after_constructor_snapshot_complete',
            'after_reader_snapshot_complete', 'after_close_snapshot_complete', 'fixture_after_complete'))
        and record.get('close_status') == 'closed' and record.get('original_fixture_unchanged') is True
        and record.get('collection_status') == 'collected'
        and record.get('all_original_rows_unchanged') is True and record.get('artifact_bytes_unchanged') is True
        and record.get('after_close_integrity') == [['ok']]
        and not any(name in record for name in ('close_failure', 'collection_failure', 'after_reader_snapshot_failure', 'after_close_failure', 'fixture_after_failure')))
    record['diagnostic_exit_code'] = 0 if passed else 1
    save(output / 'reader-observation.json', record)
    raise SystemExit(record['diagnostic_exit_code'])


if __name__ == '__main__': main()
