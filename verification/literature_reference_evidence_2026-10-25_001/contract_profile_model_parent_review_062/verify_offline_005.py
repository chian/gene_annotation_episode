"""Inspect registered-source custody/counts only, without reading scientific text."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
OUT = HERE / 'offline_preparation_005'
PIN = HERE.parent / 'literature_contract_profile_model_run_063/pin_001'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((OUT / 'RECEIPT.json').read_text())
    for row in receipt['files']:
        assert digest(OUT / row['path']) == row['sha256']
    source_info = json.loads((OUT / 'SOURCE_CATALOG.json').read_text())
    metadata = json.loads((PIN / 'inputs/SOURCE_INPUT_METADATA.json').read_text())
    descriptor = json.loads((OUT / 'BINDING_DESCRIPTOR.json').read_text())
    assert descriptor['configuration']['contract_information_profile'] == 'operation_contract_information_v1'
    assert source_info['source_refs'] == descriptor['configuration']['reference_parent_sources']
    assert len(source_info['source_refs']) == 1
    source_checks = []
    database = (OUT / 'state/state.sqlite3').resolve()
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        runtime_tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'runtime_%'")]
        counts = {name: db.execute('SELECT count(*) FROM records WHERE record_type=?', (name,)).fetchone()[0]
                  for name in ('source', 'observation', 'assessment')}
        # Store.create_problem separately retains the caller sequence source.
        # One registered literature source does not imply one TOTAL source.
        assert runtime_tables == [] and counts == {'source': 2, 'observation': 0, 'assessment': 0}
        providers = dict(db.execute("SELECT json_extract(data,'$.provider'),count(*) FROM records WHERE record_type='source' GROUP BY json_extract(data,'$.provider')"))
        assert providers == {'caller': 1, 'retained_primary_pmc_html': 1}
        for item in metadata['sources']:
            saved = source_info['source_records'][item['key']]
            kind, origin, raw = db.execute('SELECT record_type,origin,data FROM records WHERE id=?', (saved['id'],)).fetchone()
            assert kind == 'source' and origin == 'caller'
            actual = json.loads(raw)
            for name in ('provider', 'artifact_ref', 'text_ref', 'parent_source_refs'):
                assert actual[name] == saved[name], name
            for key, field in (('original', 'artifact_ref'), ('text', 'text_ref')):
                if item[key] is None:
                    assert saved[field] is None
                    continue
                artifact = saved[field]
                assert artifact == 'artifact_' + item[key]['sha256']
                sha = artifact[len('artifact_'):]
                artifact_path = OUT / 'state/artifacts' / sha[:2] / sha
                assert digest(artifact_path) == item[key]['sha256'] == digest(PIN / 'inputs' / item[key]['filename'])
            source_checks.append({'source_ref': saved['id'], 'original_and_optional_text_bytes_match_original_pin': True})
        assert db.total_changes == 0 and db.execute('PRAGMA query_only').fetchone()[0] == 1
    result = {'observed_utc': datetime.now(timezone.utc).isoformat(),
        'command': 'Existing immutable pinned run_literature_source_job_062.py --offline-check root-owned offline_preparation_005',
        'actual_exit_code': 0, 'observed_terminal_result': {'status': 'passed', 'model_backed': False, 'source_count': 1, 'live_run_launched': False},
        'receipt_payload_files_verified': len(receipt['files']), 'actual_source_registration': True,
        'profile': descriptor['configuration']['contract_information_profile'],
        'mode_ro_public_record_counts': counts, 'total_source_count_meaning': 'one caller sequence-input source plus one registered literature source',
        'registered_literature_source_checks': source_checks, 'runtime_tables_present': runtime_tables,
        'sqlite_total_changes': 0, 'prospective_partner_form_is_fixture_not_live_selection': True,
        'root_job_or_prospective_task_or_scientific_text_opened': False, 'source_content_hashed_without_decoding': True,
        'actual_scientific_source_interpretation': False, 'configured_model_launched': False,
        'next_required': 'Complete actual JOB/prospective TASK review with required packet reset before scientific interpretation, then actual configured model execution.',
        'prepared_numeric_operands_supplied': False, 'original066_seal_preserved_by_external_output_location': True}
    with (HERE / 'OFFLINE_ROOT_RECEIPT_005.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'actual_exit_code': 0, 'literature_source_registration': 1,
        'total_sources_including_supplied_sequence': 2, 'observations': 0, 'assessments': 0,
        'runtime_tables': runtime_tables, 'model_launched': False, 'root_prospective_task_review_pending': True}))


if __name__ == '__main__':
    main()
