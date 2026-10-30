"""Additive fixed-row accounting of verified components. Stdlib metadata only."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
now = datetime.now(timezone.utc).isoformat()
review_path = PACKET / 'ROOT_REVIEW_001.json'
review = json.loads(review_path.read_text())
assert review['distinct_clean_scope_cases_passed'] == 178
assert all(row['receipt']['terminal'] and row['receipt']['quiescent'] for row in review['attempts'])
evidence = [str((PACKET/name).relative_to(REPO)) for name in [
    'CONTRACT_001.md','CONTRACT_001_A.md','CONTRACT_001_B.md','SOURCE_PINS_001.json',
    'CASE_IDS_001.json','ROOT_REVIEW_001.json','HANDOFF_001.md']]
evidence += ['verification/tool_graders_ncbi_gene_native_2026-10-29_737/VERIFICATION_001.json',
             'verification/tool_graders_addgene_sequence_native_2026-10-29_738/VERIFICATION_001.json']
names = ['get_gene_coding_sequence', 'get_plasmid_sequence']
changes = []
staged_tables = []
for relative, expected, goal_table in [
    ('research/tool_grader_inventory_2026-10-24/WORK_STATUS.json', [177,178], False),
    ('research/tool_grader_goal_2026-10-24/WORK_STATUS.json', [124,125], True),
]:
    path = REPO/relative
    before_bytes = path.read_bytes()
    before = json.loads(before_bytes)
    # The first recording attempt stopped after table writes because historical
    # evidence mixes pins and paths. Recover the exact original semantic rows
    # from their preserved history, then verify the original067 byte hash.
    recovered = False
    for index in expected:
        current = before['rows'][index]
        if current.get('sequence_support_current_boundary',{}).get('evidence') == evidence:
            history = current['history']
            previous = history[-1]['previous']
            restored = {}
            for key in current:
                if key == 'history': restored[key] = deepcopy(history[:-1])
                elif key in previous: restored[key] = deepcopy(previous[key])
            before['rows'][index] = restored
            recovered = True
    if recovered:
        before_bytes = (json.dumps(before,indent=2,allow_nan=False)+'\n').encode()
        expected_hash = ('be51210012960146e97da610499b4403c3b17b660b81e5f96762ccf55f941dbe' if goal_table
            else '1f72d8f5d62fb1426882701b712c990834e0262f1d44048827693b1aa3b8f169')
        assert hashlib.sha256(before_bytes).hexdigest() == expected_hash, 'historical_row_reconstruction_conflict'
    after = deepcopy(before)
    for index, name in zip(expected, names):
        row = after['rows'][index]
        assert row.get('name') == name if not goal_table else row['id'].endswith('-'+name)
        history = row.setdefault('history', [])
        history.append({'recorded_at': now, 'previous': {key:deepcopy(value) for key,value in row.items() if key!='history'},
            'reason': '737/738/739 components verified against saved native responses and engineered extraction/transport; actual host/resource/episode paths remain open.'})
        gene = name == names[0]
        boundary = {
            'status': 'verified_components_not_whole_supporting_operation',
            'common_authority': 'sequence_extraction_sheet_v1 / calculate_extraction_scores reused unchanged' if gene else 'addgene_sequence_page_v1 typed supporting data; no scientific confidence score',
            'new_independent_numerical_grader': False,
            'public_resource_child_binding_verified': False,
            'requested_episode_return_verified': False,
            'native_response': review['native_cases']['Gene' if gene else 'Addgene'],
            'remaining': review['remaining'], 'evidence': evidence,
        }
        row['sequence_support_current_boundary'] = boundary
        if goal_table:
            row.update(overall='in_progress', source_presence='implemented_bounded_verified_components',
                invocation_contract='component_APIs_defined_public_child_contract_pending',
                numerical_sheet='existing_shared_extraction_sheet_for_selected_CDS_only' if gene else 'typed_supporting_data_no_independent_scientific_sheet',
                native_parser='saved_native_Gene_XML_and_engineered_GenBank_geometry_verified' if gene else 'saved_current_HTML_metadata_and_engineered_legacy_literals_verified',
                metadata_extractor='native_paths_and_selected_source_ordinals_preserved_component_only',
                deterministic_calculator='existing_calculate_extraction_scores_reused' if gene else 'typed_validator_only_no_scientific_confidence',
                numerical_verification='engineered_shared_sheet_checks_pass_authentic_CDS_input_still_unavailable' if gene else 'typed_relationship_checks_pass_no_authenticated_sequence_bases',
                production_result_binding='pending_actual_selected_host_publication',
                integration_verification='component_only_no_episode_delivery',
                live_resource_verification='original201_capture_audit_failure_saved_parser_replay_verified_no_complete_resource_binding')
            row['evidence_ids'] = list(dict.fromkeys(row.get('evidence_ids',[])+evidence))
            row['note'] = '173 new component checks +5 shared regressions across declared scopes; no whole-tool/name/group completion. '+('Authentic nucleotide capture failed; Gene/locus/nucleotide/CDS host join and episode return remain open.' if gene else 'Actual public page has3 metadata entries and requires authentication; no sequence bases obtained, no fallback.')
        else:
            row['completion'].update(sheet_contract='shared_sequence_extraction_sheet_v1_reused_for_selected_CDS_only' if gene else 'typed_supporting_schema_no_independent_scientific_sheet',
                readers='verified_native_Gene_XML_and_selected_CDS_components' if gene else 'verified_current_Addgene_metadata_and_engineered_literals',
                calculators='unchanged_calculate_extraction_scores_reused' if gene else 'typed_validator_no_function_confidence',
                verification='components_verified_actual_host_resource_episode_paths_pending')
            row['resource_tests'] = 'Original201 has a retained unbound-NSS audit failure; saved native parser verification clean. One Nucleotide request failed network is unreachable. No full resource-child verification.'
            row['evidence'] = list(dict.fromkeys(row.get('evidence',[])+evidence))
            row['remaining'] = deepcopy(review['remaining'])
    assert {key:value for key,value in before.items() if key!='rows'} == {key:value for key,value in after.items() if key!='rows'}
    changed = [i for i,(old,new) in enumerate(zip(before['rows'],after['rows'])) if old!=new]
    assert changed == expected and len(before['rows']) == len(after['rows'])
    after_bytes = (json.dumps(after,indent=2,allow_nan=False)+'\n').encode()
    staged_tables.append((path,after_bytes))
    changes.append({'path':relative,'rows':len(after['rows']),'changed_row_indices':changed,
        'all_other_rows_and_top_fields_unchanged':True,'before_sha256':hashlib.sha256(before_bytes).hexdigest(),
        'after_sha256':hashlib.sha256(after_bytes).hexdigest()})

previous_path = REPO/'research/tool_grader_progress_2026-10-27/PROGRESS_067.json'
new_path = REPO/'research/tool_grader_progress_2026-10-27/PROGRESS_068.json'
assert not new_path.exists()
previous_bytes = previous_path.read_bytes()
progress = json.loads(previous_bytes)
assert all(row['status']=='open' for row in progress['deliverables'])
for field in ['current_turn_accounting','current_turn_native_work','current_turn_classification','current_workloads','accounting_review','next_continuation','current_native_verification','shared_regression_evidence']:
    progress['previous_'+field] = deepcopy(progress.get(field))
progress.update(recorded_at=now, previous_progress_record=str(previous_path.relative_to(REPO)),
    previous_progress_sha256=hashlib.sha256(previous_bytes).hexdigest(),
    previous_turn_classification={'classification':'progress','basis':'Previous continuation retained actual native responses and wrote bounded supporting adapters; those inputs exposed identity, authentication and transport verification needs. No whole-tool completion.'},
    current_turn_classification={'classification':'progress','basis':'173 new component checks+5 regressions pass across737/738/739; concrete raw-textarea/body-truncation and source-binding behaviors verified. Original native acquisition/audit failures retained; allRopen.'},
    current_turn_native_work={'selected_public_acquisition_attempts':3,'successful_public_responses':2,
        'successful_authentic_source_CDS_extractions':0,'engineered_native_extraction_executed':True,
        'new_installations':0,'external_model_calls':0,'bounded_verification_jobs':7},
    current_turn_accounting={'inventory_changes':changes,'new_complete_inventory_rows':0,
        'new_connected_operation_names':0,'shared_group_census_changed':False,'all_R1_to_R7_open':True,
        'sequence_support737738739':{'new_component_passed':173,'regressions_passed':5,'distinct_passed':178,
            'single_fresh178_case_run':False,'original201_custody_cases_excluded_from_clean_union':2,
            'remaining_failed_acquisition_cases':1,'all_original_handles_collected':True,'evidence':evidence}},
    accounting_review='Only the same2 Gene/plasmid rows per fixed table changed additively. All other rows/top fields, earlier FBA/restriction work, pending feedback and census preserved. No complete tool/name/group increment.',
    current_next_action='Trace and bind the delivered Gene/Addgene readers and explicit CDS selection to actual host-owned acquisition/publication, typed requested returns and saved replay through the existing resource-child machinery. Preserve parent-selected provider/locus/record choices. Resolve authentic nucleotide input/actual network route, authorized Addgene access and common mixed/remote/zero-length extraction modes explicitly; do not claim full wrappers from178 component checks. Required concrete TASK/STEERING trace/feedback remains separate. Do not rerun completed parser components without a defect.',
    next_continuation={'action':'actual_selected_supporting_resource_operation_and_typed_return_binding',
        'reuse':evidence,'remaining':review['remaining']})
progress['sequence_support_current_boundary'] = {key:deepcopy(value) for key,value in review.items() if key!='attempts'}
progress['current_turn_verification']['sequence_support737738739'] = {'root_review':str(review_path.relative_to(REPO)),
    'distinct_passed':178,'new_component_passed':173,'regressions':5,'authentic_source_CDS_verified':False}
for entry in evidence:
    if entry not in progress['current_update_evidence']: progress['current_update_evidence'].append(entry)
progress['current_workloads'] = [
    {'work':'737/738 pure native readers','state':'verified_components_all_original_handles_collected','live_jobs':0},
    {'work':'739 shared CDS adapter and bounded acquisition','state':'component_checks_pass_authentic_nucleotide_capture_failed_host_binding_unfinished','live_jobs':0},
]
progress['current_native_verification'] = {'original_attempts':[row['attempt'] for row in review['attempts']],
    'state':'all_collected_component_evidence_only_original_failures_preserved',
    'root_review':str(review_path.relative_to(REPO)), 'authentic_source_CDS_verified':False}
progress['shared_regression_evidence'] = {'purpose':'shared extraction authority and unchanged unbounded HTTP caller',
    'tests':5,'status':'passed','case_ids':str((PACKET/'CASE_IDS_001.json').relative_to(REPO)),
    'qualification':'Existing selected cases, not a broad family retest; original missing Rfam fixture collection failure retained.'}
progress_bytes=(json.dumps(progress,indent=2,allow_nan=False)+'\n').encode()
for path,after_bytes in staged_tables: path.write_bytes(after_bytes)
new_path.write_bytes(progress_bytes)
accounting={'inventory_changes':changes,'progress_record':str(new_path.relative_to(REPO)),
    'previous_progress_unchanged':previous_path.read_bytes()==previous_bytes,
    'progress_sha256':hashlib.sha256(new_path.read_bytes()).hexdigest(),
    'all_R1_to_R7_open':True,'new_whole_tool_or_name_or_group_increment':0}
accounting['original_recording_failure']='Mixed pin/path evidence list caused TypeError after two intended table writes; original rows recovered from preserved history and exact067 hashes verified before repaired publication. No app/test rerun.'
(PACKET/'ACCOUNTING_001.json').write_text(json.dumps(accounting,indent=2)+'\n')
print(json.dumps(accounting,indent=2))
