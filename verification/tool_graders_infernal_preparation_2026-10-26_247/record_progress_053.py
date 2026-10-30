"""Add component evidence to the existing seven inventory rows without closing them."""
raise SystemExit('Historical progress mutation retired; current progress is not reconstructed from old goal attachments or notes.')
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'research/tool_grader_goal_2026-10-24'
STATUS = DIRECTORY / 'WORK_STATUS.json'
UPDATE = DIRECTORY / 'PROGRESS_UPDATE_053.json'
GOAL = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


before_bytes = STATUS.read_bytes()
status = json.loads(before_bytes)
assert status['authority_sha256'] == sha(GOAL.read_bytes())
scope_hash = sha((DIRECTORY / status['scope_file']).read_bytes())
assert scope_hash == '2f2d6670e3f89ecb980f87857b44d129751bad26471213b8bada9115960c1719'
assert not UPDATE.exists()
programs = ('cmbuild', 'cmcalibrate', 'cmconvert', 'cmemit', 'cmfetch', 'cmpress', 'cmstat')
notes = {
    'cmbuild': 'Native build/refine fixtures and Stockholm training measurements exist. Non-Stockholm training extraction and additional expert/clustering variants are not established.',
    'cmcalibrate': 'Six explicit modes have native fixtures. Previous merge-partition producer requests and GC-input calibration provenance remain unavailable and are reported unknown; no invented provenance.',
    'cmconvert': 'Five explicit conversions have native fixtures. Opaque binary output stays retained without a fabricated decoded model population; legacy calibration/state-table equivalence is not established.',
    'cmemit': 'Three explicit modes and seven retained sequence/alignment formats have native examples. Generated sequences remain generated; full node-level trace grading and exhaustive expert variants are not established.',
    'cmfetch': 'Single-key, key-file and index modes have native fixtures. Missing key diagnostics are distinct from native exit status. Supplied old SSI provenance and binary index decoding remain unknown.',
    'cmpress': 'Four native index companions are retained with current-attempt/source bindings. Full binary index decoding is not established; failed calibration checks are diagnostic facts, not a scientific gate.',
    'cmstat': 'Seven explicit modes preserve native values and separate saved conversions. Signed residuals and native formatting uncertainty remain distinct; unavailable calibration inputs remain unknown.',
}
qualification = ('Update053 records in-progress implementation, not tool closure. Seven programs and27 explicit modes have producer/grade components. '
    'The historical direct Workflow run passed one mode per program but publication sources changed during that run. '
    'Expanded mode, nested scientific return, typed failure and final replay checks are still active. '
    'The existing numerical implementation tally remains72; these seven rows remain among236 outside that tally. '
    'No annotation-confidence score, biological observation, W05 change, literature grading, HPC deployment or configured-model science is claimed. '
    'The full308-row scope and general TASK/STEERING/resource-instruction work remain unchanged.')
groups = {
    'INFERNAL-PREPARATION-COMPONENTS-053': (
        'Actual native inputs/outputs, tool-specific populated sheets and separate deterministic calculations exist; original occurrence associations and unavailable states remain explicit.',
        ['verification/tool_graders_infernal_preparation_2026-10-26_247/worker_003/receipt.json',
         'verification/tool_graders_infernal_preparation_2026-10-26_247/NATIVE_COMPILED_INDEX_001.json',
         'verification/tool_graders_infernal_preparation_producer_2026-10-26_251/VERIFICATION_001.md',
         'verification/tool_graders_infernal_preparation_capture_2026-10-26_252/REPORT_001.md']),
    'INFERNAL-PREPARATION-RETURNS-053': (
        'Requested numerical/artifact/population projections and immediate-child return authentication are implemented. Later optional failure facts are under active verification.',
        ['verification/tool_graders_infernal_preparation_views_2026-10-26_253/HANDOFF_001.md',
         'verification/tool_graders_infernal_preparation_returns_2026-10-26_255/boundary_003/receipt.json',
         'verification/tool_graders_infernal_preparation_2026-10-26_247/FAILURE_RETURN_HANDOFF_001.md',
         'verification/tool_graders_infernal_preparation_2026-10-26_247/FAILURE_RETURN_HANDOFF_002.md']),
    'INFERNAL-PREPARATION-INTEGRATION-053': (
        'Actual local native jobs pass through launch/local/results and requested parent forms in historical scripted Workflow cases. Broader final-source verification is unfinished.',
        ['verification/tool_graders_infernal_preparation_2026-10-26_247/workflow_002/receipt.json',
         'verification/tool_graders_infernal_preparation_2026-10-26_247/workflow_002/tests.xml',
         'verification/tool_graders_infernal_preparation_2026-10-26_247/NESTED_WORKFLOW_HANDOFF_001.md']),
}
evidence = []
for identifier, (summary, paths) in groups.items():
    evidence.append({'id': identifier, 'kind': 'implemented_components_full_integration_verification_in_progress',
        'summary': summary, 'qualification': qualification,
        'reports': [{'path': p, 'sha256': sha((ROOT / p).read_bytes())} for p in paths]})
changes = []
for program in programs:
    identifier = 'A-L077-' + program
    row = next(r for r in status['rows'] if r['id'] == identifier)
    old = deepcopy(row)
    assert row['overall'] == 'not_assessed'
    row.update(overall='implemented_components_full_integration_verification_in_progress',
        source_presence='source_present',
        tool_information='configured_real_four_field_local_mode_contracts_present',
        invocation_contract='explicit_original_request_compiles_to_selected_native_mode',
        numerical_sheet='filled_native_examples_retained',
        native_parser='component_tested_supported_formats_unparsed_formats_explicit',
        metadata_extractor='original_occurrence_and_supported_metadata_joins_tested',
        deterministic_calculator='separate_saved_sheet_calculators_tested',
        production_result_binding='native_preparation_results_and_requested_parent_facts_implemented',
        numerical_verification='qualified_native_component_receipts_retained',
        integration_verification='historical_direct_native_workflow_pass_nested_and_final_mode_verification_active',
        live_resource_verification='actual_small_native_local_examples_no_hpc_binding',
        evidence_ids=list(groups), note=qualification + ' ' + notes[program])
    changes.append({'group': 'rows', 'id': identifier, 'before': old, 'after': deepcopy(row)})
    resource = next(r for r in status['resource_bindings'] if r['id'] == identifier + '::local')
    old = deepcopy(resource)
    resource.update(invocation_contract='explicit_original_local_request_bound',
        production_result_binding='retained_native_sheet_calculations_and_requested_returns_implemented',
        integration_verification='direct_workflow_historical_pass_full_verification_active',
        live_resource_verification='actual_small_native_examples',
        prerequisites_present='explicit_native_executable_and_example_input_identities_verified',
        native_format_observed='retained_original_mode_specific_native_artifacts', evidence_ids=list(groups))
    changes.append({'group': 'resource_bindings', 'id': resource['id'], 'before': old, 'after': deepcopy(resource)})
status['verification_evidence'].extend(evidence)
after_bytes = (json.dumps(status, indent=2) + '\n').encode()
update = {'schema': 'tool_grader_progress_update_v1', 'date': '2026-10-26',
    'recorded_at': datetime.now(timezone.utc).isoformat(), 'author': 'root',
    'previous_status_sha256': sha(before_bytes), 'new_status_sha256': sha(after_bytes),
    'scope_sha256_unchanged': scope_hash, 'scope_changes': False,
    'changes': changes, 'added_evidence': evidence,
    'numerical_grader_progress_tally': {'before': 72, 'after': 72, 'added_row_ids': [],
        'meaning': 'Existing tally unchanged; seven preparation rows now record actual component progress and unfinished integration.'}}
assert len(status['rows']) == 308 and len(status['resource_bindings']) == 288
assert STATUS.read_bytes() == before_bytes
with UPDATE.open('x') as stream:
    stream.write(json.dumps(update, indent=2) + '\n')
temporary = STATUS.with_name('WORK_STATUS.update053.tmp')
with temporary.open('xb') as stream:
    stream.write(after_bytes)
temporary.replace(STATUS)
print(json.dumps({'update': str(UPDATE.relative_to(ROOT)), 'rows_updated': len(programs),
    'resource_bindings_updated': len(programs), 'numerical_tally': 72, 'scope_rows': len(status['rows']),
    'scope_changed': False, 'status_sha256': sha(STATUS.read_bytes())}))
