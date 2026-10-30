"""Retain terminal receipts and copies of actual saved forms; no scientific work."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET

E = Path(__file__).resolve().parent
C = E.parent / 'candidate'
NOW = datetime.now(timezone.utc).isoformat()

def load(path):
    return json.loads(path.read_text())

def save(name, value):
    (E / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def xml_result(stem):
    suite = ET.parse(E / (stem + '.xml')).getroot().find('testsuite')
    return {'summary': dict(suite.attrib), 'testcases': [dict(row.attrib) for row in suite.findall('testcase')]}

before = load(E / 'FINAL_SOURCE_BEFORE_002.json')
after = load(E / 'FINAL_SOURCE_AFTER_002.json')
assert before['files'] == after['files']
assert before['provider_pin'] == after['provider_pin']
for row in after['files']:
    assert sha(C / row['path']) == row['sha256']
for row in load(E.parent / 'evidence_p/P_VERIFICATION_INPUTS_003.json')['dependencies']:
    assert sha(C / row['path']) == row['sha256']
assert not Path('/proc/1094950').exists()
assert not Path('/proc/1094957').exists()

manifest = dict(after)
manifest.update(captured_at=NOW, capture_note='Final I handoff; candidate ownership released. Runtime/tests/fixtures frozen for root Workflow and installed-wheel verification.')
save('I_OWNED_FILE_MANIFEST_001.json', manifest)

before012 = load(E / 'FINAL_SOURCE_BEFORE_001.json')
after012 = load(E / 'FINAL_SOURCE_AFTER_001.json')
assert before012['files'] == after012['files']
assert before012['provider_pin'] == after012['provider_pin']
base = 'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests /home/chia/repos/gene_annotation_episode/.venv/bin/python -m pytest -q '
receipt012 = {
    'captured_at': NOW, 'cwd': str(C), 'session_id': 6562, 'exit_code': 1,
    'command': base + 'tests/test_bvbrc_comparative_systems_publication.py tests/test_bvbrc_comparative_systems_returns.py tests/test_bvbrc_comparative_systems_host_inputs.py -p no:cacheprovider --basetemp=../evidence_i/pytest_012 --junitxml=../evidence_i/pytest_012.xml > ../evidence_i/pytest_012.log 2>&1',
    'result': '31 passed, 1 failed in 190.03s', 'junit': xml_result('pytest_012'),
    'log_sha256': sha(E / 'pytest_012.log'), 'junit_sha256': sha(E / 'pytest_012.xml'),
    'provider_pin': before012['provider_pin'], 'source_snapshot_unchanged': True,
    'failure_cause': 'The test selected another download after validated completion of its original practical assignment. The actual host correctly rejected api_assignment_already_completed before a new publication. No production correction was made.',
    'retained_cause_evidence': 'LATEST_FAILURE_REASON_001.json',
    'correction': 'LATEST_HISTORY_TEST_FIX_003.patch; a partial original assignment with a specific requested unacquired pathway output now tests latest-history behavior. Completed-assignment rejection is tested separately.',
}
save('FINAL_TERMINAL_001.json', receipt012)
receipt013 = {
    'captured_at': NOW, 'cwd': str(C), 'session_id': None, 'exit_code': None,
    'command': base + "tests/test_bvbrc_comparative_systems_returns.py -k 'latest_partial_keeps or completed_original_assignment' -p no:cacheprovider --basetemp=../evidence_i/pytest_013 --junitxml=../evidence_i/pytest_013.xml > ../evidence_i/pytest_013.log 2>&1",
    'terminal_evidence': 'The original test process completed its final pytest summary and JUnit, then both recorded process IDs ceased to exist. Its unified-exec session ID was lost in context compaction, so no exit code is invented. No stop/restart occurred.',
    'original_process_ids': [1094950, 1094957], 'live_processes': [],
    'result': '2 passed, 14 deselected in 187.16s', 'junit': xml_result('pytest_013'),
    'log_sha256': sha(E / 'pytest_013.log'), 'junit_sha256': sha(E / 'pytest_013.xml'),
    'provider_pin': before['provider_pin'], 'source_snapshot_unchanged': True,
    'before_manifest': 'FINAL_SOURCE_BEFORE_002.json', 'after_manifest': 'FINAL_SOURCE_AFTER_002.json',
    'runtime_changed_after_pytest012': False,
    'root_verification': {'workflow_session': 61821, 'installed_wheel_session': 64821, 'state_at_release': 'running under root ownership; results reported by root'},
}
save('FINAL_TERMINAL_002.json', receipt013)
save('ACTIVE_VERIFICATION_STATE_002.json', {'captured_at': NOW, 'state': 'terminal', 'live_i_processes': [], 'receipt': 'FINAL_TERMINAL_002.json', 'candidate_ownership': 'released; source freeze remains active for root verification'})

def extract(folder, name, expected_forms, classification, terminal):
    root = E / folder
    db = sqlite3.connect('file:' + str(root / 'state/state.sqlite3') + '?mode=ro', uri=True)
    forms = []
    for eid, raw in db.execute('SELECT episode_id,form FROM runtime_forms WHERE form IS NOT NULL'):
        form = json.loads(raw)
        if any(key.startswith('facts_') for key in form):
            forms.append({'episode_id': eid, 'form': form})
    db.close()
    assert len(forms) == expected_forms
    if expected_forms == 2:
        assert forms[0]['form'] == forms[1]['form']
    publications = []
    for path in sorted(root.glob('api-service-execution/**/bundle_publication.json')):
        body = load(path)
        if not body['value']['result_record_refs']:
            continue
        inputs = load(path.with_name('publication_inputs.json'))
        publications.append({'path': str(path), 'sha256': sha(path),
            'original_inputs_sha256': sha(path.with_name('publication_inputs.json')),
            'adapter_implementation_sha256': inputs['adapter_implementation_sha256'],
            'publication': body, 'publication_inputs': inputs})
    save(name, {'classification': classification, 'terminal_receipt': terminal,
        'typed_returns': forms, 'original_publications': publications,
        'new_observations_from_parsing_projection_or_forwarding': 0})

extract('pytest_011/test_actual_preparation_task_m0', 'FILLED_TYPED_RETURN_002.json', 2,
    'Actual executor/custody/P/N/C publication and typed admission through two parent boundaries; 005 v2 wrapper. Controlled choices/transport associate retained source-executed synthetic family bytes with synthetic task123. This historical positive result uses pin58ed93 before the later P diagnostic-location correction; it is not a live service or shared Workflow run.',
    'FOCUSED_TERMINAL_001.json; this case passed within43passed/1unrelated-failed/1deselected')
extract('pytest_013/test_latest_partial_keeps_orig0', 'FILLED_TYPED_HISTORY_003.json', 1,
    'Actual final-pin executor/custody/native publication and typed parent admission. Original selected numeric fields remain available while a specific requested pathway output is unacquired. A later selected malformed-native download creates a partial latest result; the original admitted form remains unchanged. Controlled transport and synthetic task123 association, not live execution.',
    'FINAL_TERMINAL_002.json')

attachment = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
contract_root = E.parent.parent / 'tool_graders_bvbrc_comparative_systems_contract_2026-10-25_185'
reset_paths = [attachment] + [E.parent / p for p in ('IMPLEMENTATION_HANDOFF_001.md','DATA_EXTRACTOR_HANDOFF_002.md','INTEGRATION_BOUNDARY_CLOSURE_003.md','REFERENCE_BINDING_CLOSURE_004.md','PROJECTION_FAILURE_CONTEXT_CLOSURE_005.md')] + [contract_root / p for p in ('BINDING_AND_WORKLOADS_001.md','FINAL_MAPPING_AND_PARENT_BOUNDARY_003.md')]
save('FINAL_CONTEXT_RESET_001.json', {'captured_at': NOW, 'reread': 'Authoritative objective lines1-55 and entire DESIGN PRINCIPLES lines351-536 verbatim; then exact I binding, parent boundary and186 additive001-005 contracts. Full original attachment and complete185 additive order were read before implementation.', 'sources': [{'path':str(p),'sha256':sha(p)} for p in reset_paths]})
print(json.dumps({'terminal': receipt013['result'], 'i_live_processes': [], 'owned_files': len(manifest['files']), 'provider_pin': manifest['provider_pin'], 'examples': ['FILLED_TYPED_RETURN_002.json','FILLED_TYPED_HISTORY_003.json']}))
