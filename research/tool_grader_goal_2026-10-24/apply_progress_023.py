"""Add current-source verification without rewriting prior checkpoints."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
path = HERE / 'WORK_STATUS.json'
raw = path.read_bytes()
before = hashlib.sha256(raw).hexdigest()
assert before == '8d06ee86dfae3efe524061a5d31ed7d4ac0e99bf1088827e098667a736f477fd'
assert not (HERE / 'PROGRESS_UPDATE_023.json').exists()
work = json.loads(raw)
old = deepcopy(work)


def hashed(relative):
    return {'path': relative, 'sha256': hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()}


returns_path = 'verification/tool_graders_bvbrc_alignment_returns_2026-10-25/TEST_004.json'
cache_path = 'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25/CONTRACT_REUSE_VERIFICATION_035.json'
returns = json.loads((ROOT / returns_path).read_text())
cache = json.loads((ROOT / cache_path).read_text())
assert returns['returncode'] == 0 and returns['source_unchanged']
assert returns['counts'] == dict(tests=563, errors=0, failures=0, skipped=0)
for source, digest in returns['source_after'].items():
    assert hashed(source)['sha256'] == digest, source
for receipt in cache['receipts']:
    assert hashed(receipt['path']) == receipt
assert cache['returncode'] == 0 and cache['counts'] == dict(tests=140, errors=0, failures=0, skipped=0)
for source, change in cache['source_changes_from_review031'].items():
    assert hashed(source)['sha256'] == change['current_sha256']
for xml_path, count in ((returns['junit'], 563), (cache['receipts'][0]['path'], 140)):
    suite = ET.parse(ROOT / xml_path).getroot().find('testsuite')
    assert len(suite.findall('testcase')) == count
    assert all(int(suite.attrib[k]) == 0 for k in ('errors', 'failures', 'skipped'))

evidence_id = 'MSA-METACATS-CURRENT-SOURCE-VERIFICATION-023'
evidence = {
    'id': evidence_id,
    'kind': 'current_source_host_binding_and_pure_validation_verification',
    'summary': 'Current-source suite004 passed563 checks without source changes:396 host/library/return checks plus56 bundle-resolution and111 saved-projection checks. Separate pure-contract/custody/publication suite passed140 checks, including10 new validation-reuse checks. The suites overlap and their totals are not summed.',
    'qualification': 'The full selected Workflow test009 remains running and is not claimed passed. Its predecessor006/007 interruptions are preserved in additive receipts; they were deliberate measured-repair interruptions, not timeouts or scientific failures. No live BV-BRC execution is established. All source-input, deployed-version and live-resource gaps from022 remain. No complete scientific tool is claimed.',
    'adapter_pins_after': cache['adapter_pins_after'],
    'reports': [hashed(p) for p in (returns_path, returns['junit'], returns['log'], cache_path,
        'verification/tool_graders_bvbrc_msa_metacats_implementation_2026-10-25/CONTRACT_VALIDATION_REUSE_033.md',
        'verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/INTERRUPTED_ATTEMPTS_008.json')],
}
assert evidence_id not in {r['id'] for r in work['verification_evidence']}
identities = {'C-L204-MSA', 'C-L205-MetaCATS'}
for row in work['rows']:
    if row['id'] in identities:
        row['integration_verification'] = '563_current_source_host_library_bundle_projection_return_checks_passed_full_Workflow009_running'
        row['evidence_ids'].append(evidence_id)
        row['note'] += (' Update023:563 current-source checks passed, including all56 bundle-resolution and111 projection checks; no deselected cases. '
            'The separate140-check contract/custody suite overlaps this suite and is not added to its total. '
            'Pure complete-value/schema validation reuse changed the adapter dependency pin toff78054bed87443c624bcd3051e033c44a1c028c5de9e17e94429cbd53b495f6; native values, calculations and external custody checks remain unchanged. '
            'Full Workflow009 is running; prior interrupted attempts006/007 and original manifests remain permanent evidence. No full Workflow or live-resource completion is claimed.')
for row in work['resource_bindings']:
    if row['id'] in {identity + '::api' for identity in identities}:
        row['integration_verification'] = '563_current_source_host_library_bundle_projection_return_checks_passed_full_Workflow009_running'
        row['evidence_ids'].append(evidence_id)
work['verification_evidence'].append(evidence)
assert len(work['rows']) == len(old['rows']) == 308
assert len(work['resource_bindings']) == len(old['resource_bindings']) == 288
assert work['complete_scientific_tools_claimed'] == old['complete_scientific_tools_claimed'] == 0
changes = []
for group in ('rows', 'resource_bindings'):
    original = {r['id']: r for r in old[group]}
    assert set(original) == {r['id'] for r in work[group]}
    changes.extend({'group': group, 'id': r['id'], 'before': original[r['id']], 'after': deepcopy(r)}
        for r in work[group] if r != original[r['id']])
updated = (json.dumps(work, indent=2) + '\n').encode()
record = {
    'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before, 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'previous_goal_turn_classification': 'no progress: answered the user\'s binding-versus-method_loop question by inspecting existing evidence; no implementation change in that question turn.',
    'current_continuation_progress': 'Verified completed563-check stable-source suite and140-check contract/custody suite against current files and XML; recorded exact scope without claiming full Workflow completion. Confirmed existing test PID1044688 live rather than restarting it.',
    'changes': changes, 'added_evidence': [evidence], 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': 0,
}
with (HERE / 'PROGRESS_UPDATE_023.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
path.write_bytes(updated)
print(json.dumps({'checkpoint': 23, 'changed_rows_and_bindings': len(changes),
    'scope_rows': 308, 'resource_bindings': 288, 'status_sha256': record['new_status_sha256']}))
