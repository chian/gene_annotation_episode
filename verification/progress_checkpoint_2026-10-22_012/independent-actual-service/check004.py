"""Read-only independent check; no application imports or raw-header output."""
from pathlib import Path
from urllib.parse import quote, quote_plus
import hashlib
import json
import re
import stat

ROOT = Path('/home/chia/repos/gene_annotation_episode')
PUB = ROOT / 'verification/hmmer_reported_timing_actual_service_2026-10-22_001'
OUT = Path(__file__).parent

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def load(name):
    return json.loads((PUB / name).read_bytes())

manifest_raw = (PUB / 'MANIFEST.json').read_bytes()
assert digest(manifest_raw) == '4b0c97d7442c05a600512c7594c39a443d9003c2b14c9efffeea9b824b234b20'
m = json.loads(manifest_raw)
assert len(m['members']) == 147
assert sum(v['bytes'] for v in m['members'].values()) == 922336
actual = {p.relative_to(PUB).as_posix() for p in PUB.rglob('*') if p.is_file()}
assert actual == set(m['members']) | {'MANIFEST.json'}
for relative, row in m['members'].items():
    p = PUB / relative
    assert p.is_file() and not p.is_symlink()
    raw = p.read_bytes()
    assert len(raw) == row['bytes'] and digest(raw) == row['sha256'], relative
    # Manifest declares hashes/sizes, not file modes; retain modes as custody facts.
report = ROOT / 'docs/HMMER_REPORTED_TIMING_ACTUAL_SERVICE_2026-10-22_001.md'
assert report.read_bytes() == (PUB / 'REPORT.md').read_bytes()
assert digest(report.read_bytes()) == '7a5e82689289921fe194778184f7a17c2136fa3a8a0153a05788c9e1a1350c7a'
mapping = load('ORIGINAL_TO_PUBLIC.json')
assert len(mapping['copied_originals']) == 128 and len(mapping['omitted_originals']) == 22
assert mapping['redacted_derivatives'] == []
private_values = set()
for row in mapping['copied_originals'] + mapping['omitted_originals']:
    original = Path(row['private_path'])
    raw = original.read_bytes()
    assert len(raw) == row['bytes'] and digest(raw) == row['sha256']
    if 'published_path' in row:
        assert raw == (PUB / row['published_path']).read_bytes()
    elif 'credential' in row['reason'] or 'transport' in row['reason'] or original.name == 'manifest.json':
        # Extract values only in memory. Never save or print raw headers/values.
        private_values.update(match.group(1).decode() for match in
            re.finditer(rb'(?i)sessionid\s*=\s*([^;\s,"\\]+)', raw))
assert private_values
forms = {x.encode() for value in private_values for x in
         (value, quote(value, safe=''), quote_plus(value, safe=''), json.dumps(value)[1:-1])}
for p in [*PUB.rglob('*'), report]:
    if p.is_file():
        raw = p.read_bytes()
        assert not any(value in raw for value in forms), 'private material in output'

checks = load('CHECKS.json')
assert checks['phase_count'] == 13 and checks['actual_phase_failure_count'] == 0
assert checks['source_file_count'] == 131
assert checks['selected_http_capture_count'] == 4
assert checks['operation_receipt_count'] == 5
assert checks['submission_claim_count'] == 1
assert checks['native_statistic_count'] == 0 and checks['reported_statistic_count'] == 1
assert checks['timing_source_count'] == 1
ledger = load('logical/timing-ledger.json')['tables']
history = load('logical/reported-history.json')['tables']
store = load('logical/store.json')
witness = load('logical/first-witness.json')
source = load('logical/timing-source.json')
for table in ['api_timing_bindings', 'api_timing_orders', 'api_timing_submission_intents',
              'api_timing_submission_bindings', 'api_timing_measurements']:
    assert len(ledger[table]) == 1
assert json.loads(ledger['api_timing_measurements'][0]['data']) == witness
assert witness == source['body']['witness'] == checks['first_witness']
assert witness['elapsed_seconds'] == 0.22888848185539246
assert witness['observed_at'] == '2026-10-22T07:31:19.992723+00:00'
assert witness['duration_measure'] == 'hmmer_reported_search_elapsed_seconds'
assert witness['observation_unit'] == 'logical_provider_job_reported_result'
intent = json.loads(ledger['api_timing_submission_intents'][0]['data'])
binding = json.loads(ledger['api_timing_submission_bindings'][0]['data'])
assert binding['intent_ref'] == intent['intent_ref'] == witness['intent_ref']
assert witness['start_context'] == intent['start_context']
assert binding['submission_operation_key'] == intent['submission_operation_key']
assert binding['submission_receipt_ref'] == checks['original_submit_receipt']['receipt_ref']
assert binding['remote_id'] == witness['remote_id'] == checks['remote_id']
assert witness['submission_binding_ref'] == binding['binding_ref']
assert len(history['reported_result_statistics']) == 1
assert not history['run_statistics'] and not history['execution_conditions']
statistic = json.loads(history['reported_result_statistics'][0]['data'])
assert statistic['elapsed_seconds'] == witness['elapsed_seconds']
assert statistic['observed_at'] == witness['observed_at']
assert statistic['source_sha256'] == digest(canonical(witness))
snapshots = {row['id']: json.loads(row['data']) for row in history['expectation_snapshots']}
assert snapshots[checks['initial_snapshot_ref']]['history_through_sequence'] == 0
assert snapshots[checks['initial_snapshot_ref']]['statistics'] == []
assert checks['final_forecast']['reported_result_support'] == {'reported_result_count': 1}
assert checks['final_forecast']['expected_total_seconds'] == witness['elapsed_seconds']
for name in ['job_ref', 'sample_ref', 'elapsed_seconds', 'outcome_support']:
    assert checks['final_forecast'][name] is None
assert len(store['claims']) == 1 and len(store['operations']) == 5
assert len(store['results']) == len(store['publications']) == 2
assert {row['page'] for row in store['results']} == {1, 2}
assert not [r for r in store['records'] if r['record_type'] in
            {'hypothesis', 'assessment', 'annotation', 'interpretation_account', 'native_execution'}]
assert source['body']['scope'] == json.loads(ledger['api_timing_orders'][0]['data'])['scope']
publications = [row['data']['result'] for row in store['publications']]
assert all(row['projection_failures'] == [] and row['page_count'] == 2 for row in publications)
assert sum(len(row['publication_rows']) for row in publications) == 8
assert {row['page'] for row in publications} == {1, 2}
record_ids = {r['id'] for r in store['records']}
for row in publications:
    for item in row['publication_rows']:
        assert item['record_ref'] in record_ids
        assert item['job_ref'] == witness['job_ref']
        assert item['request_sha256'] == witness['request_sha256']
        assert item['acquisition_receipt_ref'] == row['acquisition_receipt_ref']

guards = sorted(PUB.glob('phase-evidence/invocations/*/sources-after.json'))
assert len(guards) == 13
original_guard = json.loads(guards[0].read_bytes())['identity']
assert original_guard['runtime_implementation_sha256'] == 'cde521578e4531b93dcbe9e33eaf58881db867c0664c3cb9af93107d549e2623'
assert len(original_guard['source_files']) == 131
assert all(json.loads(p.read_bytes()) == {'identity': original_guard, 'unchanged': True} for p in guards)

result = {'version': 'independent_reported_timing_publication_check_v1', 'status': 'passed',
          'manifest_sha256': digest(manifest_raw), 'members': 147, 'bytes': 922336,
          'safe_originals_checked': 128, 'omitted_original_hashes_checked': 22,
          'phase_count': 13, 'reported_timing_identities': 1, 'reported_statistics': 1,
          'native_statistics': 0, 'published_pages': [1, 2], 'publication_witnesses': 8,
          'privacy_match_count': 0, 'raw_values_printed': False,
          'application_imports_or_calls': 0, 'database_opens': 0, 'network_model_native_calls': 0,
          'limitations': ['Partial derivative, no standalone replay DB.',
                          'Reported provider interval only; no physical-attempt, queue or turnaround claim.',
                          'No episode/controller/scientific demonstration.']}
(OUT / 'RESULTS.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print(json.dumps(result, sort_keys=True))
