"""Record exact FastqUtils application and completed verification; preserve pending scope."""
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
V = ROOT / 'verification'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reports(base, names):
    return [dict(path=str((base / n).relative_to(ROOT)), sha256=sha(base / n)) for n in names]


raw = STATUS.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '74a5df4ae5d29f7dfe5115f18d114d8ca7e1c7ba115f0bf38a708962f5616eac'
assert not (HERE / 'PROGRESS_UPDATE_049.json').exists()
work = json.loads(raw)
original = deepcopy(work)
scope_path = HERE / work['scope_file']
scope, scope_hash = read(scope_path), sha(scope_path)

p = V / 'tool_graders_fastqutils_combined_verification_2026-10-26_217'
r = read(p / 'suite_receipt.json')
assert r['passed'] and r['distinct_test_cases'] == 562 and r['test_files'] == 20
assert r['exit_code'] == 0 and not any(r[k] for k in ('failures', 'errors', 'skipped', 'deselections'))
assert not any(r['changed'].values())
package = read(p / 'package_verification_001/receipt.json')
assert package['passed'] and package['forbidden_call_count'] == 0
assert package['changed_parameters_preserve_original'] and package['same_parameter_saved_recalculation']
assert package['saved_return_without_calculators'] and package['dependency_count'] == 36
assert sha(Path(package['wheel_path'])) == package['wheel_sha256']
seal = read(p / 'SEAL_001.json')
assert seal['file_count'] == len(seal['files']) == 3643
for name, expected in seal['files'].items():
    assert sha(p / name) == expected
combined = dict(id='FASTQUTILS-COMBINED-PACKAGE-049',
    kind='all20_suites_and_installed_package_verified_exact_composed_source',
    summary='All 562 distinct cases in all 20 FastqUtils suites passed once, with no exclusions. '
        'The installed wheel passed native quantities, historical return schemas, saved same-parameter '
        'and changed-R1 recalculation, and typed replay with calculation disabled. All 3643 sealed '
        'evidence hashes and the wheel hash were checked by root. Legacy SAMstat fractions were '
        '10/11 and 5/11, current fractions 9/10 and 4/10, and changed R1 fractions 8/9 and 4/9.',
    qualification='These are component/provider/package checks using retained native and synthetic '
        'inputs, not a live BV-BRC service or complete new SAMstat episode run. Report fractions '
        'retain native record populations, unknown original-input scope and MAPQ255 limitations.',
    reports=reports(p, ['HANDOFF_001.md', 'HANDOFF_001.json', 'SEAL_001.json', 'suite_receipt.json',
        'suite_results.xml', 'package_verification_001/receipt.json', 'NUMERICAL_EVIDENCE_001.json']))

p = V / 'tool_graders_bvbrc_fastqutils_episode_path_2026-10-25_202'
seal = read(p / 'final_208_001/SEALED_RECEIPT_001.json')
assert seal['passed_tests'] == 14 and seal['exit_code'] == 0
assert seal['owned_action_count'] == seal['observation_count'] == 18
assert seal['root_admission_succeeded'] and seal['all_scoped_input_and_dependency_hashes_unchanged']
manifest = p / 'final_208_001/EVIDENCE_FILES_001.json'
assert sha(manifest) == seal['evidence_manifest_sha256']
files = read(manifest)
assert len(files) == 2607
for name, expected in files.items():
    assert sha(manifest.parent / name) == expected
workflow = dict(id='FASTQUTILS-BASELINE-WORKFLOW-049',
    kind='shared_Workflow_selected_actions_credit_continuation_and_typed_admission_verified',
    summary='The preserved exact208 baseline run completed normally: 14 tests passed, including '
        'the actual Workflow with 18 selected completed actions and 18 observations. Seven fact '
        'families and values 2, 5/9, 0.001 and 0.75 reached root with requested component order '
        '[gc, errors, retained]. Practical endpoints immediately retained exact-zero future '
        'expectation while preserving the final actual gains. Root verified all 2607 sealed files.',
    qualification='Controlled service transport and model choices; parent/scientific continuation '
        'and zero scientific-credit projection were controlled, while practical controllers ran. '
        'This proves the exact208 baseline path, not later SRA/SAMstat coverage, live service, '
        'model planning, W05 aggregation or whole-tool completion.',
    reports=reports(p, ['RELEASE_001.md', 'RELEASE_FILES_001.json',
        'final_208_001/SEALED_RECEIPT_001.json', 'final_208_001/EVIDENCE_FILES_001.json',
        'final_208_001/receipt.json', 'final_208_001/junit.xml', 'final_208_001/terminal_audit.json']))

p = V / 'tool_graders_fastqutils_combined_2026-10-25_216'
applied = read(p / 'PRODUCTION_APPLICATION_001.json')
assert applied['production_changed'] and applied['changed_paths'] == 189
assert not any(applied[k] for k in ('annotation_score_changed', 'method_loop_changed', 'historical_records_changed'))
for item in applied['applied_files']:
    assert sha(ROOT / item['path']) == item['after_sha256']
first, second = (read(p / f'production_checks_00{i}/receipt.json') for i in (1, 2))
assert first['tests'] == 42 and first['failures'] == 2 and first['errors'] == 0
assert second['passed'] and second['tests'] == 6 and second['failures'] == second['errors'] == 0
assert not first['changed_sources'] and not second['changed_sources']
latest = {}
for run in ('production_checks_001', 'production_checks_002'):
    for case in ET.parse(p / run / 'results.xml').iter('testcase'):
        latest[(case.get('classname'), case.get('name'))] = not any(
            case.find(kind) is not None for kind in ('failure', 'error', 'skipped'))
assert len(latest) == 42 and all(latest.values())
application = dict(id='FASTQUTILS-PRODUCTION-APPLICATION-049',
    kind='exact_tested_components_and_shared_binding_applied_focused_regressions_passed',
    summary='Applied 189 exact tested paths: FastqUtils package modules/assets, fixtures, tests '
        'and six shared integration/package paths. Actual registration, publication, saved '
        'validation and seven-family typed returns now exist in production. Forty-two distinct '
        'focused regression cases have passing final results. Initial run had 40 pass and two '
        'failures from an incomplete test double; after adding its four missing return handlers, '
        'all six cases in that test module passed. Runtime source was not changed for that fix.',
    qualification='The original failing run remains preserved. The other 36 regression cases '
        'were not rerun because their sources were unchanged. New SAMstat full-Workflow and '
        'legacy host verification remain owned by running worker218; no pending result is '
        'claimed here. Live BV-BRC job verification remains unfinished.',
    reports=reports(p, ['APPLICATION_PLAN_001.json', 'PRODUCTION_APPLICATION_001.json',
        'production_checks_001/receipt.json', 'production_checks_001/results.xml',
        'production_checks_001/stdout.log', 'CHECK_PRODUCTION_002.py',
        'production_checks_002/receipt.json', 'production_checks_002/results.xml']) +
        reports(ROOT, ['tests/test_api_service_result_ordering.py']))

evidence = [combined, workflow, application]
assert not {e['id'] for e in evidence} & {e['id'] for e in work['verification_evidence']}
work['verification_evidence'].extend(evidence)
for group in ('rows', 'resource_bindings'):
    for row in work[group]:
        if row['id'].split('::')[0] != 'C-L209-FastqUtils':
            continue
        row['evidence_ids'].extend(e['id'] for e in evidence)
        row['invocation_contract'] = 'production_selected_prepare_submit_status_workspace_contracts_tested_controlled_transport_not_live_service'
        row['native_parser'] = 'production_native_parsers_including_SRA_and_current_legacy_SAMstat_562combined_cases_passed'
        row['production_result_binding'] = 'applied_registration_publication_saved_validation_and_seven_family_typed_returns'
        row['numerical_verification'] = '562distinct_combined_cases_and_installed_wheel_passed_saved_recalculation_without_IO'
        row['integration_verification'] = 'baseline_actual_Workflow18actions18observations_passed_Cutadapt_SRA_host_passed_new_SAMstat_Workflow_pending'
        if group == 'rows':
            row['overall'] = 'implemented_applied_component_package_and_baseline_episode_verified_new_SAMstat_episode_and_live_service_unfinished'
            row['tool_information'] = 'production_name_description_API_resources_substantive_instructions_and_actual_catalog_contract_tested'
            row['numerical_sheet'] = 'production_native_and_calculated_quantities_populated_explicit_populations_assumptions_unknowns_preserved'
            row['deterministic_calculator'] = 'production_composition_quality_original_read_mapping_SAMstat_report_mapping_retention_consistency_verified'
            row['note'] += ' Update049: ' + ' '.join(e['summary'] + ' ' + e['qualification'] for e in evidence)
        else:
            row['native_format_observed'] = 'retained_native_producer_outputs_and_official_source_verified_no_successful_live_BV_BRC_job'

changes = []
for group, count in (('rows', 308), ('resource_bindings', 288)):
    assert len(work[group]) == count
    assert [r['id'] for r in work[group]] == [r['id'] for r in original[group]] == [r['id'] for r in scope[group]]
    previous = {r['id']: r for r in original[group]}
    changes.extend(dict(group=group, id=r['id'], before=previous[r['id']], after=deepcopy(r))
        for r in work[group] if r != previous[r['id']])
assert len(changes) == 2 and work['complete_scientific_tools_claimed'] == 0
assert sha(scope_path) == scope_hash
updated = (json.dumps(work, indent=2) + '\n').encode()
record = dict(schema='tool_grader_progress_update_v1', date='2026-10-26',
    recorded_at=datetime.now(timezone.utc).isoformat(), author='root',
    previous_status_sha256=hashlib.sha256(raw).hexdigest(), new_status_sha256=hashlib.sha256(updated).hexdigest(),
    scope_sha256_unchanged=scope_hash, scope_changes=False, changes=changes, added_evidence=evidence,
    inventory_maintenance_counted_as_implementation_progress=False,
    specific_pending_NCBI_job_verification_included=False, complete_scientific_tools_claimed=0,
    previous_goal_turn_classification='progress_terminal_regression_evidence_changed_next_action')
with (HERE / 'PROGRESS_UPDATE_049.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
STATUS.write_bytes(updated)
print(json.dumps(dict(checkpoint=49, changed_rows_and_bindings=len(changes),
    status_sha256=record['new_status_sha256'], distinct_final_passing_regressions=len(latest))))
