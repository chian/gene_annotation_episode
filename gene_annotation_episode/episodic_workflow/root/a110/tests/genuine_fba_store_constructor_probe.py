"""Observe the actual A110 Store constructor on an exact original360 copy.

No __new__ bypass, policy construction, native work or schema repair is used.
Original failed-run evidence and original saved runtime settings remain intact.
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

PIN = '7a3e9d961da978a8bc382539dcf21f6e224f26d4ac786d571fd4d60edfae18ae'


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
def cell(value): return {'sqlite_blob_base64': base64.b64encode(value).decode('ascii')} if isinstance(value, bytes) else value


def snapshot(connection):
    # Override the cursor materializer only, so these are exact stored cells,
    # distinct from Store._row's authenticated logical request restoration.
    cursor = connection.cursor()
    cursor.row_factory = sqlite3.Row
    try:
        schema = [dict(row) for row in cursor.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE type IN ('table','index','trigger','view') ORDER BY type,name")]
        tables = {}
        for entry in schema:
            if entry['type'] != 'table': continue
            name = entry['name']
            values = [{key: cell(row[key]) for key in row.keys()} for row in cursor.execute(
                'SELECT * FROM "' + name.replace('"', '""') + '"')]
            values.sort(key=canonical)
            tables[name] = {'count': len(values), 'rows_sha256': sha(canonical(values).encode()), 'raw_rows': values}
        pragmas = {name: cursor.execute('PRAGMA ' + name).fetchone()[0] for name in (
            'foreign_keys', 'journal_mode', 'synchronous', 'query_only', 'locking_mode')}
        integrity = [list(row) for row in cursor.execute('PRAGMA integrity_check')]
        foreign_keys = [list(row) for row in cursor.execute('PRAGMA foreign_key_check')]
        return {'schema': schema, 'tables': tables, 'connection_pragmas': pragmas,
            'integrity_check': integrity, 'foreign_key_check': foreign_keys,
            'connection_total_changes': connection.total_changes}
    finally: cursor.close()


def readonly(path):
    # mode=ro retains SQLite's ordinary WAL handling. No immutable flag can
    # silently ignore a constructor-created committed sidecar.
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try: return snapshot(connection)
    finally: connection.close()


def artifact_inventory(directory):
    return {str(path.relative_to(directory)): {'sha256': sha(path.read_bytes()), 'size_bytes': path.stat().st_size}
        for path in sorted((directory / 'artifacts').rglob('*')) if path.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).parent / 'fixtures/genuine_fba360'
    source = fixture / 'store/state.sqlite3'
    assert sha(source.read_bytes()) == PIN
    provenance = json.loads((fixture / 'provenance.json').read_text())
    assert provenance['historical_run_returncode'] == 1
    destination = output / 'actual-store'
    shutil.copytree(fixture / 'store', destination)
    copied_database_sha256 = sha((destination / 'state.sqlite3').read_bytes())
    if copied_database_sha256 != PIN:
        failure = {'version': 'a110_genuine_fba_actual_store_constructor_v2',
            'status': 'copied_database_pin_mismatch', 'original_database_sha256': PIN,
            'copied_database_before_constructor_sha256': copied_database_sha256,
            'original_run_returncode': 1, 'constructor_attempted': False,
            'policy_constructed': False, 'native_work': False, 'constructor_bypass': False}
        (output / 'constructor-observation.json').write_text(json.dumps(failure, indent=2) + '\n')
        raise SystemExit(1)
    before = readonly(destination / 'state.sqlite3')
    original_artifacts = artifact_inventory(destination)
    (output / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
    record = {'version': 'a110_genuine_fba_actual_store_constructor_v2',
        'original_database_sha256': PIN, 'original_run_returncode': 1,
        'copied_database_before_constructor_sha256': copied_database_sha256,
        'constructor_called': 'gene_annotation_episode.episodic_workflow.root.a110.state.Store',
        'policy_constructed': False, 'native_work': False, 'constructor_bypass': False,
        'historical_factory_inferred': False, 'before': 'before.json'}
    store = None
    try:
        state = importlib.import_module('gene_annotation_episode.episodic_workflow.root.a110.state')
        record['actual_constructor_source_sha256'] = sha(Path(state.__file__).read_bytes())
        store = state.Store(destination)
        after = snapshot(store.db)
        (output / 'after-constructor.json').write_text(json.dumps(after, indent=2) + '\n')
        record.update(status='constructed', after_constructor='after-constructor.json',
            actual_connection_pragmas=after['connection_pragmas'])
    except Exception as error:
        record.update(status='raised', exception_type=type(error).__module__ + '.' + type(error).__qualname__,
            message=str(error), traceback=traceback.format_exc())
    finally:
        record['close_attempted'] = store is not None
        try:
            if store is not None:
                store.close()
                record['close_status'] = 'closed'
        except Exception as error:
            record['close_failure'] = {'type': type(error).__module__ + '.' + type(error).__qualname__,
                'message': str(error), 'traceback': traceback.format_exc()}
        try:
            gc.collect()
        except Exception as error:
            record['collection_failure'] = {'type': type(error).__module__ + '.' + type(error).__qualname__,
                'message': str(error), 'traceback': traceback.format_exc()}
        (output / 'constructor-observation.json').write_text(json.dumps(record, indent=2) + '\n')
    try:
        closed = readonly(destination / 'state.sqlite3')
        (output / 'after-close.json').write_text(json.dumps(closed, indent=2) + '\n')
        changed_rows = [name for name, value in before['tables'].items()
            if closed['tables'].get(name) != value]
        previous_schema = {(row['type'], row['name']): row for row in before['schema']}
        current_schema = {(row['type'], row['name']): row for row in closed['schema']}
        record.update(after_close='after-close.json',
            changed_original_tables=changed_rows,
            added_tables=sorted(set(closed['tables']) - set(before['tables'])),
            changed_original_schema=[list(key) for key, value in previous_schema.items() if current_schema.get(key) != value],
            added_schema=[list(key) for key in current_schema if key not in previous_schema],
            all_original_rows_unchanged=not changed_rows,
            artifact_bytes_unchanged=artifact_inventory(destination) == original_artifacts,
            after_close_integrity=closed['integrity_check'],
            after_close_foreign_key_check=closed['foreign_key_check'])
    except Exception as error:
        record['after_close_failure'] = {'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'traceback': traceback.format_exc()}
    record['original_fixture_database_unchanged'] = sha(source.read_bytes()) == PIN
    (output / 'constructor-observation.json').write_text(json.dumps(record, indent=2) + '\n')
    passed = (record['status'] == 'constructed' and record.get('close_status') == 'closed'
        and 'close_failure' not in record and 'collection_failure' not in record
        and record.get('original_fixture_database_unchanged') is True
        and record.get('all_original_rows_unchanged') is True
        and record.get('artifact_bytes_unchanged') is True
        and record.get('actual_connection_pragmas', {}).get('foreign_keys') == 1
        and record.get('after_close_integrity') == [['ok']])
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__': main()
