"""Compare completed historical and197 action accounting without writable Stores."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

OWN = Path(__file__).resolve().parent
REPO = OWN.parent.parent
OUTPUT = Path(sys.argv[1]).resolve()
assert OUTPUT.parent == OWN and OUTPUT.is_dir()
current = json.loads((OWN / 'accounting_audit_002/WORKFLOW_ACCOUNTING.json').read_text())
historical = [
    ('proteome182', 'tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182',
        'temporary/test_actual_selected_tool_shar0/state/state.sqlite3'),
    ('comparative186', 'tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186',
        'temporary/test_actual_selected_tool_shar1/state/state.sqlite3'),
]
report = {}
for label, directory, current_key in historical:
    run = REPO / 'verification' / directory / 'final_workflow_001'
    databases = {path.resolve() for path in (run / 'temporary').glob(
        'test_actual_selected_tool_shar*/state/state.sqlite3')}
    assert len(databases) == 1, (label, databases)
    database = databases.pop()
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    roles = {}
    for row in connection.execute('SELECT * FROM runtime_episodes ORDER BY path'):
        role = json.loads(row['path'])[-1][0]
        assert role not in roles
        actions = list(connection.execute(
            'SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index',
            (row['run_id'], row['episode_id'])))
        observations = [json.loads(item['observation']) for item in connection.execute(
            'SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index',
            (row['run_id'], row['episode_id']))]
        roles[role] = {'action_count': len(actions), 'observation_count': len(observations),
            'credits': [item['credit']['credit'] for item in observations],
            'completion': json.loads(row['completion']), 'state': row['state']}
        expected = current[current_key]['episodes'][role]
        assert roles[role] == {key: expected[key] for key in roles[role]}, (label, role)
    assert set(roles) == set(current[current_key]['episodes'])
    connection.close()
    assert before == hashlib.sha256(database.read_bytes()).hexdigest()
    report[label] = {'historical_database': str(database), 'database_sha256': before,
        'read_only_unchanged': True, 'candidate_database': current_key,
        'equal_counts_credits_and_completion': True, 'roles': roles}
(OUTPUT / 'SAVED_WORKFLOW_ACCOUNTING_COMPARISON.json').write_text(
    json.dumps(report, indent=2) + '\n')
print(json.dumps({label: {'equal_counts_credits_and_completion': row[
    'equal_counts_credits_and_completion'], 'database_sha256': row['database_sha256']}
    for label, row in report.items()}, indent=2))
