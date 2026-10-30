"""Record terminal evidence without changing the fixed tool scope."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def report(path):
    return {'path': path, 'sha256': sha(ROOT / path)}


raw = STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '0d74f925e55eddc96a93ee26e9fd0ed6a2eaf746af06b33d4ca6767bf5548e08'
assert not (HERE / 'PROGRESS_UPDATE_039.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope_sha = sha(scope_path)
scope = json.loads(scope_path.read_text())
authority = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
assert sha(authority) == work['authority_sha256']
p = 'verification/tool_graders_bvbrc_proteome_directional_integration_2026-10-25_182/'
c = 'verification/tool_graders_bvbrc_comparative_systems_implementation_2026-10-25_186/'
f = 'verification/tool_graders_bvbrc_fastqutils_contract_2026-10-25_193/'
for name, value in read(p + 'BASELINE_001.json').items():
    assert sha(ROOT / name) == value, name
assert not (ROOT / (p + 'APPLICATION_RECEIPT_001.json')).exists()
pw = read(p + 'final_workflow_001/receipt.json')
assert pw['passed'] and pw['exit_code'] == 0 and not pw['changed_sources']
assert pw['case_counts'] == {'passed': 2, 'failed': 0, 'error': 0, 'skipped': 0}
assert pw['source_count'] == 952
for name, value in read(p + 'FREEZE_001.json')['sources'].items():
    assert sha(ROOT / (p + 'candidate/' + name)) == value, name
cp = read(c + 'package_verification_002/receipt.json')
assert cp['passed'] and cp['installed_exit_code'] == 0 and not cp['changed_sources']
assert cp['source_count'] == 1045
for name, value in read(c + 'package_verification_002/source_after.json').items():
    assert sha(ROOT / (c + 'candidate/' + name)) == value, name
pt = read(c + 'evidence_p/P_TERMINAL_RECEIPT_003.json')
assert pt['pytest']['exit_code'] == 0 and pt['pytest']['result'].startswith('127 passed')
assert pt['source_snapshot_unchanged']
it = read(c + 'evidence_i/FINAL_TERMINAL_002.json')
assert it['source_snapshot_unchanged'] and it['result'] == '2 passed, 14 deselected in 187.16s'
assert it['exit_code'] is None  # Do not invent the lost tool-session exit code.
assert it['junit']['summary']['failures'] == it['junit']['summary']['errors'] == '0'

proteome = {
    'id': 'PROTEOME-DIRECTIONAL-WORKFLOW-PASS-039',
    'kind': 'frozen_candidate_actual_Workflow_verified_host_still_pending',
    'summary': 'The two actual shared-Workflow tests passed in 4004.05 seconds, exit0, all952 sources unchanged. Existing737 unit cases and installed-package evidence remain. No182 production application has occurred; final host verification has not yet supplied a terminal receipt.',
    'qualification': 'Controlled transport and scripted choices exercised real provider/publication/communication. No live GenomeComparison job or deployed producer/input association is claimed. Expensive application binding validation is under separate measured investigation; method_loop behavior is unchanged.',
    'reports': [report(p + name) for name in ('final_workflow_001/receipt.json', 'final_workflow_001/pytest.xml', 'FREEZE_001.json', 'final_host_001/command.json')],
}
comparative = {
    'id': 'COMPARATIVE-SYSTEMS-PROVIDER-PACKAGE-AND-RETURNS-039',
    'kind': 'frozen_candidate_provider_package_and_typed_history_verified_Workflow_pending',
    'summary': 'Final provider127 tests pass. I implements selected API binding, exact original metadata/content custody, lossless publication with separate original failure context, and all seven typed fact families. Final-pin targeted history tests pass; final root Workflow verification is running. The installed wheel probe passes against unchanged1045 sources. Production is unchanged.',
    'numerical_example': 'Native3/(2*2)*100=75 remains separate from later4/(3*3)*100=44.44444444444444; native reference2/4 remains separate from later3/4; active genome count is measured0; reference release remains unknown.',
    'corrections': 'The original history test incorrectly selected a new download after its practical assignment completed. The corrected fixture leaves an explicitly requested artifact unacquired, verifies valid partial information and preserves prior admitted history. A separate test verifies completed-assignment rejection. No production continuation rule changed. Package001 built correctly but its probe passed JSON lists into tuple-only ABI inputs; corrected probe002 reuses the exact wheel and passes.',
    'qualification': 'I013 JUnit and final log establish two completed passing cases, but the lost tool-session exit code remains null. Earlier overlapping test runs are retained and are not summed as unique coverage. Remote execution, deployed producing identity and immutable remote Data snapshots remain unverified.',
    'reports': [report(c + name) for name in ('PROJECTION_FAILURE_CONTEXT_CLOSURE_005.md', 'ROOT_PROVIDER_REVIEW_002.json', 'evidence_p/P_HANDOFF_003.md', 'evidence_p/P_TERMINAL_RECEIPT_003.json', 'evidence_p/FILLED_PROVIDER_RESULT_003.json', 'evidence_i/I_HANDOFF_001.md', 'evidence_i/I_OWNED_FILE_MANIFEST_001.json', 'evidence_i/FINAL_TERMINAL_002.json', 'evidence_i/FILLED_TYPED_HISTORY_003.json', 'package_verification_001/receipt.json', 'package_verification_002/receipt.json', 'final_workflow_001/command.json')],
}
fastq = {
    'id': 'FASTQUTILS-CONTRACT-REVIEW-039',
    'kind': 'native_format_and_interface_design_only_no_grader_implementation',
    'summary': 'A source-grounded FastqUtils sheet/parser/calculator contract is drafted. Root identified pre-acquisition selector, missing-value/cardinality, identity and workload-boundary gaps. Fresh195 is closing those interfaces before coding assignments. No new FastqUtils parser, calculator or production result path is claimed.',
    'qualification': 'Root initially said OriginalTask omitted submitted parameters; that was factually wrong and is corrected additively in ROOT_INTERFACE_REVIEW_002.md. Existing authenticated submitted_parameters and submitted_start_parameters must be used; no new provenance requirement is justified by that mistake.',
    'reports': [report(f + name) for name in ('CONTRACT_001.md', 'WORKLOADS_001.md', 'ROOT_INTERFACE_REVIEW_002.md')],
}
added = [proteome, comparative, fastq]
assert not {e['id'] for e in added}.intersection(e['id'] for e in work['verification_evidence'])
work['verification_evidence'].extend(added)
for row in work['rows']:
    if row['id'] == 'C-L206-GenomeComparison':
        row['integration_verification'] = '737unit_installed_facade_and_two_actual_Workflow_cases_pass_final_host_pending'
        row['evidence_ids'].append(proteome['id'])
        row['note'] += ' Update039: actual Workflow2pass with952unchanged sources; final host verification remains pending. No182production application. Original live-service and producer/input association limits remain.'
    elif row['id'] == 'C-L207-ComparativeSystems':
        row['overall'] = 'candidate_provider_typed_returns_and_installed_package_verified_final_Workflow_pending'
        row['tool_information'] = 'candidate_real_API_tool_information_and_selected_operation_binding_implemented'
        row['metadata_extractor'] = 'candidate_qualified_Data_extraction_and_actual_host_possession_tested'
        row['production_result_binding'] = 'candidate_actual_publication_and_own_received_typed_returns_implemented_not_applied'
        row['integration_verification'] = 'provider127pass_installed_package_pass_final_pin_history_JUnit_pass_full_Workflow_running'
        row['evidence_ids'].append(comparative['id'])
        row['note'] += ' Update039: P127pass; original failure context preserved separately through v2 publication and saved validation. I selected binding and seven-family typed delivery implemented; final-pin31prior passing cases plus2targeted passing cases documented without claiming lost shell exit code. Installed package probe002pass;001probe ABI error retained. Full root Workflow running; production unchanged; no live service claim.'
    elif row['id'] == 'C-L209-FastqUtils':
        row['numerical_sheet'] = 'source_grounded_contract_drafted_interface_review_in_progress_no_implementation'
        row['native_parser'] = 'native_formats_examined_contract_only_no_implementation'
        row['metadata_extractor'] = 'explicit_metadata_join_contract_under_review_no_implementation'
        row['deterministic_calculator'] = 'numerical_components_drafted_contract_only_no_implementation'
        row['evidence_ids'].append(fastq['id'])
        row['note'] += ' Update039:193source-grounded contract drafted;195closing exact pre-acquisition selectors, missing payloads, metadata/identity ports and independent workload ownership. Not a working grader. OriginalTask submitted-parameter omission claimed by root was false and corrected additively.'
for row in work['resource_bindings']:
    if row['id'] == 'C-L206-GenomeComparison::api':
        row['integration_verification'] = '737unit_installed_facade_and_two_actual_Workflow_cases_pass_final_host_pending'
        row['evidence_ids'].append(proteome['id'])
    elif row['id'] == 'C-L207-ComparativeSystems::api':
        row['production_result_binding'] = 'candidate_selected_API_publication_and_typed_returns_implemented_not_applied'
        row['integration_verification'] = 'provider127_and_installed_package_pass_typed_history_tested_full_Workflow_running'
        row['evidence_ids'].append(comparative['id'])
    elif row['id'] == 'C-L209-FastqUtils::api':
        row['evidence_ids'].append(fastq['id'])

changes = []
for group, count in (('rows', 308), ('resource_bindings', 288)):
    assert len(work[group]) == count
    assert [r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]]
    previous = {r['id']: r for r in original[group]}
    changes.extend({'group': group, 'id': r['id'], 'before': previous[r['id']], 'after': deepcopy(r)}
                   for r in work[group] if r != previous[r['id']])
assert len(changes) == 6 and work['complete_scientific_tools_claimed'] == 0
assert sha(scope_path) == scope_sha
updated = (json.dumps(work, indent=2) + '\n').encode()
record = {
    'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': hashlib.sha256(raw).hexdigest(),
    'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'scope_sha256_unchanged': scope_sha, 'scope_changes': False,
    'previous_goal_turn_classification': 'no_progress_wording_clarification_only',
    'current_progress': 'Confirmed terminal proteome Workflow and ComparativeSystems installed-package results, reviewed exact final provider/typed-return interfaces, and continued separate contract/application work. Both remaining long verification jobs were polled live; neither was stopped or restarted.',
    'changes': changes, 'added_evidence': added,
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': 0,
}
with (HERE / 'PROGRESS_UPDATE_039.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps({'checkpoint': 39, 'changed_rows_and_bindings': len(changes),
                  'status_sha256': record['new_status_sha256']}))
