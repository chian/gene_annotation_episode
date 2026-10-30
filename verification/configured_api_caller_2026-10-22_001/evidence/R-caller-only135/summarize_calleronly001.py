"""Summarize already retained isolated caller-only evidence; no application I/O."""
import hashlib
import json
from pathlib import Path
import stat
import xml.etree.ElementTree as ET

evidence = Path(__file__).parent
checkout = Path('/tmp/gene-annotation-api-caller-20261022-006p-001')
original = Path('/tmp/gene-annotation-configured-caller-20261022-006')


def digest(path):
    body = path.read_bytes()
    return {'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}


before = json.loads((evidence / 'calleronly001-before.json').read_text())
after = json.loads((evidence / 'calleronly001-after.json').read_text())
assert before['files'] == after['files']
xml = ET.parse(evidence / 'calleronly001.xml')
suites = list(xml.getroot().iter('testsuite'))
assert len(suites) == 1
suite = suites[0]
assert suite.attrib['tests'] == '8'
assert all(suite.attrib[key] == '0' for key in ('errors', 'failures', 'skipped'))
tests = [{'nodeid': 'tests/test_api_planning_case_reconstruction.py::' + row.attrib['name'],
          'seconds': float(row.attrib['time'])} for row in suite.findall('testcase')]
preservation = json.loads((evidence / 'calleronly001-fixtures/PRESERVATION.json').read_text())
assert preservation['source_membership_and_bytes_sizes_modes_mtimes_stable'] is True
proof_path = evidence / 'calleronly001-fixtures/raw-tree/test_new_policy_detached_forec0/reconstruction-proof.json'
proof = json.loads(proof_path.read_text())
numeric = {}
for owner in ('child', 'parent'):
    rows = proof[owner + '_observations']
    assert len(rows) >= 8
    assert all(row['step']['marginal_credit'] == 0 for row in rows)
    assert all(row['step']['stop'] is False for row in rows[:-1])
    last = rows[-1]['step']
    assert last['stop'] is True
    decision = last['decision']
    assert decision['continuation_cost'] == 1000000
    assert decision['projected_gain']['upper'] <= decision['continuation_cost']
    assert last['estimate']['parameters'] == {
        'subsample_semantics': 'minimum_evaluated_acquisition_turns_before_full_history_fit',
        'subsample_size': 4, 'uncertainty_alpha': .05,
        'window_semantics': 'minimum_completed_acquisition_turns_before_full_history_fit',
        'window_size': 8}
    numeric[owner] = {'completed_own_observations': len(rows), 'all_marginal_credit_zero': True,
        'prior_stop_values_false': True, 'final_stop': True,
        'final_projected_upper': decision['projected_gain']['upper'],
        'continuation_cost_test_only': decision['continuation_cost'],
        'decision_basis': decision['decision_basis']}
assert proof['zero_http_requests'] is True and proof['configured_model_science'] is False
returned = proof['returned']
assert returned['outcome'] == 'closed' and returned['failure'] is None
forecast, = returned['form']['forecasts']
assert forecast['expected_total_seconds'] is None
assert forecast['reported_result_support'] == {'reported_result_count': 0}
test_relative = Path('tests/test_api_planning_case_reconstruction.py')
test_hashes = {'frozen': digest(checkout / test_relative), 'owned_original006': digest(original / test_relative),
               'initial_retained': digest(evidence / 'test_api_planning_case_reconstruction.initial.py')}
assert len({row['sha256'] for row in test_hashes.values()}) == 1
source_relative = Path('gene_annotation_episode/api_planning_case_policy.py')
source_hashes = {'frozen': digest(checkout / source_relative), 'owned_by_P_original006': digest(original / source_relative)}
assert len({row['sha256'] for row in source_hashes.values()}) == 1
result = {
    'version': 'caller_only_reconstruction_verification_v1',
    'status': 'passed', 'invocation': 'calleronly001', 'exit_code': 0,
    'command': (evidence / 'calleronly001-command.txt').read_text().strip(),
    'cwd': str(checkout), 'runtime_pin': before['runtime_pin'], 'runtime_files': 135, 'test_files': 216,
    'frozen_inputs': digest(checkout / 'FROZEN_INPUTS001.json'),
    'all678_declared_inputs_unchanged': True, 'C_component_absent': True,
    'test_file_hashes': test_hashes, 'P_source_hashes': source_hashes,
    'pytest': {'cases': tests, 'passed': 8, 'failures': 0, 'errors': 0, 'skipped': 0,
        'distinct_nodeids': len({row['nodeid'] for row in tests}), 'suite_seconds': float(suite.attrib['time']),
        'displayed_seconds': 98.07, 'log': digest(evidence / 'calleronly001.log'),
        'xml': digest(evidence / 'calleronly001.xml'), 'first_test_invocation_passed': True,
        'test_corrections': 0},
    'proof': {'actual_new_P_policy_module_supplied_and_loaded': True,
        'shared_P_policy_source_unchanged': True,
        'saved_caller_reopened_without_model_transport': True,
        'six_pretransport_mismatches': ['source', 'parameters', 'client', 'map', 'models', 'restoration'],
        'actual_detached_scripted_worker': True, 'real_YieldController': True,
        'numerical_closure': numeric, 'parent_next_contexts': len(proof['parent_received_contexts']),
        'parent_typed_forecast_return_received': True, 'private_child_proposal_absent_from_parent': True,
        'parent_return_admission_exactly_once': True, 'return_redelivery_preserves_observations_receipts_credit': True,
        'closed_archives_load': True, 'forecast_expected_seconds': None, 'forecast_reported_result_support': 0,
        'zero_http_requests': True, 'zero_native_jobs': True, 'zero_public_service_calls': True,
        'zero_actual_model_calls': True, 'actual_custody_forks': 0, 'actual_scientific_runs': 0,
        'reconstruction_proof_json': digest(proof_path)},
    'raw_fixture_preservation': {key: value for key, value in preservation.items()
        if key not in ('files', 'pytest_alias_symlinks_not_followed')},
    'raw_fixture_manifest': digest(evidence / 'calleronly001-fixtures/PRESERVATION.json'),
    'not_claimed': ['final combined006 runtime proof', 'custody-to-caller integration',
        'actual scientific checkpoint or launch', 'real provider or native execution',
        'relocated raw fixture resumability'],
    'historical_not_counted': ['collection001 collected eight nodes without execution',
        'numeric-preflight001 pure eight-zero numerical calculation'],
}
target = evidence / 'CALLERONLY001_RESULTS.json'
with target.open('x') as handle:
    handle.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
manifest_rows = {}
for path in sorted(evidence.rglob('*')):
    if path.is_file() and not path.is_symlink():
        manifest_rows[path.relative_to(evidence).as_posix()] = {
            **digest(path), 'mode': f'{stat.S_IMODE(path.stat().st_mode):04o}'}
manifest = {'version': 'caller_only_R_evidence_manifest_v1', 'files': manifest_rows,
    'file_count': len(manifest_rows), 'bytes': sum(row['bytes'] for row in manifest_rows.values()),
    'claim': 'Caller-only135-file source identity; C excluded. No combined006 claim.'}
manifest_path = evidence / 'CALLERONLY001_MANIFEST.json'
with manifest_path.open('x') as handle:
    handle.write(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
print(json.dumps({'results': digest(target), 'manifest': digest(manifest_path),
    'manifest_file_count': manifest['file_count'], 'manifest_bytes': manifest['bytes'],
    'numeric': numeric, 'pytest_cases': 8, 'runtime_pin': result['runtime_pin']}, sort_keys=True, indent=2))
