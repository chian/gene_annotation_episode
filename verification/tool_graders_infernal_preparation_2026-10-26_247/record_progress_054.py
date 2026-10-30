"""Record the seven verified numerical preparation implementations, once."""
raise SystemExit('Historical progress mutation retired; current progress is not reconstructed from old goal attachments or notes.')
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'research/tool_grader_goal_2026-10-24'
STATUS = DIRECTORY / 'WORK_STATUS.json'
UPDATE = DIRECTORY / 'PROGRESS_UPDATE_054.json'
GOAL = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
BASE = 'verification/tool_graders_infernal_preparation_2026-10-26_247/'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def evidence(path):
    return {'path': path, 'sha256': sha((ROOT / path).read_bytes())}


def suite(directory, passed, failed=0):
    receipt_path = directory + '/receipt.json'
    receipt = json.loads((ROOT / receipt_path).read_text())
    cases = list(ET.parse(ROOT / directory / 'tests.xml').iter('testcase'))
    failures = [case for case in cases if case.find('failure') is not None or case.find('error') is not None]
    successes = [case for case in cases if case not in failures and case.find('skipped') is None]
    assert len(successes) == passed and len(failures) == failed, directory
    assert receipt['returncode'] == (1 if failed else 0), directory
    before, after = receipt['source_hashes_before'], receipt['source_hashes_after']
    return {'directory': directory, 'passed': passed, 'failed': failed,
        'failed_cases': [case.attrib for case in failures],
        'source_changes': [key for key in before if before[key] != after.get(key)],
        'receipt': evidence(receipt_path), 'junit': evidence(directory + '/tests.xml')}


before_bytes = STATUS.read_bytes()
status = json.loads(before_bytes)
assert status['authority_sha256'] == sha(GOAL.read_bytes())
scope_hash = sha((DIRECTORY / status['scope_file']).read_bytes())
assert scope_hash == '2f2d6670e3f89ecb980f87857b44d129751bad26471213b8bada9115960c1719'
assert json.loads((DIRECTORY / 'PROGRESS_UPDATE_053.json').read_text())['numerical_grader_progress_tally']['after'] == 72
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288

verification = [
    suite(BASE + 'final_boundary_009', 274, 1),
    suite(BASE + 'reference_boundary_011', 23),
    suite(BASE + 'final_nested_visibility_012', 3),
    suite(BASE + 'shared_receipts_008', 49, 8),
]
assert verification[0]['failed_cases'][0]['name'] == 'test_unrequested_results_reference_does_not_reopen_original_bundle'
assert verification[0]['source_changes'] == ['gene_annotation_episode/native_infernal_preparation_results.py']
assert not verification[1]['source_changes'] and not verification[2]['source_changes']
for directory in ('reference_boundary_011', 'final_nested_visibility_012'):
    receipt = json.loads((ROOT / BASE / directory / 'receipt.json').read_text())
    for name in ('episode_receipts', 'execution_episodes', 'native_infernal_preparation_results',
            'native_infernal_preparation_returns'):
        key = 'gene_annotation_episode/' + name + '.py'
        assert receipt['source_hashes_after'][key] == sha((ROOT / key).read_bytes()), key

nested_path = 'verification/tool_graders_infernal_preparation_nested_workflow_2026-10-26_257/VERIFICATION_001.json'
modes_path = 'verification/tool_graders_infernal_preparation_workflow_modes_2026-10-26_256/FINAL_EVIDENCE_001.json'
nested = json.loads((ROOT / nested_path).read_text())
assert nested['biological_observation_count'] == 0 and nested['annotation_count'] == 0
for directory, expected in (
    ('verification/tool_graders_infernal_preparation_nested_workflow_2026-10-26_257/stable_009', 48),
    ('verification/tool_graders_infernal_preparation_workflow_modes_2026-10-26_256/modes_003', 20),
):
    cases = list(ET.parse(ROOT / directory / 'tests.xml').iter('testcase'))
    assert len(cases) == expected and not any(
        case.find('failure') is not None or case.find('error') is not None
        or case.find('skipped') is not None for case in cases), directory

programs = ('cmbuild', 'cmcalibrate', 'cmconvert', 'cmemit', 'cmfetch', 'cmpress', 'cmstat')
notes = {
    'cmbuild': 'Build/refine paths verified; non-Stockholm training extraction and additional expert/clustering variants remain explicit unverified subcases.',
    'cmcalibrate': 'All six declared modes verified. Full sidecar/partition arrays retained. Absent original merge-partition producer requests and GC calibration provenance remain unknown.',
    'cmconvert': 'All five declared conversions verified. Opaque binary content is retained and validated without invented decoded populations; full binary/state-table equivalence is not claimed.',
    'cmemit': 'Three declared modes verified; generated data remain generated. Full node-level trace grading and exhaustive expert/truncation variants remain unverified subcases.',
    'cmfetch': 'Single-key, key-file and index paths verified, including missing-key diagnostics distinct from exit code. Prior supplied SSI provenance and complete binary index decoding remain unknown.',
    'cmpress': 'All four native index companions retain original source/attempt association and byte validation. Full binary index decoding and new downstream scientific consumption are not claimed by this batch.',
    'cmstat': 'All seven declared modes verified. Native and calculated values, signed residuals, rounding and missing calibration/cutoff inputs remain separate.',
}
qualification = (
    'Update054 adds seven implemented numerical preparation/validation rows to the carried-forward tally (72 to79). '
    'The27 declared local modes have actual native Workflow evidence;48 nested tests cover one mode per program through both scientific boundaries. '
    'The later metadata-only reference repair has23 passing focused cases and3 fresh nested requested-only cases. '
    'A preceding combined run retained274 passes and1 subsequently corrected source-membership failure; its results module changed during that run. '
    'Mode/nested runs retain their exact before/after hashes and three unrelated literature-file changes absent from their imported-module manifests. '
    'No annotation-confidence score or biological observation is created. This is numerical implementation progress, not whole-goal or every-variant completion. '
    'General TASK/STEERING/resource-instruction work, remaining required tools and resource deployments stay unfinished; W05 and literature graders remain separate.'
)
groups = {
    'INFERNAL-PREPARATION-LOCAL-MODES-054': (
        'Seven native preparation programs and27 declared modes; native values, separate saved-sheet calculations and actual selected execution.',
        [modes_path, 'verification/tool_graders_infernal_preparation_workflow_modes_2026-10-26_256/VERIFICATION_REPORT_001.md',
         'verification/tool_graders_infernal_preparation_workflow_modes_2026-10-26_256/modes_003/EVIDENCE_INDEX.json']),
    'INFERNAL-PREPARATION-NESTED-054': (
        'Actual selected tool information, native execution and requested forms through scientific_process and annotation, with original credit/continuation.',
        [nested_path, 'verification/tool_graders_infernal_preparation_nested_workflow_2026-10-26_257/VERIFICATION_001.md']),
    'INFERNAL-PREPARATION-VISIBILITY-054': (
        'Requested-only file visibility, typed failure facts, full fact authentication, metadata-only reference membership and original replay.',
        [BASE + 'final_boundary_009/receipt.json', BASE + 'reference_boundary_011/receipt.json',
         BASE + 'final_nested_visibility_012/receipt.json', BASE + 'REFERENCE_VISIBILITY_HANDOFF_002.md',
         'verification/tool_graders_receipt_regression_trace_2026-10-26_260/CAUSE_REPORT_001.md']),
}
added_evidence = [{'id': identifier, 'kind': 'local_numerical_preparation_path_verified_with_explicit_remaining_subcases',
    'summary': summary, 'qualification': qualification, 'reports': [evidence(path) for path in paths]}
    for identifier, (summary, paths) in groups.items()]
changes = []
for program in programs:
    identifier = 'A-L077-' + program
    row = next(item for item in status['rows'] if item['id'] == identifier)
    old = deepcopy(row)
    assert row['overall'] == 'implemented_components_full_integration_verification_in_progress'
    row.update(overall='local_numerical_preparation_path_verified_remaining_subcases_explicit',
        source_presence='source_present', tool_information='actual_four_field_information_and_callable_contract_delivery_verified',
        invocation_contract='verified_declared_modes_through_selected_local_native_execution',
        numerical_sheet='verified_filled_native_examples_and_explicit_unavailable_values',
        native_parser='verified_declared_formats_with_opaque_formats_explicit',
        metadata_extractor='verified_original_occurrence_associations_and_requested_projections',
        deterministic_calculator='verified_separate_saved_data_calculation_and_parameter_replay',
        production_result_binding='verified_existing_launch_local_results_and_two_scientific_boundaries',
        numerical_verification='verified_actual_native_and_partial_failure_examples',
        integration_verification='verified_scripted_native_mode_and_nested_typed_return_paths',
        live_resource_verification='verified_small_actual_local_native_jobs_no_hpc_deployment_claim',
        evidence_ids=list(dict.fromkeys(row['evidence_ids'] + list(groups))), note=qualification + ' ' + notes[program])
    changes.append({'group': 'rows', 'id': identifier, 'before': old, 'after': deepcopy(row)})
    resource = next(item for item in status['resource_bindings'] if item['id'] == identifier + '::local')
    old = deepcopy(resource)
    resource.update(invocation_contract='verified_original_selected_native_modes',
        production_result_binding='verified_native_sheet_calculations_and_requested_typed_returns',
        integration_verification='verified_scripted_actual_native_workflow_and_nested_returns',
        live_resource_verification='verified_actual_small_native_local_examples',
        prerequisites_present='verified_explicit_native_executable_and_input_identities',
        native_format_observed='retained_actual_mode_specific_native_artifacts',
        evidence_ids=list(dict.fromkeys(resource['evidence_ids'] + list(groups))))
    changes.append({'group': 'resource_bindings', 'id': resource['id'], 'before': old, 'after': deepcopy(resource)})
status['verification_evidence'].extend(added_evidence)
local_before = status['verified_bound_local_tool_mode_rows']
assert local_before == 25
status['verified_bound_local_tool_mode_rows'] = 32
after_bytes = (json.dumps(status, indent=2) + '\n').encode()
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-26',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': sha(before_bytes), 'new_status_sha256': sha(after_bytes),
    'scope_sha256_unchanged': scope_hash, 'scope_changes': False,
    'changes': changes, 'added_evidence': added_evidence, 'verification': verification,
    'count_change': {'verified_bound_local_tool_mode_rows': {'before': local_before, 'after': 32}},
    'numerical_grader_progress_tally': {'before': 72, 'after': 79,
        'added_row_ids': ['A-L077-' + name for name in programs],
        'meaning': 'Carried-forward numerical-grader implementation tally including supporting numerical validation; not whole-goal completion or a new unique-algorithm count.'},
    'remaining_fixed_rows_outside_tally': 229,
    'completed_work': [qualification],
    'unfinished_work': [
        'The unchanged remaining308-row scope, with229 rows outside the carried-forward implementation tally.',
        'The exact format/expert/deployment limitations retained separately on all seven rows.',
        'General role TASK/STEERING and selected resource instruction work, and other previously qualified integration/resource gaps.',
        'Eight obsolete shared receipt test expectations: seven removed root-tool calls and one retired scorer constructor; traced separately, not fixed or silently reclassified as passes.',
        'Separate E-L291 Pfam/InterPro/Rfam model acquisition and remaining native preparation/scientific/API operations.',
    ],
    'excluded_claims': ['W05 or final annotation scoring changes', 'literature grader implementation',
        'HPC deployment', 'configured-model scientific investigation', 'whole-checkout frozen verification',
        'full308-goal completion'],
    'inventory_maintenance_counted_as_implementation_progress': False,
    'specific_pending_NCBI_job_verification_included': False,
    'complete_scientific_tools_claimed': status['complete_scientific_tools_claimed'],
    'closure_reset': {'original_goal': str(GOAL), 'sha256': sha(GOAL.read_bytes()),
        'objective_and_all16_read_verbatim': True,
        'exact_contracts_read': [
            evidence(BASE + 'INTERFACES_001.md'), evidence(BASE + 'RESULT_HANDOFF_005.md'),
            evidence('verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/IMPLEMENTATION_CONTRACT_PROPOSAL_001.md'),
            evidence(BASE + 'REFERENCE_VISIBILITY_HANDOFF_002.md')]}}
assert STATUS.read_bytes() == before_bytes and not UPDATE.exists()
with UPDATE.open('x') as stream:
    stream.write(json.dumps(update, indent=2) + '\n')
temporary = STATUS.with_name('WORK_STATUS.update054.tmp')
with temporary.open('xb') as stream:
    stream.write(after_bytes)
temporary.replace(STATUS)
print(json.dumps({'update': str(UPDATE.relative_to(ROOT)), 'numerical_tally': 79,
    'added_rows': len(programs), 'scope_rows': len(status['rows']), 'scope_changed': False,
    'status_sha256': sha(STATUS.read_bytes())}))
