"""Record fixed Rfam-row progress from completed, inspected verification.

This records implementation evidence. It changes neither scope nor completion
criteria and executes no scientific tool, episode, parser or calculator.
"""
raise SystemExit('Historical progress mutation retired; current progress is not reconstructed from old goal attachments or notes.')
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TRACKER = ROOT / 'research/tool_grader_goal_2026-10-24'
AUTHORITY = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
AUTHORITY_SHA = '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def write_new(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def relative(path):
    return str(path.relative_to(ROOT))


RECEIPTS = {
    'numerical': 'verification/tool_graders_rfam_report_2026-10-26_242/final_010/verification-receipt.json',
    'report_publication_returns': 'verification/tool_graders_rfam_report_returns_2026-10-26_244/tests_003/verification-receipt.json',
    'report_workflow': 'verification/tool_graders_rfam_report_workflow_2026-10-26_245/tests_002/receipt.json',
    'legacy_publication_returns': relative(HERE / 'run_010_old_publication_returns/receipt.json'),
    'service_table': relative(HERE / 'run_011_service_table/receipt.json'),
    'legacy_workflow': relative(HERE / 'run_012_old_workflow/receipt.json'),
    'original_live_replay': relative(HERE / 'run_013_original_replay/receipt.json'),
}


def verification():
    results, all_tests = {}, set()
    for label, name in RECEIPTS.items():
        path = ROOT / name
        receipt = load(path)
        assert receipt['returncode'] == 0, name
        assert receipt['policy'] == {'memory_bytes': 20 * 1024**3,
            'scratch_bytes': 4 * 1024**3, 'wall_seconds': None}, name
        before = receipt.get('source_hashes_before', receipt.get('source_sha256_before'))
        after = receipt.get('source_hashes_after', receipt.get('source_sha256_after', receipt.get('source_sha256')))
        assert isinstance(before, dict) and isinstance(after, dict), name
        changed = sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))
        consumed_tests = {str(Path(arg.split('::')[0]).relative_to(ROOT))
            for arg in receipt['command'] if arg.startswith(str(ROOT / 'tests'))}
        relevant = {key for key in after if key.startswith('gene_annotation_episode/')
            or key in consumed_tests}
        assert not relevant.intersection(changed), (name, changed)
        assert all((ROOT / key).is_file() and sha(ROOT / key) == after[key] for key in relevant), name
        xml_path, = path.parent.glob('*.xml')
        cases = ET.parse(xml_path).findall('.//testcase')
        assert cases and not any(case.find(tag) is not None for case in cases
            for tag in ('failure', 'error', 'skipped')), name
        identities = {(case.attrib.get('classname'), case.attrib['name']) for case in cases}
        assert len(identities) == len(cases), name
        overlap = all_tests.intersection(identities)
        all_tests.update(identities)
        results[label] = {'receipt': name, 'receipt_sha256': sha(path),
            'junit': relative(xml_path), 'junit_sha256': sha(xml_path),
            'passed': len(cases), 'overlap_with_prior_suites': len(overlap),
            'changed_monitored_files': changed,
            'consumed_tests_and_monitored_production_unchanged': True,
            'qualification': ('Only the unconsumed new replay test and the runner source changed; '
                'consumed test files and monitored production modules stayed unchanged.' if changed else
                'All monitored source hashes stayed unchanged.')}
    return {'suites': results, 'unique_passing_test_identities': len(all_tests),
        'qualification': 'These tests cover the listed Rfam numerical, publication and episode paths; '
            'their count does not establish full-goal or all-resource completion.'}


def main():
    assert sha(AUTHORITY) == AUTHORITY_SHA
    assert not (TRACKER / 'PROGRESS_UPDATE_052.json').exists()
    verified = verification()
    assert verified['unique_passing_test_identities'] == 409
    status_path, scope_path = TRACKER / 'WORK_STATUS.json', TRACKER / 'SCOPE.json'
    status, original = load(status_path), status_path.read_bytes()
    scope_sha = sha(scope_path)
    assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
    assert status['authority_sha256'] == AUTHORITY_SHA
    previous = load(TRACKER / 'PROGRESS_UPDATE_051.json')
    assert previous['numerical_grader_progress_tally']['after'] == 71
    row, = [value for value in status['rows'] if value['id'] == 'A-L068-rfam-batch']
    resource, = [value for value in status['resource_bindings'] if value['id'] == 'A-L068-rfam-batch::api']
    assert row['overall'] == 'not_assessed'
    before_row, before_resource = deepcopy(row), deepcopy(resource)
    evidence_ids = ['RFAM-NUMERICAL-052', 'RFAM-API-RETURNS-052', 'RFAM-EPISODE-052']
    row.update(overall='api_numerical_episode_path_verified_prompt_work_remaining',
        source_presence='source_present',
        tool_information='configured_real_four_field_api_contracts_present',
        invocation_contract='original_single_or_explicit_batch_submit_status_selected_fetch_bound',
        numerical_sheet='verified_native_json_table_report_filled_examples',
        native_parser='verified_distinct_single_json_batch_tblout_and_batch_out_formats',
        metadata_extractor='verified_original_occurrences_coordinates_and_explicit_metadata_bindings',
        deterministic_calculator='verified_separate_pure_calculators_and_saved_recalculation',
        production_result_binding='api_retained_publication_and_requested_typed_parent_returns_verified',
        numerical_verification='181_numerical_and58_service_table_tests_with_retained_native_examples',
        integration_verification='96_legacy_and40_report_publication_return_tests_15_legacy_and18_report_workflow_tests_1_original_live_replay',
        live_resource_verification='actual_three_query_API_job_table_returns_and_separate_original_job_report_GET',
        evidence_ids=evidence_ids,
        note='Update052: Rfam API operations retain full native output, separate numerical sheets/calculations, '
            'and requested typed projections through results->scientific_process->annotation. The fixed row now '
            'contributes one entry to the carried-forward numerical implementation tally (71->72). '
            '409 unique passing test identities across seven qualified suites cover the current components. '
            'The actual live job used scripted decisions and table output; its publisher changed during that run. '
            'A later current-code replay preserves all original archives, histories, returns and outcomes with '
            'network/parser/calculator/model calls forbidden. The new report path is verified using exact retained '
            'native bytes plus explicit synthetic empty/partial cases, not another fresh live Workflow. '
            'Batch JSON without query identities and single unheaded text remain explicitly ungraded; no order-based '
            'query association or full-model length is invented. General role TASK/STEERING and selected resource '
            'instruction delivery, configured-model scientific investigation and full-goal completion remain unfinished. '
            'No W05, literature, annotation-formula, native HPC or separate E-L291 model-acquisition completion claimed.')
    resource.update(invocation_contract='verified_explicit_original_input_and_selected_representation',
        production_result_binding='verified_full_native_and_numerical_publication_requested_returns',
        integration_verification='verified_scripted_actual_Workflow_both_parent_boundaries_and_replay',
        live_resource_verification='one_live_three_query_batch_and_original_job_report_acquisition',
        prerequisites_present='public_Rfam_batch_endpoint_used_successfully',
        native_format_observed='single_json_cmscan1.1.5_tblout_format1_and_native_out', evidence_ids=evidence_ids)
    reports = {
        evidence_ids[0]: ['verification/tool_graders_rfam_report_2026-10-26_242/HANDOFF.md',
            'verification/tool_graders_rfam_report_2026-10-26_242/HANDOFF_MANIFEST.json',
            'verification/tool_graders_rfam_report_2026-10-26_242/examples_011/native.sheet.json',
            'verification/tool_graders_rfam_report_2026-10-26_242/examples_011/native.calculation.json'],
        evidence_ids[1]: ['verification/tool_graders_rfam_report_returns_2026-10-26_244/HANDOFF.md',
            'verification/tool_graders_rfam_report_returns_2026-10-26_244/FINAL_SOURCE_AND_EVIDENCE_001.json'],
        evidence_ids[2]: ['verification/tool_graders_rfam_report_workflow_2026-10-26_245/REPORT.md',
            'verification/tool_graders_rfam_report_workflow_2026-10-26_245/SUMMARY.json',
            'verification/tool_graders_rfam_live_workflow_2026-10-26_243/REPORT.md',
            'verification/tool_graders_rfam_live_workflow_2026-10-26_243/live_001/SUMMARY.json',
            'verification/tool_graders_rfam_live_workflow_2026-10-26_243/live_001/SOURCE_QUALIFICATION.json'],
    }
    summaries = [
        'Native cells, model/query spans, coordinate correspondence, posterior bins, consensus comparisons, '
            'insertions/deletions and original-query/strand populations remain separate. Signed bias is preserved. '
            'Full model coverage remains unavailable without bound metadata; native model endpoints are not denominators.',
        'Selected acquisition retains original submission, native response, parse, full sheet and calculation. '
            'Only frozen requested numerical rows and population facts enter authenticated immediate-parent returns. '
            'Old forms remain unchanged; report model names use their own nullable identity field.',
        'Actual live table Workflow plus controlled JSON/table/report Workflows verify both scientific return boundaries, '
            'one observation per selected own action and production practical terminal-zero behavior. Synthetic partial '
            'report work preserves useful values without a completion proof. Original live run replays under current code.'
    ]
    new_evidence = []
    for identifier, summary in zip(evidence_ids, summaries):
        entry = {'id': identifier, 'kind': 'implemented_and_verified_with_explicit_resource_qualifications',
            'summary': summary, 'qualification': row['note'],
            'reports': [{'path': name, 'sha256': sha(ROOT / name)} for name in reports[identifier]]}
        assert not any(old['id'] == identifier for old in status['verification_evidence'])
        status['verification_evidence'].append(entry)
        new_evidence.append(entry)
    assert status['complete_scientific_tools_claimed'] == 0
    encoded = (json.dumps(status, indent=2, ensure_ascii=False) + '\n').encode()
    update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-26',
        'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
        'previous_status_sha256': hashlib.sha256(original).hexdigest(),
        'new_status_sha256': hashlib.sha256(encoded).hexdigest(),
        'scope_sha256_unchanged': scope_sha, 'scope_changes': False,
        'changes': [{'group': 'rows', 'id': row['id'], 'before': before_row, 'after': deepcopy(row)},
            {'group': 'resource_bindings', 'id': resource['id'], 'before': before_resource, 'after': deepcopy(resource)}],
        'added_evidence': new_evidence,
        'numerical_grader_progress_tally': {'before': 71, 'after': 72, 'added_row_ids': [row['id']],
            'meaning': previous['numerical_grader_progress_tally']['meaning']},
        'verification': verified,
        'remaining_fixed_rows_outside_tally': 236,
        'completed_work': ['Separate Rfam native numerical sheets, parsers/metadata and calculators',
            'Child-owned API submission/status/selected acquisition, full retained numerical publication',
            'Requested typed returns through both scientific parent boundaries',
            'One real live table job; current-code saved replay; retained-native report Workflow verification'],
        'unfinished_work': ['General role TASK/STEERING and selected resource-instruction prompt work',
            'Remaining236 fixed entries and their resource-specific integration/verification',
            'Separate E-L291 Rfam model acquisition and seven Infernal preparation/inspection rows',
            'Four previously identified shared root-tool/history test failures',
            'Configured-model scientific investigation and full original-goal completion'],
        'excluded_claims': ['Fresh live v3 report Workflow', 'Independent detached recovery from these tests',
            'Scientific annotation credit or W05 implementation', 'Literature graders', 'HPC execution', 'Full-goal completion'],
        'inventory_maintenance_counted_as_implementation_progress': False,
        'accounting_executed_scientific_tools': False, 'accounting_executed_tests': False,
        'specific_pending_NCBI_job_verification_included': False, 'complete_scientific_tools_claimed': 0}
    write_new(HERE / 'VERIFICATION_014.json', verified)
    write_new(TRACKER / 'PROGRESS_UPDATE_052.json', update)
    assert status_path.read_bytes() == original and sha(scope_path) == scope_sha
    status_path.write_bytes(encoded)
    assert sha(status_path) == update['new_status_sha256'] and sha(scope_path) == scope_sha
    print(json.dumps({'rows': len(status['rows']), 'resource_bindings': len(status['resource_bindings']),
        'numerical_tally': 72, 'unique_passing_tests': verified['unique_passing_test_identities'],
        'full_goal_complete': False}))


if __name__ == '__main__':
    main()
