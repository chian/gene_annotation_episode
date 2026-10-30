"""Read-only saved-run forensics, invoked only by the existing bounded runner.

This collects prior rows; it does not rerun failed tests or scientific analyses.
"""
from pathlib import Path
import hashlib
import json
import os
import sqlite3


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(value):
    return None if value is None else json.loads(value)


def _rows(db, table):
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
        return []
    return [dict(row) for row in db.execute('SELECT * FROM ' + table)]


def _call(row):
    request = _json(row['request'])
    context = request['context']
    selection = request['schema'].get('properties', {}).get('selection', {})
    working = context.get('working_state', {})
    return {'episode_id': row['episode_id'], 'call_index': row['call_index'],
        'request_sha256': hashlib.sha256(row['request'].encode()).hexdigest(),
        'decision_protocol': request.get('decision_protocol'),
        'response': _json(row['response']),
        'context': {key: context.get(key) for key in ('current_credit', 'feedback',
            'visible_record_refs', 'controller', 'child_reports', 'report_deliveries')},
        'working_state': {'record_view': working.get('record_view'),
            'assessment_refs': [value['id'] for value in working.get('assessments', [])]},
        'tool_names': [entry['name'] for entry in context.get('tools', [])],
        'action_alternatives': [{'kind': branch.get('properties', {}).get('kind', {}).get('const'),
            'tool': branch.get('properties', {}).get('tool', {}).get('const')}
            for branch in selection.get('anyOf', [])]}


def test_collect_saved_check061_failures_read_only():
    attempt = Path(os.environ['HMMER529_ATTEMPT'])
    packet = Path(__file__).resolve().parent
    manifest = json.loads((packet/'saved_inputs/manifest.json').read_text())
    original_repo = attempt.parents[2]
    assert len(manifest['cases']) == 12
    cases = []
    for case in manifest['cases']:
        path = packet/'saved_inputs'/case['staged_name']
        original = original_repo/case['original']['path']
        before, original_before = _sha(path), _sha(original)
        assert before == original_before == case['staged_sha256'] == case['original']['sha256']
        db = sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True)
        db.row_factory = sqlite3.Row
        try:
            runs = _rows(db, 'runtime_runs')
            episodes = _rows(db, 'runtime_episodes')
            actions = _rows(db, 'runtime_actions')
            observations = _rows(db, 'runtime_observations')
            reports = _rows(db, 'runtime_report_attempts')
            effects = _rows(db, 'runtime_decision_effects')
            exchanges = _rows(db, 'runtime_decision_exchanges')
            calls = _rows(db, 'runtime_model_calls')
            cases.append({'case_index': case['case_index'], 'nodeid': case['nodeid'],
                'saved_failure': case['saved_failure'], 'original_database': case['original'],
                'runs': [{**row, 'settings': _json(row['settings']), 'summary': _json(row['summary'])}
                    for row in runs],
                'episodes': [{key: (_json(row[key]) if key in {'path', 'completion'} else row[key])
                    for key in ('episode_id', 'path', 'initial_credit', 'state', 'completion')}
                    for row in episodes],
                'calls': [_call(row) for row in calls],
                'actions': [{**row, 'action': _json(row['action']), 'result': _json(row['result'])}
                    for row in actions],
                'observations': [{**row, 'observation': _json(row['observation'])} for row in observations],
                'reports': [{**row, 'contract': _json(row['contract']), 'form': _json(row['form']),
                    'failure': _json(row['failure'])} for row in reports],
                'decision_effects': effects,
                'exchanges': [{key: (_json(value) if key in {'response', 'lookup_result'} else value)
                    for key, value in row.items() if key != 'request'} for row in exchanges],
                'record_receipts': _rows(db, 'runtime_record_receipts'),
                'receipt_inheritance': _rows(db, 'runtime_receipt_inheritance'),
                'table_counts': {table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                    for table in ('reasoning_commits', 'tool_operations', 'records', 'synthetic_records')
                    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()},
                'readonly': True})
        finally:
            db.close()
        assert _sha(path) == before and _sha(original) == original_before
        cases[-1]['staged_and_original_hashes_unchanged'] = True
    (attempt/'saved_failure_rows.json').write_text(json.dumps({
        'source': manifest['evidence_source'], 'cases': cases}, indent=2, allow_nan=False)+'\n')
