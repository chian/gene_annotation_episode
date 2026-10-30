"""Read completed197 Workflow journals without opening a writable Store."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

OWN = Path(__file__).resolve().parent
RUN = OWN / 'full_workflow_001'
OUTPUT = Path(sys.argv[1]).resolve()
assert OUTPUT.parent == OWN and OUTPUT.is_dir()
assert json.loads((RUN / 'receipt.json').read_text())['exit_code'] == 0
assert json.loads((RUN / 'pytest_exit.json').read_text())['exit_code'] == 0
EXPECTED = {'annotation': 1, 'scientific_process': 2, 'launch': 1, 'launch_api': 2, 'results': 7}
ZERO = {'alpha': 0.0, 'lower': 0.0, 'status_code': 0, 'uncertainty_code': 0, 'upper': 0.0, 'value': 0.0}
report = {}
databases = {path.resolve() for path in (RUN / 'temporary').glob('test_actual_selected_tool_shar*/state/state.sqlite3')}
for database in sorted(databases):
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    episodes = {}
    forms = {}
    for row in connection.execute('SELECT * FROM runtime_episodes ORDER BY path'):
        role = json.loads(row['path'])[-1][0]
        assert role not in episodes
        actions = [dict(item) for item in connection.execute(
            'SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index',
            (row['run_id'], row['episode_id']))]
        observations = [json.loads(item['observation']) for item in connection.execute(
            'SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index',
            (row['run_id'], row['episode_id']))]
        completion = json.loads(row['completion'])
        assert completion == {'actions': EXPECTED[role], 'ended_by': 'yield_stop'}, (role, completion)
        assert row['state'] == 'yielded'
        assert len(actions) == len(observations) == EXPECTED[role]
        assert [item['decision_index'] for item in actions] == list(range(EXPECTED[role]))
        assert [item['decision_index'] for item in observations] == list(range(EXPECTED[role]))
        assert [item['unit_ref']['unit_index'] for item in observations] == list(range(EXPECTED[role]))
        for action, observation in zip(actions, observations):
            assert action['result'] is not None
            assert action['credit'] == observation['credit']['credit']
        if role in {'launch', 'launch_api', 'results'}:
            last = observations[-1]
            assert last['credit']['credit'] > 0
            assert last['credit']['practical_completion']['version'] == 'practical_completion_v1'
            assert last['step']['estimate']['expected_next_gain'] == ZERO
            assert last['step']['stop'] is True
        form_row = connection.execute(
            'SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (row['run_id'], row['episode_id'])).fetchone()
        if role == 'annotation':
            assert form_row is None, 'root annotation has no parent return'
        else:
            assert form_row is not None, role
            forms[role] = json.loads(form_row['form'])
        episodes[role] = {'episode_id': row['episode_id'], 'state': row['state'],
            'completion': completion, 'action_count': len(actions), 'observation_count': len(observations),
            'credits': [item['credit']['credit'] for item in observations],
            'last_expected_next_gain': observations[-1]['step']['estimate']['expected_next_gain'],
            'observations': observations, 'archive': json.loads(row['archive'])}
    assert set(episodes) == set(EXPECTED)
    assert forms['results']['completed'] is True
    assert json.dumps(forms['scientific_process'], sort_keys=True) == json.dumps(
        {key: forms['results'][key] for key in forms['scientific_process']}, sort_keys=True)
    assert sum(item['action_count'] for item in episodes.values()) == 13
    assert sum(item['observation_count'] for item in episodes.values()) == 13
    connection.close()
    after = hashlib.sha256(database.read_bytes()).hexdigest()
    assert before == after
    report[str(database.relative_to(RUN))] = {'database_sha256': before, 'read_only_unchanged': True,
        'episodes': episodes, 'forms': forms, 'root_has_no_parent_return': True,
        'scientific_forwarded_field_count': len(forms['scientific_process'])}
assert len(report) == 2
(OUTPUT / 'WORKFLOW_ACCOUNTING.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({path: {role: {key: value[key] for key in ('action_count', 'observation_count', 'credits')}
    for role, value in result['episodes'].items()} for path, result in report.items()}, indent=2))
