"""Record tested barcode parts without counting an unfinished complete result path."""

raise SystemExit('Historical progress replay is retired; this script does not update current accounting.')
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
BASE = ROOT / 'research/tool_grader_goal_2026-10-24'
STATUS = BASE / 'WORK_STATUS.json'
UPDATE = BASE / 'PROGRESS_UPDATE_115.json'
EXPECTED = '878bbc9df3d4ded7c320d2e73ca35ad4ef3769797117d7efc79dc8247abb88f7'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()

def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(raw), 'size_bytes': len(raw)}

def checked(path, count):
    receipt = json.loads((path / 'receipt.json').read_text())
    audit = json.loads((path / 'execution_audit.json').read_text())
    assert receipt['returncode'] == 0 and receipt['terminal'] and receipt['quiescent']
    assert all(receipt[k] is True for k in ('source_unchanged', 'dependency_unchanged', 'stdlib_unchanged', 'binary_unchanged'))
    assert audit['pytest_returncode'] == 0 and audit['native_unchanged'] and not audit['outside_modules'] and not audit['unbound_mappings']
    cases = ET.parse(path / 'junit.xml').findall('.//testcase')
    assert len(cases) == count and not any(c.find(k) is not None for c in cases for k in ('failure','error','skipped'))
    return {'directory': str(path.relative_to(ROOT)), 'passed': count, 'unit': receipt['unit'],
        'terminal': True, 'quiescent': True, 'returncode': 0,
        'evidence': [pin(path / name) for name in ('receipt.json','execution_audit.json','junit.xml')]}

raw = STATUS.read_bytes()
assert sha(raw) == EXPECTED and not UPDATE.exists()
previous = json.loads((BASE / 'PROGRESS_UPDATE_114.json').read_text())
old = json.loads(raw)
new = deepcopy(old)
scope_sha = sha((BASE / 'SCOPE.json').read_bytes())
assert scope_sha == previous['scope_sha256_unchanged']
assert len(new['rows']) == 308 and len(new['resource_bindings']) == 288
assert previous['numerical_grader_progress_tally']['after'] == 114
assert new['verified_bound_local_tool_mode_rows'] == 44
checks = [checked(PACKET / 'check001',13), checked(PACKET / 'math001',61),
    checked(ROOT / 'verification/tool_graders_barcode_native_2026-10-27_492/check004',38)]
summary = ('Barcode native492/check004 passed38 tests at its unchanged frozen software. '
    'Root494/check001 passed13 actual local-resource/input-authority cases, including one selected '
    'start/observation, exact terminal-zero expectation, original-handle monitoring and closed resource '
    'replay after all three input files were removed. Root reviewed the numerical implementation and '
    'corrected unavailable measurement units/source categories;494/math001 passed61 cases at that '
    'corrected snapshot. These61 include the earlier491 cases and are not additional to60. Actual '
    '12-read data yield10 extracted, counts4/3/2/1, distances1/4/3, merge heights1/3.5 and clusters7/2. '
    'Every collected handle is terminal/quiescent0 with unchanged recorded source/runtime pins. '
    '493 result custody and495 shared registration are written and under verification; the complete '
    'scientific-parent typed-result Workflow remains unfinished. No barcode grader/local row is added '
    'to the tally. NMF490 remains on its original full-Workflow handle. Count114/308,44 verified local '
    'rows and194 outside tally remain unchanged. W05/literature stay separate.')
evidence = {'id':'BARCODE-RESOURCE-AND-NUMERICAL-115','kind':'partial_implementation_verification',
    'summary':summary,'checks':checks,'reports':[pin(PACKET / name) for name in
        ('VERIFICATION.md','VERIFICATION.json','NUMERICAL_REVIEW_CORRECTION_001.md')]}
row = next(r for r in new['rows'] if r['id']=='B-L130-analyze_barcode_sequencing_data')
before = deepcopy(row)
row.update(overall='native_resource_and_numerical_components_verified_full_result_path_pending',
    tool_information='real_local_information_and_native_contract_verified_shared_registration_pending',
    invocation_contract='actual_shared_local_resource_episode_original_handle_and_replay_verified',
    numerical_sheet='implemented_root_reviewed_final61_component_checks_pass',
    native_parser='implemented_root_reviewed_final61_component_checks_pass',
    metadata_extractor='implemented_root_reviewed_final61_component_checks_pass',
    deterministic_calculator='implemented_root_reviewed_missing_units_corrected_final61_checks_pass',
    production_result_binding='result_host_and_shared_registration_written_final_verification_in_progress',
    numerical_verification='61_corrected_numerical_tests_and_separate38_native_tests_pass',
    integration_verification='13_local_resource_and_input_cases_pass_complete_scientific_Workflow_pending',
    live_resource_verification='actual_tiny_local_barcode_resource_episode_and_four_native_file_variants_tested')
row['evidence_ids'].append(evidence['id'])
row['note'] += ' Update115: ' + summary
binding = next(r for r in new['resource_bindings'] if r['id']=='B-L130-analyze_barcode_sequencing_data::local')
binding_before = deepcopy(binding)
binding.update(invocation_contract='actual_shared_local_resource_episode_verified',
    production_result_binding='493_host_and495_shared_registration_under_verification',
    integration_verification='local_resource_scope_and_closed_replay_verified_full_scientific_path_pending',
    live_resource_verification='native492_final38_and_root494_resource_input13_pass',
    prerequisites_present='frozen_actual_Bio1.85_NumPy2.2.6_SciPy1.15.3_jsonschema4.25.1',
    native_format_observed='actual_FASTA_FASTQ_gzip_retained_barcode_bundle_and_numerical_outputs')
binding['evidence_ids'].append(evidence['id'])
new['verification_evidence'].append(evidence)
new_raw = encode(new)
update = {'schema':'tool_grader_progress_update_v1','date':'2026-10-27','author':'root',
    'recorded_at':datetime.now(timezone.utc).isoformat(), 'previous_status_sha256':EXPECTED,
    'new_status_sha256':sha(new_raw),'scope_sha256_unchanged':scope_sha,'scope_changes':[],
    'changes':[{'id':row['id'],'before':before,'after':row}],
    'resource_binding_changes':[{'id':binding['id'],'before':binding_before,'after':binding}],
    'added_evidence':[evidence],
    'numerical_grader_progress_tally':{'before':114,'after':114,'added_row_ids':[],
        'meaning':previous['numerical_grader_progress_tally']['meaning']},
    'verified_bound_local_tool_mode_rows':{'before':44,'after':44},
    'remaining_fixed_rows_outside_tally':194,
    'completed_work':[summary],
    'findings_requiring_repair':['Barcode complete scientific-parent result Workflow and final493/495 checks remain.',
        'NMF original full Workflow remains unfinished; saved calculation has completed but final root return is pending.',
        *previous['findings_requiring_repair'][2:]],
    'work_item_states':deepcopy(previous['work_item_states']),
    'unfinished_work':[*previous['unfinished_work'],
        'Update115 supersedes only barcode current-status wording: native/numerical and local resource/input checks '
        'now verified; complete typed scientific-parent path still pending. No count increment. Earlier fixed scope '
        'and all unfinished items remain.'],
    'inventory_maintenance_counted_as_implementation_progress':False,
    'specific_pending_NCBI_job_verification_included':False,'complete_scientific_tools_claimed':0,
    'previous_goal_turn_classification':previous['this_goal_turn_progress'],
    'this_goal_turn_progress':'implemented_and_verified_barcode_local_resource_and_input_authority_corrected_missing_measurement_units_and_verified61_numerical_cases',
    'partial_work':['493 result host/custody and495 shared registration final checks remain; complete Workflow next.']}
assert [r['id'] for r in new['rows']] == [r['id'] for r in old['rows']]
assert [r['id'] for r in new['resource_bindings']] == [r['id'] for r in old['resource_bindings']]
with UPDATE.open('xb') as out:
    out.write(encode(update))
STATUS.write_bytes(new_raw)
print(json.dumps({'update':115,'numerical_graders':114,'fixed_rows':308,'local_rows':44,
    'outside_tally':194,'status_sha256':sha(new_raw)}))
