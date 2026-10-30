"""Read completed composition evidence without opening a writable Store."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import socket
import sqlite3
import sys

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[1]
CANDIDATE = OWN / 'composition_candidate'
RUN = OWN / 'composition_checks_001'
OUT = OWN / 'COMPOSITION_FINAL_AUDIT_001.json'
assert not OUT.exists()
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


def forbidden(*args, **kwargs):
    raise AssertionError('Read-only completed evidence audit attempted network access')


socket.socket.connect = socket.socket.connect_ex = socket.create_connection = forbidden


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    path.chmod(0o444)


receipt = read(RUN / 'receipt.json')
assert receipt['exit_code'] == 0
outcomes = read(RUN / 'test_outcomes.json')
calls = [row for row in outcomes if row['when'] == 'call']
assert len(calls) == 7 and all(row['outcome'] == 'passed' for row in outcomes)
assert len({row['nodeid'] for row in calls}) == 7
assert len(read(RUN / 'collected.json')) == 7
expected = read(OWN / 'COMPOSITION_SOURCE_BEFORE_001.json')
actual = {name: sha(CANDIDATE / name) for name in expected}
assert actual == expected == read(RUN / 'source_before.json') == read(RUN / 'source_after.json')
production = read(OWN / 'APPLICATION_AFTER_001.json')
production_after = {name: sha(ROOT / name) for name in production}
assert production_after == production == read(OWN / 'COMPOSITION_PRODUCTION_BEFORE_001.json')
assert {name: actual[name] for name in production} == production
protected = read(OWN / 'COMPOSITION_PROTECTED_APPLICATION_001.json')
assert {name: sha(OWN / name) for name in protected} == protected
candidate_pins = read(OWN / 'COMPOSITION_CANDIDATE_PINS_002.json')
root_pins = read(OWN / 'COMPOSITION_PRODUCTION_PINS_002.json')
pins = {name: row['implementation_sha256'] for name, row in candidate_pins['pins'].items()}
assert pins == {name: row['implementation_sha256'] for name, row in root_pins['pins'].items()}
assert candidate_pins['registry_bound_adapters'] == root_pins['registry_bound_adapters'] == 9
flow_runs = list((CANDIDATE / 'verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25/runs').iterdir())
assert len(flow_runs) == 1
flow = flow_runs[0]
provenance = read(flow / 'PROVENANCE.json')
assert provenance['status'] == 'workflow_closed'
assert provenance['adapter_pin'] == pins['bvbrc_genome_alignment_bundle_adapter']
guard = read(flow / 'SOURCE_GUARD_AFTER_TESTS.json')
assert not guard['used_without_before_hash'] and not guard['all_changes'] and not guard['all_additions']
archive = read(flow / 'archive.json')
records = {}


def visit(record):
    records[record['episode_id']] = record
    for unit in record['units']:
        if unit.get('child') is not None:
            visit(unit['child'])


visit(archive)
database = flow / 'state/state.sqlite3'
database_before = sha(database)
connection = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
connection.row_factory = sqlite3.Row
episodes, forms, ids = {}, {}, {}
ZERO = {'alpha': 0.0, 'lower': 0.0, 'status_code': 0, 'uncertainty_code': 0,
        'upper': 0.0, 'value': 0.0}
for row in connection.execute('SELECT * FROM runtime_episodes ORDER BY path'):
    path = json.loads(row['path'])
    role = path[-1][0]
    assert role not in episodes
    ids[role] = row['episode_id']
    record = records[row['episode_id']]
    action_rows = [dict(item) for item in connection.execute(
        'SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index',
        (row['run_id'], row['episode_id']))]
    observations = [json.loads(item['observation']) for item in connection.execute(
        'SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index',
        (row['run_id'], row['episode_id']))]
    actions = {item['decision_index']: item for item in action_rows}
    assert len(actions) == len(observations) == record['units_consumed']
    assert row['state'] == 'yielded'
    assert json.loads(row['completion']) == {'actions': len(observations), 'ended_by': 'yield_stop'}
    assert [o['unit_ref']['unit_index'] for o in observations] == list(range(len(observations)))
    assert {o['decision_index'] for o in observations} == set(actions)
    previous = row['initial_credit']
    for index, observation in enumerate(observations):
        action = actions[observation['decision_index']]
        assert action['result'] is not None
        cumulative = observation['credit']['credit']
        marginal = observation['step']['marginal_credit']
        assert action['credit'] == cumulative == observation['step']['credit']
        assert marginal == cumulative - previous
        assert record['units'][index]['controller_step']['marginal_credit'] == marginal
        previous = cumulative
    model_calls = connection.execute('SELECT count(*) FROM runtime_model_calls WHERE run_id=? AND episode_id=?',
        (row['run_id'], row['episode_id'])).fetchone()[0]
    assert model_calls == len(observations) + int(role == 'scientific_process')
    if role in {'launch', 'launch_api', 'results'}:
        final = observations[-1]
        assert final['step']['marginal_credit'] > 0
        assert final['step']['estimate']['expected_next_gain'] == ZERO
        assert final['step']['stop'] is True
        assert record['controller_state']['estimate']['expected_next_gain'] == ZERO
        context = connection.execute('SELECT data FROM runtime_estimation_contexts WHERE run_id=? AND episode_id=? '
            'ORDER BY decision_index DESC LIMIT 1', (row['run_id'], row['episode_id'])).fetchone()
        proof = json.loads(context['data'])['practical_completion']
        assert proof['action_index'] == proof['unit_ref']['unit_index'] == len(observations) - 1
    else:
        assert all(o['step']['marginal_credit'] == 0 for o in observations)
        assert record['controller_state']['estimate']['expected_next_gain']['upper'] <= 0.1
    saved_form = connection.execute('SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?',
        (row['run_id'], row['episode_id'])).fetchone()
    if saved_form is not None:
        forms[role] = json.loads(saved_form['form'])
    if role == 'annotation':
        assert saved_form is None
        assert all(json.loads(action['action'])['kind'] != 'tool' for action in action_rows)
    episodes[role] = {'episode_id': row['episode_id'], 'state': row['state'],
        'action_count': len(actions), 'observation_count': len(observations), 'model_call_count': model_calls,
        'decision_indices': sorted(actions), 'initial_cumulative_credit': row['initial_credit'],
        'cumulative_credits': [o['credit']['credit'] for o in observations],
        'actual_marginal_gains': [o['step']['marginal_credit'] for o in observations],
        'final_expected_next_gain': observations[-1]['step']['estimate']['expected_next_gain'],
        'final_stop': observations[-1]['step']['stop'], 'observations': observations,
        'completion': json.loads(row['completion']), 'archive': json.loads(row['archive'])}
assert set(episodes) == {'annotation', 'scientific_process', 'launch', 'launch_api', 'results'}
assert (episodes['launch_api']['action_count'], episodes['launch']['action_count'], episodes['results']['action_count']) == (2, 1, 7)
assert forms['results'] == read(flow / 'results-return.json')
assert forms['scientific_process'] == read(flow / 'scientific-return.json')
assert forms['scientific_process'] == {key: forms['results'][key] for key in ('numbers', 'missing', 'qualifications')}
assert forms['results']['completed'] is True
attempt_evidence = []
for child_role, parent_role in (('results', 'scientific_process'), ('scientific_process', 'annotation')):
    attempts = [dict(row) for row in connection.execute('SELECT * FROM runtime_report_attempts WHERE child_episode_id=? '
        'ORDER BY decision_index', (ids[child_role],))]
    assert len(attempts) == (2 if child_role == 'results' else 1)
    child_row = connection.execute('SELECT request FROM runtime_episodes WHERE episode_id=?', (ids[child_role],)).fetchone()
    original_contract = json.loads(child_row['request'])['report_contract']
    for index, attempt in enumerate(attempts):
        assert attempt['parent_episode_id'] == ids[parent_role] and attempt['failure'] is None
        assert json.loads(attempt['form']) == forms[child_role]
        contract = json.loads(attempt['contract'])
        assert contract['measurements']['schema'] == original_contract['measurements']['schema']
        if index == 0:
            assert contract == original_contract
    attempt_evidence.append({'child': child_role, 'parent': parent_role, 'original_form_equal': True,
        'successful_attempt_count': len(attempts), 'original_schema_equal': True,
        'decision_indices': [a['decision_index'] for a in attempts]})
table_counts = {table: connection.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in
    ('runtime_actions', 'runtime_model_calls', 'runtime_observations', 'runtime_report_attempts', 'runtime_record_receipts')}
connection.close()
assert sha(database) == database_before
replay = read(flow / 'SAVED_REPLAY_CHECK.json')
assert replay['counts_before'] == replay['counts_after'] == table_counts
assert replay['new_http_calls'] == 0 and replay['same_plan_recalculation_equal'] is True
assert replay['changed_plan_union_bases'] == 677 and replay['changed_plan_fraction'] == 677 / 693
assert replay['saved_reads_and_admission_without_science'] and replay['workflow_redelivery_without_science']
assert replay['original_action_unchanged']
assert len(replay['blocked_scientific_implementations_and_aliases']) >= 100
numerical = read(flow / 'NUMERICAL_RETURN_CHECK.json')
coverage = numerical['numbers']['coverage']
assert (coverage['value'], coverage['numerator'], coverage['denominator'], coverage['unit'], coverage['state']) == (
    690 / 693, 690, 693, 'fraction', 'available')
assert numerical['numbers']['zero_gaps']['value'] == 0
assert numerical['retained_missing_requirements'] and numerical['qualifications']
original_native = CANDIDATE / 'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/retained_sources/mauve/testdata/small.mauve'
assert (flow / 'native-v4.mauve').read_bytes() == original_native.read_bytes()
write(OWN / 'COMPOSITION_SOURCE_AFTER_001.json', actual)
write(OWN / 'COMPOSITION_PRODUCTION_AFTER_001.json', production_after)
write(OWN / 'COMPOSITION_WORKFLOW_ACCOUNTING_001.json', {'database': str(database),
    'database_sha256': database_before, 'database_read_only_unchanged': True,
    'gain_source': 'runtime_observations.observation.step.marginal_credit',
    'cumulative_source': 'runtime_observations.observation.credit.credit',
    'episodes': episodes, 'forms': forms, 'parent_admissions': attempt_evidence, 'table_counts': table_counts})
result = {'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv, 'executable': sys.executable,
    'cwd': str(Path.cwd()), 'exit_code': 0, 'scope': 'bounded 197+203 composition verification only',
    'distinct_passing_cases': 7, 'failing_cases': [], 'workflow_cases': 6, 'previously_failing_host_case_passed': True,
    'frozen_candidate_paths_unchanged': len(actual), 'production_paths_unchanged': len(production_after),
    'protected_application_files_unchanged': len(protected), 'candidate_common_production_hashes_equal': True,
    'registry_pins': pins, 'fresh_root_package_origin_count': len(root_pins['package_origins']),
    'workflow_directory': str(flow), 'workflow_source_guard': guard,
    'database_sha256': database_before, 'database_read_only_unchanged': True,
    'numerical': numerical, 'saved_replay': replay, 'parent_admissions': attempt_evidence,
    'episodes': {role: {key: value for key, value in facts.items() if key not in ('observations', 'archive')}
        for role, facts in episodes.items()},
    'root_execution_tool_catalog': {'value': [], 'verified_by':
        'tests/test_bvbrc_genome_alignment_episode_flow.py::test_selected_library_three_slots_and_real_child_http_route',
        'test_sha256': expected['tests/test_bvbrc_genome_alignment_episode_flow.py'],
        'root_tool_actions': 0},
    'memory_limit_bytes': 20 * 1024**3, 'scratch_limit_bytes': 4 * 1024**3,
    'scratch_bytes': sum(p.stat().st_size for p in OWN.rglob('*') if p.is_file()), 'wall_time_limit': None,
    'live_bvbrc': False, 'new_native_alignment': False, 'configured_model': False, 'hpc': False,
    'production_mutated_by_verifier': False, 'whole_tool_completion_claim': False, 'goal_completion_claim': False}
assert result['scratch_bytes'] < 4 * 1024**3
write(OUT, result)
print(json.dumps({key: result[key] for key in ('exit_code', 'distinct_passing_cases', 'frozen_candidate_paths_unchanged',
    'production_paths_unchanged', 'protected_application_files_unchanged', 'episodes', 'scratch_bytes')}, sort_keys=True))
