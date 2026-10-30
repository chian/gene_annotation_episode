"""Record actual chromatin/HIC evidence without changing scope or tool counts."""
raise SystemExit("Historical progress mutation retired; current accounting is maintained separately.")

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATUS = HERE / 'WORK_STATUS.json'
UPDATE = HERE / 'PROGRESS_UPDATE_108.json'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not UPDATE.exists()
previous = read(HERE / 'PROGRESS_UPDATE_107.json')
before_sha, scope_sha = sha(STATUS), sha(HERE / 'SCOPE.json')
assert before_sha == previous['new_status_sha256']
assert scope_sha == previous['scope_sha256_unchanged']
status = read(STATUS)
original = deepcopy(status)
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 112
assert status['verified_bound_local_tool_mode_rows'] == 42
assert sha(Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')) == status['authority_sha256']

attempts = [
    ('tool_graders_chromatin_workflow_2026-10-27_451/check001', 6, 0, 0,
     'complete_scripted_Cooler_Workflow_at_original_pre_HIC_snapshot'),
    ('tool_graders_chromatin_workflow_2026-10-27_451/check002', 0, 2, 5,
     'current_provider_schema_failure_before_native_start'),
    ('tool_graders_chromatin_hic_binding_2026-10-27_457/check001', 3, 6, 0,
     'retained_failed_runtime_pinning_and_builtin_module_test'),
    ('tool_graders_chromatin_hic_binding_2026-10-27_457/check002', 9, 0, 0,
     'actual_native_producer_and_retained_worker_not_full_Workflow'),
    ('tool_graders_chromatin_hic_records_2026-10-27_456/check007', 64, 0, 0,
     'focused_HIC_sheet_and_exact_legacy_return_boundaries'),
    ('tool_graders_chromatin_hic_records_2026-10-27_456/check005', 1, 0, 0,
     'actual_Cooler_producer_worker_old_form_and_receipt_replay'),
]
checks, reports = [], []
for relative, passed, failed, errors, meaning in attempts:
    directory = ROOT / 'verification' / relative
    receipt = read(directory / 'receipt.json')
    assert receipt['returncode'] == (1 if failed or errors else 0)
    assert receipt['terminal'] and receipt['quiescent']
    assert receipt['source_pins_unchanged'] and receipt['binary_pins_unchanged']
    assert receipt['metadata']['policy'] == {
        'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}
    group = receipt['metadata']['verified_cgroup']
    assert group['memory_max'] == 21474836480 and group['memory_swap_max'] == 0
    assert group['runtime_max'] == 'infinity'
    suite = ET.parse(directory / 'junit.xml').getroot().find('testsuite')
    assert suite is not None
    assert int(suite.attrib['tests']) == passed + failed + errors
    assert int(suite.attrib['failures']) == failed and int(suite.attrib['errors']) == errors
    assert int(suite.attrib['skipped']) == 0
    checks.append({'attempt': relative, 'passed': passed, 'failed': failed, 'errors': errors,
        'scope': meaning, 'source_pins_unchanged': True, 'binary_pins_unchanged': True,
        'checkout_changes': [row['after']['path'] for row in receipt.get('checkout_drift', [])]})
    for filename in ('receipt.json', 'source_pins_before.json', 'source_pins_after.json', 'junit.xml'):
        path = directory / filename
        reports.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path)})

summary = (
    'Original chromatin Cooler Workflow451/check001 passed all6 cases at its unchanged pre-HIC snapshot: '
    'selected actual execution, requested-only return, saved calculation after21 source/producer paths were removed, '
    'receiver authority, exact action credit/terminal zero, closed replay and useful partial results. '
    'Current-source451/check002 failed2 cases with5 setup errors before native start. Read-only probes establish '
    'that shared provider-schema conversion makes an optional native_runtime field required while a literal '
    'software-binding constraint excludes it; fresh458 is repairing this production transport defect. '
    'HIC457/check001 retained3pass6fail; probe001 identified unpinned mmap loaded by canonical-table helpers. '
    'After explicit runtime pinning and correcting one builtin-zlib test assumption,457/check002 passed all9 '
    'actual producer/worker cases: raw6/mean4/fold1.5, divisive mean3.25/fold24/13, genuine empty zero-denominator, '
    'insulation, saved recalculation without original HIC/native attempt, invalid runtime rejection, format-specific '
    'tool information and unchanged default Cooler dispatch.456 final focused checks passed64 and a separate '
    'actual Cooler producer/worker/old-form receipt replay passed1. Those are separate source snapshots, not one '
    'combined final suite. Root reviewed full HIC reader/records/table helpers and found/fixed present-weight '
    'validation after contact loss through456. H1 malformed-tail partial-retention repair and final parser checks '
    'continue. HIC full Workflow, model-facing text, other native formats/versions and HPC remain unfinished. '
    'Protein/genomic-overlap messages and received-input selection, historical failures and all other fixed rows '
    'remain open. Counts stay112/308,42local,196outside; W05/literature remain separate.')
evidence = {'id': 'CHROMATIN-WORKFLOW-HIC-BINDING-108',
    'kind': 'separately_pinned_workflow_component_and_failed_transport_evidence',
    'summary': summary, 'checks': checks, 'reports': reports}
assert evidence['id'] not in {item['id'] for item in status['verification_evidence']}
status['verification_evidence'].append(evidence)
tool_id = 'B-L124-analyze_chromatin_interactions'
row = next(item for item in status['rows'] if item['id'] == tool_id)
before = deepcopy(row)
row.update(
    tool_information='format_specific_local_information_verified_model_facing_work_unfinished',
    native_parser='Cooler_and_HIC_v9_checks_passed_HIC_final_partial_retention_verification_in_progress',
    production_result_binding='original_Cooler_Workflow_and_HIC_native_worker_verified_current_transport_repair_open',
    integration_verification='original_Cooler_Workflow_passed_current_provider_schema_failure_HIC_Workflow_unfinished')
row['evidence_ids'].append(evidence['id'])
row['note'] += ' Update108: ' + summary
assert all(a == b for a, b in zip(original['rows'], status['rows']) if a['id'] != tool_id)
assert original['resource_bindings'] == status['resource_bindings']
checklist = deepcopy(previous['work_item_states'])
for item in checklist:
    if item['id'] == 'U05':
        item['current_evidence'] += ' Update108: ' + summary
assert [(x['id'], x['original_item'], x['status']) for x in checklist] == [
    (x['id'], x['original_item'], x['status']) for x in previous['work_item_states']]
findings = deepcopy(previous['findings_requiring_repair'])
findings.append('Update108: current composed launch_local assignment has contradictory provider requirements '
    'for optional native_runtime and literal software;458 owns the narrow production transport repair. '
    'Original451 six-pass snapshot remains valid evidence; current full Workflow is unfinished.')
raw = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-27', 'author': 'root',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'previous_status_sha256': before_sha,
    'new_status_sha256': hashlib.sha256(raw).hexdigest(), 'scope_sha256_unchanged': scope_sha,
    'scope_changes': [], 'changes': [{'id': tool_id, 'before': before, 'after': deepcopy(row)}],
    'resource_binding_changes': [], 'added_evidence': [evidence],
    'numerical_grader_progress_tally': {'before': 112, 'after': 112, 'added_row_ids': [],
        'meaning': previous['numerical_grader_progress_tally']['meaning']},
    'verified_bound_local_tool_mode_rows': {'before': 42, 'after': 42},
    'remaining_fixed_rows_outside_tally': 196,
    'completed_work': ['Original Cooler Workflow6passed at recorded pre-HIC source snapshot.',
        'HIC actual native producer and retained-worker path9passed after exact mmap repair.',
        'Focused HIC sheet/return validation64passed; actual Cooler legacy receipt path1passed separately.'],
    'findings_requiring_repair': findings, 'work_item_states': checklist,
    'unfinished_work': [x['current_evidence'] for x in checklist if x['status'] != 'complete'],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': status['complete_scientific_tools_claimed']}
assert sha(STATUS) == before_sha and sha(HERE / 'SCOPE.json') == scope_sha
with UPDATE.open('x') as output:
    json.dump(update, output, indent=2, ensure_ascii=False)
    output.write('\n')
temporary = STATUS.with_name('.WORK_STATUS.108.writing')
with temporary.open('xb') as output:
    output.write(raw)
temporary.replace(STATUS)
print(json.dumps({'updated_tool_rows': 1, 'updated_resource_bindings': 0,
    'grader_tally': 112, 'verified_local_bindings': 42, 'remaining_rows': 196,
    'new_status_sha256': sha(STATUS)}))
