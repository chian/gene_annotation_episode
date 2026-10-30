"""Reviewable exact-column derivatives from the copied scripted fixture only."""
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote


ROOT = Path('/tmp/api-planning-root-final-20261022-004/detached-fixture-001')
RAW = ROOT/'raw-tree'
OUT = ROOT/'derived-control-records'
OUT.mkdir(mode=0o700)
mapping = []


def connection(relative):
    db = sqlite3.connect('file:'+quote(str(RAW/relative), safe='/')+'?mode=ro&immutable=1',
        uri=True, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    return db


def raw_column(name, text, *, database, table, column, key):
    assert isinstance(text, str)
    target = OUT/name
    target.write_bytes(text.encode())
    mapping.append({'derived_path': str(target.relative_to(ROOT)),
        'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'bytes': target.stat().st_size,
        'source_copied_database': database, 'source_table': table, 'source_column': column,
        'source_row_key': key, 'representation': 'exact_original_stored_text_column_utf8_no_added_newline',
        'original_database_or_content_address_not_relabelled': True})


backend = connection('run/episode-execution/executions.sqlite')
try:
    commission, = backend.execute('SELECT * FROM commissions').fetchall()
    returned, = backend.execute('SELECT * FROM returns').fetchall()
    assert commission['handle'] == returned['handle']
    envelope = json.loads(returned['envelope'])
    identity = json.loads(commission['execution_identity'])
    spec = json.loads(commission['spec'])
    assert envelope['outcome'] == 'closed' and envelope['failure'] is None
    assert envelope['completion']['units_consumed'] == 2
    assert len(envelope['form']['forecasts']) == 1
    assert envelope['form']['forecasts'][0]['reported_result_support'] == {'reported_result_count': 0}
    assert envelope['form']['forecasts'][0]['expected_total_seconds'] is None
    raw_column('worker-execution-identity.from-sqlite.json', commission['execution_identity'],
        database='run/episode-execution/executions.sqlite', table='commissions',
        column='execution_identity', key={'handle': commission['handle']})
    raw_column('worker-return-envelope.from-sqlite.json', returned['envelope'],
        database='run/episode-execution/executions.sqlite', table='returns', column='envelope',
        key={'handle': returned['handle'], 'return_id': returned['return_id']})
    raw_column('original-commission-spec.from-sqlite.json', commission['spec'],
        database='run/episode-execution/executions.sqlite', table='commissions', column='spec',
        key={'handle': commission['handle']})
    backend.rollback()
finally:
    backend.close()

state = connection('case/workspace/state.sqlite3')
try:
    child_id, parent_id = spec['child']['episode_id'], spec['parent']['episode_id']
    child = state.execute('SELECT * FROM runtime_episodes WHERE episode_id=?', (child_id,)).fetchone()
    parent = state.execute('SELECT * FROM runtime_episodes WHERE episode_id=?', (parent_id,)).fetchone()
    assert child is not None and parent is not None
    form = state.execute('SELECT * FROM runtime_forms WHERE episode_id=?', (child_id,)).fetchone()
    assert json.loads(form['form']) == envelope['form']
    child_observations = state.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?', (child_id,)).fetchone()[0]
    parent_observations = state.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?', (parent_id,)).fetchone()[0]
    assert child_observations == 2 and parent_observations == 0
    api_action = state.execute("SELECT result FROM runtime_actions WHERE episode_id=? AND json_extract(action,'$.tool')='execution.estimate'", (child_id,)).fetchone()
    action = json.loads(api_action['result'])
    assert action['result']['api_reported_execution_forecasts'] == envelope['form']['forecasts']
    original_request = json.loads(child['request'])
    assert original_request == spec['child']['request']
    raw_column('original-child-request.from-sqlite.json', child['request'],
        database='case/workspace/state.sqlite3', table='runtime_episodes', column='request', key={'episode_id': child_id})
    raw_column('child-returned-form.from-sqlite.json', form['form'],
        database='case/workspace/state.sqlite3', table='runtime_forms', column='form', key={'episode_id': child_id})
    raw_column('original-estimate-action-result.from-sqlite.json', api_action['result'],
        database='case/workspace/state.sqlite3', table='runtime_actions', column='result',
        key={'episode_id': child_id, 'selected_tool': 'execution.estimate'})
    baseline = [dict(row) for row in state.execute('SELECT * FROM runtime_receipt_inheritance ORDER BY episode_id')]
    receipts = [dict(row) for row in state.execute('SELECT * FROM runtime_record_receipts ORDER BY receipt_index')]
    baseline_path = OUT/'original-receipt-baseline.rows-from-sqlite.json'
    baseline_path.write_text(json.dumps({'source_database': 'case/workspace/state.sqlite3',
        'runtime_receipt_inheritance': baseline, 'runtime_record_receipts': receipts}, indent=2, sort_keys=True)+'\n')
    mapping.append({'derived_path': str(baseline_path.relative_to(ROOT)), 'sha256': hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        'bytes': baseline_path.stat().st_size, 'source_copied_database': 'case/workspace/state.sqlite3',
        'source_tables': ['runtime_receipt_inheritance', 'runtime_record_receipts'],
        'representation': 'explicit_new_rows_export_preserving_original_column_values',
        'original_database_or_content_address_not_relabelled': True})
    assert state.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
    assert state.execute("SELECT count(*) FROM records WHERE record_type='native_execution'").fetchone()[0] == 0
    state.rollback()
finally:
    state.close()

summary = {'version': 'passed_fixture_control_relationships_v1',
    'source': 'Copied root-scripted detached scientific fixture only; no actual/private scientific provider input.',
    'handle': commission['handle'], 'child_episode_id': child_id, 'parent_episode_id': parent_id,
    'recorded_execution_identity': identity, 'recorded_backend_lifecycle': commission['lifecycle_state'],
    'return_id': returned['return_id'], 'return_outcome': envelope['outcome'],
    'returned_form_equals_original_child_form': True,
    'original_child_request_equals_original_commission': True,
    'returned_forecast_equals_original_selected_estimate': True,
    'child_observations': child_observations, 'parent_observations': parent_observations,
    'provider_job_count': 0, 'native_execution_record_count': 0,
    'parent_admission_limit': 'This detached fixture preserves closed child return and original parent pending commission; parent has zero observations. Separate connected tests cover parent typed admission. No parent admission is inferred here.',
    'archives': {key: envelope[key] for key in ('episode_archive', 'result_archive', 'facts_archive')},
    'raw_original_paths_and_references_remain_unchanged': True, 'derived_exports': mapping,
    'no_relocated_resumability_claim': True}
path = ROOT/'CONTROL_RELATIONSHIPS.json'
path.write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
print(json.dumps({'exports': len(mapping), 'summary': str(path),
    'child_observations': child_observations, 'parent_observations': parent_observations,
    'closed_original_form_verified': True, 'original_scope_and_proposal_preserved': True}, indent=2))
