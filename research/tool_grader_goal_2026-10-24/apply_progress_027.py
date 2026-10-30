"""Record saved validation, actual host integration and pending Workflow runs."""
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
assert before == 'ee7e80300b69ada441fe4fad207e5300fe706066efe701a4298f4a0fd078af4a'
assert not (HERE / 'PROGRESS_UPDATE_027.json').exists()
work = json.loads(raw)
old = deepcopy(work)


def hashed(name):
    return {'path': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}


def junit(name):
    suites = list(ET.parse(ROOT / name).getroot().iter('testsuite'))
    return {key: sum(int(s.get(key, '0')) for s in suites)
            for key in ('tests', 'failures', 'errors', 'skipped')}


structure = 'verification/tool_graders_bvbrc_genome_alignment_saved_structure_2026-10-25/'
boundary = 'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/'
host = 'verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/'
flow = 'verification/tool_graders_bvbrc_genome_alignment_episode_flow_2026-10-25/'
assert junit(structure + 'REGRESSION_001.xml') == {
    'tests': 1160, 'failures': 0, 'errors': 0, 'skipped': 0}
assert junit(structure + 'STRICT_EF_001.xml') == {
    'tests': 6, 'failures': 0, 'errors': 0, 'skipped': 0}
assert junit(boundary + 'RECEIPT_CHAIN_015.xml') == {
    'tests': 83, 'failures': 0, 'errors': 0, 'skipped': 0}
host_receipts = [host + 'pytest_' + number + '.xml' for number in ('003', '004', '005')]
assert [junit(p) for p in host_receipts] == [
    {'tests': 5, 'failures': 1, 'errors': 0, 'skipped': 0},
    {'tests': 5, 'failures': 1, 'errors': 0, 'skipped': 0},
    {'tests': 4, 'failures': 0, 'errors': 0, 'skipped': 0}]
passed_host_cases = set()
for name in host_receipts:
    for case in ET.parse(ROOT / name).getroot().iter('testcase'):
        if not any(case.find(kind) is not None for kind in ('failure', 'error', 'skipped')):
            passed_host_cases.add((case.get('classname'), case.get('name')))
assert len(passed_host_cases) == 12
assert junit(boundary + 'HOST_LIBRARY_016.xml')['failures'] == 3
assert junit(boundary + 'LIBRARY_PRESENTATION_017.xml')['failures'] == 1
assert junit(boundary + 'GENOME_PRESENTATION_018.xml') == {
    'tests': 1, 'failures': 0, 'errors': 0, 'skipped': 0}

genome_id = 'GENOME-ALIGNMENT-HOST-SAVED-VALIDATION-027'
genome = {
    'id': genome_id, 'kind': 'actual_host_and_saved_typed_return_verification',
    'summary': 'Separate saved structural validators preserve original numerical producer checks; 1160 regression tests pass, including 121 new cases. Six strict saved E/F tests also pass and overlap that regression. The actual API host now supplies authenticated native receipt dependencies, registers the GenomeAlignment adapter, exposes substantive tool information, and routes original typed facts through both own and received return consumers. Twelve distinct host cases pass across three disjoint run portions, covering all four retained formats, zero versus missing values, content possession, wrong task/receipt/current acquisition, saved replay, explicit recalculation and later-partial recovery.',
    'qualification': 'Controlled service responses and scripted original selections with real Store/Journal/custody/publication, not live BV-BRC or a completed configured-model Workflow. Root corrected actual TaskInfo purpose and Workspace.get manifest association after the first real-host failure;83 focused tests passed after that change. The1160 regression predates this C/host correction. Host003 and004 each retain one test-expectation failure, corrected in subsequent runs; there is no single12-pass invocation. The separate full Workflow is running. Live execution and full goal completion remain unverified.',
    'filled_examples': {'v4_native_coverage': {'numerator': 690, 'denominator': 693},
        'backbone_unions': [50, 49, 19], 'bbcols_selected_union': 52,
        'xmfa_identity': {'numerator': 40, 'denominator': 48},
        'missing_original_source_relationship': None, 'measured_zero_gap_count': 0},
    'passed_host_cases': [list(value) for value in sorted(passed_host_cases)],
    'reports': [hashed(name) for name in (
        structure + 'HANDOFF_001.md', structure + 'REGRESSION_001.xml',
        structure + 'STRICT_EF_001.xml', structure + 'STRUCTURE_001.xml',
        boundary + 'HOST_INTEGRATION_014.md', boundary + 'NATIVE_RECEIPT_CHAIN_015.md',
        boundary + 'RECEIPT_CHAIN_015.xml', boundary + 'HOST_LIBRARY_016.xml',
        boundary + 'LIBRARY_PRESENTATION_017.xml', boundary + 'GENOME_PRESENTATION_018.xml',
        host + 'pytest_001.xml', host + 'pytest_002.xml', *host_receipts,
        host + 'SOURCE_COMPARISON_004.json', host + 'SAVED_TRACE_003.json',
        host + 'SAVED_TRACE_004.json', flow + 'RUN_COMMAND_001.json',
        flow + 'PROCESS_HANDLE_001.json')],
    'library_and_presentation_receipts': {
        'HOST_LIBRARY_016': '39passed/3failed: three fixture calls omitted required start_parameters',
        'LIBRARY_PRESENTATION_017': '7passed/1failed: corrected invocation cases pass; new presentation assertion expected the wrong outer state',
        'GENOME_PRESENTATION_018': 'corrected presentation assertion passes; no numerical or production validation relaxed'},
}

prompt_id = 'SHARED-ROLE-PROMPT-GAP-027'
prompt = {
    'id': prompt_id, 'kind': 'inspected_unfinished_communication_requirement',
    'summary': 'providers._SessionConnection._presentation calls the TASK/STEERING renderer only for published scientific contexts; other contexts still use json.dumps(context). Scientific rendering checks do not establish all-role prompt completion. Full engineering Workflow fixtures use scripted Choices.complete and call the real scientific renderer separately, bypassing the model connection dispatch.',
    'qualification': 'This is an inspected remaining requirement, not a completed repair. No runtime, prompt dispatch, estimator, evidence-axis or method_loop behavior was changed for this finding. Plan and trace each affected template before implementing a correction; preserve detailed TASK and concise decision-specific STEERING.',
    'reports': [hashed('gene_annotation_episode/providers.py'),
        hashed(boundary + 'EPISODE_VERIFICATION_016.md'),
        hashed('tests/test_bvbrc_genome_alignment_episode_flow.py')],
}
for evidence in (genome, prompt):
    assert evidence['id'] not in {r['id'] for r in work['verification_evidence']}
    work['verification_evidence'].append(evidence)

for row in work['rows']:
    if row['id'] == 'C-L202-GenomeAlignment':
        row.update(
            overall='real_host_and_saved_typed_returns_verified_full_Workflow_running_live_unverified',
            tool_information='actual_name_description_resources_and_substantive_instructions_bound_with_typed_contract',
            invocation_contract='real_selected_start_app2_task_info_Workspace_metadata_capability_and_download_bound_controlled_native_responses_verified',
            metadata_extractor='actual_original_receipts_explicit_content_and_Workspace_manifest_chain_bound_and_verified',
            production_result_binding='registered_native_bundle_sheet_calculators_and_own_received_typed_return_consumers_bound',
            numerical_verification='1160_regression_passes_before_host_receipt_repair_83_C_checks_after_repair_12_actual_host_cases_pass_across_disjoint_runs',
            integration_verification='four_native_formats_actual_host_and_original_parent_admission_verified_complete_Workflow_running')
        row['evidence_ids'].extend([genome_id, prompt_id])
        row['note'] += (' Update027:strict saved replay is repaired without weakening original numerical producer validation. '
            'Actual host tests exposed and corrected TaskInfo purpose and the Workspace.get-to-manifest receipt chain. '
            'Twelve distinct host cases now pass across003/004/005, retaining original failures; current ownership and '
            'historical parent-admitted values remain distinct under later partial recovery. Actual tool information, '
            'registry and return consumers are connected. New full Workflow starts with prospective current pins; '
            'it is not yet a passed suite. Published scientific rendering is verified separately; other model-context '
            'roles still have the JSON fallback and need receiver-specific prompt work. No live-service or full-tool claim.')
    elif row['id'] in ('C-L204-MSA', 'C-L205-MetaCATS'):
        row['integration_verification'] = 'previous_closed_MSA_run_and_saved_reader_preserved_new_three_case_Workflow_running_after_shared_source_repair'
        row['evidence_ids'].extend([genome_id, prompt_id])
        row['note'] += (' Update027:shared saved-structure repair is complete and production sources are frozen for '
            'the fresh12-test MSA/MetaCATS/XMFA Workflow run. The original failed fixture receipt remains unchanged. '
            'No complete-suite pass or all-role prompt-rendering verification is inferred from scientific-only checks.')

rows = {row['id']: row for row in work['rows']}
for row in work['resource_bindings']:
    if row['id'] == 'C-L202-GenomeAlignment::api':
        source = rows['C-L202-GenomeAlignment']
        for key in ('invocation_contract', 'production_result_binding', 'integration_verification'):
            row[key] = source[key]
        row['evidence_ids'].extend([genome_id, prompt_id])
    elif row['id'] in ('C-L204-MSA::api', 'C-L205-MetaCATS::api'):
        row['integration_verification'] = 'prior_closed_MSA_and_saved_return_evidence_preserved_new_full_Workflow_running'
        row['evidence_ids'].extend([genome_id, prompt_id])

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
record = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-25',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': before, 'new_status_sha256': hashlib.sha256(updated).hexdigest(),
    'current_progress': 'Recorded saved-validation repair, actual native host integration and typed parent returns, exact original receipt corrections, library and scientific presentation checks. Launched two independently scoped full Workflow verifications against frozen production sources. Recorded the real non-scientific-context JSON fallback as unfinished communication work.',
    'changes': changes, 'added_evidence': [genome, prompt], 'scope_changes': False,
    'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
with (HERE / 'PROGRESS_UPDATE_027.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
path.write_bytes(updated)
print(json.dumps({'checkpoint': 27, 'changed_rows_and_bindings': len(changes),
    'scope_rows': 308, 'resource_bindings': 288,
    'distinct_host_cases_passed': len(passed_host_cases),
    'status_sha256': record['new_status_sha256']}))
