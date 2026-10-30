"""Audit the completed controlled MinHash Workflow using read-only SQLite."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

OWN = Path(__file__).resolve().parent
OUTPUT = Path(sys.argv[1]).resolve()
assert OUTPUT.parent == OWN and OUTPUT.is_dir()
assert json.loads((OWN / 'fixture_comparison_001/receipt.json').read_text())['exit_code'] == 0
database = OWN / 'fixture_comparison_001/temporary/minhash-return-boundaries0/state/state.sqlite3'
before = hashlib.sha256(database.read_bytes()).hexdigest()
expected = {'launch_api': 1, 'launch': 1, 'results': 1, 'scientific_process': 3, 'annotation': 2}
report = {}
with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
    connection.row_factory = sqlite3.Row
    for episode in connection.execute('SELECT * FROM runtime_episodes ORDER BY path'):
        identity = (episode['run_id'], episode['episode_id'])
        role = json.loads(episode['path'])[-1][0]
        actions = [dict(item) for item in connection.execute(
            'SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index', identity)]
        observations = [json.loads(item['observation']) for item in connection.execute(
            'SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index', identity)]
        assert len(actions) == len(observations) == expected[role]
        assert episode['state'] == 'yielded'
        assert json.loads(episode['completion']) == {'actions': expected[role], 'ended_by': 'yield_stop'}
        for index, (action, observation) in enumerate(zip(actions, observations)):
            assert action['result'] is not None
            assert action['decision_index'] == observation['decision_index'] == observation['unit_ref']['unit_index'] == index
            assert action['credit'] == observation['credit']['credit']
        if role in {'launch_api', 'launch', 'results'}:
            last = observations[-1]
            assert last['credit']['credit'] > 0
            assert last['credit']['practical_completion']['version'] == 'practical_completion_v1'
            band = last['step']['estimate']['expected_next_gain']
            assert band['value'] == band['lower'] == band['upper'] == 0
            assert last['step']['stop'] is True
        report[role] = {'episode_id': episode['episode_id'], 'actions': len(actions),
            'observations': len(observations), 'credits': [item['credit']['credit'] for item in observations],
            'last_expected_next_gain': observations[-1]['step']['estimate']['expected_next_gain']}
assert set(report) == set(expected)
assert sum(item['actions'] for item in report.values()) == 8
assert hashlib.sha256(database.read_bytes()).hexdigest() == before
result = {'database': str(database), 'database_sha256': before, 'read_only_unchanged': True,
    'one_observation_per_completed_action': True, 'episodes': report}
(OUTPUT / 'MINHASH_FIXTURE_JOURNAL.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
