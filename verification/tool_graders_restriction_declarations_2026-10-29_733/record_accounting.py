"""Add verified733/734 facts to the two existing fixed restriction rows only."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
PACKET=Path(__file__).resolve().parent
PROGRESS=ROOT/'research/tool_grader_progress_2026-10-27'


def pin(path):
    data=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}


def write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def record():
    target=PROGRESS/'PROGRESS_066.json'
    assert not target.exists(),'Do not replace a recorded progress update'
    previous=PROGRESS/'PROGRESS_065.json'
    old=json.loads(previous.read_text())
    current=deepcopy(old)
    verification=json.loads((PACKET/'VERIFICATION_001.json').read_text())
    assert verification['all_distinct_passing_checks']==127
    assert verification['remaining_unrepaired_test_failures']==0
    timestamp=datetime.now(timezone.utc).isoformat()
    evidence=[str((PACKET/name).relative_to(ROOT)) for name in
        ('CONTRACT_001.md','CONTRACT_001_A.md','HANDOFF_001.md','CASE_IDS_001.json',
         'VERIFICATION_001.json','ROOT_REVIEW_001.json','SOURCE_PINS_001.json','NEXT_BOUNDARY_TRACE_001.md')]
    remaining=[
        'Parent own-catalog names explicitly supplied in initial interpretations require source receipt-cutoff proof; ordinary received-name construction is repaired',
        'Compact selector/compiler/original declaration proof is verified in the existing generic configured path; production scientific presentation profile/TASK/STEERING remains unimplemented and needs its concrete trace and running feedback',
        'Actual public alias ToolInfo/catalog pending draft002 feedback and nonempty selected scientific/credit/controller/resource verification remain open',
        'All earlier FBA/tool/template and R1-R7 requirements remain open']
    boundary={'state':'explicit_selection_compiler_original_commission_and_redelivery_proof_verified_production_presentation_pending',
        'selector734_component_checks':78,'root733_component_checks':28,'new_component_checks':106,
        'existing_regression_checks':21,'total_distinct_current_checks':127,
        'previous_restriction_component_union':386,'cumulative_restriction_component_union':492,
        'single_fresh492_case_suite':False,'all_original_handles_collected':True,
        'new_scientific_native_searches_or_calculations':0,'new_whole_tools_or_links_or_groups':0,
        'actual_saved_numerical_example':{'EcoRI_recognition_match_count':1,'native_position_1based':6,
            'Watson_boundary_0based':5,'Crick_boundary_0based':9,'complete_empty_enzyme_count':0,
            'new_scientific_operation':False},
        'actual_shared_loop_engineering_example':{'completed_own_actions':6,'observations':6,
            'restriction_result_rows':0,'opt_in_configuration':'engineering callback only',
            'configured_model_verification':False},
        'remaining':remaining,'evidence':evidence}
    updates=[]
    for relative,indices,identities in [
        ('research/tool_grader_inventory_2026-10-24/WORK_STATUS.json',[182,183],['find_restriction_sites','find_restriction_enzymes']),
        ('research/tool_grader_goal_2026-10-24/WORK_STATUS.json',[126,127],['B-L171-find_restriction_sites','B-L172-find_restriction_enzymes'])]:
        path=ROOT/relative
        before=json.loads(path.read_text())
        after=deepcopy(before)
        before_pin=pin(path)
        inventory='inventory_' in relative
        keys=('completion','resource_tests','remaining','note') if inventory else (
            'production_result_binding','integration_verification','remaining','note')
        for index,identity in zip(indices,identities):
            row=after['rows'][index]
            assert row['name' if inventory else 'id']==identity
            row.setdefault('history',[]).append({'recorded_at':timestamp,
                'record':str(target.relative_to(ROOT)),
                'scope':'explicit restriction subset and original compact form/declaration proof; production presentation remains open',
                'previous_current_fields':{key:deepcopy(row.get(key)) for key in keys}})
            row['compact_declaration_verification']=deepcopy(boundary)
            row['remaining']=deepcopy(remaining)
            row['note']='733/734 add106 component checks +21 regressions,127 distinct passing cases;492 cumulative component union across retained scopes. Same719 scientific numerical authority and723 projection. Generic configured Workflow compact admission/redelivery and empty-source shared loop are verified with engineering fixtures; production presentation/public native scientific paths remain open. Earlier facts remain in history.'
            if inventory:
                row['completion']['result_path_binding']='literal_and_compact_requested_forms_original_commission_redelivery_initial_received_name_proof_verified_production_scientific_path_pending'
                row['completion']['verification']='492_cumulative_component_union_106_new_selector_declaration_plus21_current_regressions_not_whole_tool'
                row['resource_tests']='Five original733/734 bounded verification handles collected, terminal/quiescent; all five pin classes unchanged and audits clean.20GiB memory/4GiB monitored scratch/per-file bound,swap0,no wall cap. No new native scientific search/calculation/model/network/installation or original scientific Store access. Earlier actual resource facts retained in history; configured public resource paths remain unfinished.'
            else:
                assert row['overall']=='in_progress'
                row['production_result_binding']='compact_and_literal_original_selected_form_proof_saved_redelivery_and_frozen_receivers_verified_public_scientific_path_pending'
                row['integration_verification']='106_new_selector_declaration_cases21_current_regressions_generic_configured_compact_empty_mother_and_engineering_nonempty_receiver_verified_production_presentation_pending'
        changed=[i for i,(a,b) in enumerate(zip(before['rows'],after['rows'])) if a!=b]
        assert changed==indices
        assert {k:v for k,v in before.items() if k!='rows'}=={k:v for k,v in after.items() if k!='rows'}
        write(path,after)
        updates.append({'path':relative,'rows':len(after['rows']),'changed_rows':len(changed),
            'changed_row_indices':changed,'all_other_rows_and_top_fields_unchanged':True,
            'before_sha256':before_pin['sha256'],'after_sha256':pin(path)['sha256']})
    current['recorded_at']=timestamp
    current['previous_progress_record']=str(previous.relative_to(ROOT))
    current['previous_progress_sha256']=pin(previous)['sha256']
    current['previous_turn_classification']=deepcopy(old['current_turn_classification'])
    current['previous_record_classification']=deepcopy(old['current_turn_classification'])
    current['previous_record_verification']=deepcopy(old['current_turn_verification'])
    current['previous_record_next_continuation']=deepcopy(old['next_continuation'])
    current['previous_turn_accounting']=deepcopy(old['current_turn_accounting'])
    current['current_turn_classification']={'classification':'progress',
        'basis':'Verified explicit restriction selector and original compact commission/redelivery proof with106 new component cases +21 regressions. All failed cases later pass; original failures retained. No whole-tool/name/group increment; production presentation and full scientific execution remain open.'}
    current['restriction_compact_declaration_current_boundary']=deepcopy(boundary)
    current['current_turn_verification']['restriction_compact_declarations_733_734']=deepcopy(boundary)
    current['current_turn_verification']['root_reviews'].append(str((PACKET/'ROOT_REVIEW_001.json').relative_to(ROOT)))
    current['current_turn_accounting']={'inventory_changes':updates,'new_complete_inventory_rows':0,
        'new_connected_operation_names':0,'shared_group_census_changed':False,
        'all_R1_to_R7_open':True,'restriction_compact_declarations_733_734':deepcopy(boundary)}
    current['current_turn_connected_operation_names']=[]
    current['current_turn_connected_operation_name_increment']=0
    current['current_turn_native_work']={'scientific_native_searches':0,'scientific_calculations':0,
        'external_model_network_calls':0,'bounded_verification_jobs':5}
    next_work=('Trace and freeze the parent-own-catalog initial-name receipt cutoff proof independently of completed received-name construction and733/734 compact proof. Read complete native catalog/action/receipt and pending-decision paths before any edit. Keep production scientific contract-information presentation/TASK/STEERING, ToolInfo draft002/FBA028 feedback and nonempty public selected scientific/credit/controller/resource verification open. Do not install the engineering profile callback or reactivate stale owners.')
    current['current_next_action']=next_work
    current['next_continuation']['previous_required_next_work']=old['next_continuation']['required_next_work']
    current['next_continuation']['required_next_work']=next_work
    current['next_continuation']['fresh_owners']=[]
    current['next_continuation']['closed_owners_this_record']=['/root/restriction_selection_734']
    current['next_continuation']['compact_declaration_evidence']=evidence
    current['next_continuation']['current_shared_contract']=evidence[:2]
    current['previous_accounting_review']=old['accounting_review']
    current['accounting_review']='Only the same2 restriction rows in each fixed table changed, additively with prior current fields in history. Other rows/top fields, FBA, pending feedback and the complete census are unchanged.106 new component cases +21 existing regressions; no whole-tool/name/group increment. All R1-R7 remain open.'
    for key in ('pending_message_feedback','current_combined_sheet_operation_census','deliverables',
        'current_workloads','shared_scientific_grader_counts'):
        assert current[key]==old[key],key
    assert all(row['status']=='open' for row in current['deliverables'])
    if isinstance(current['current_update_evidence'],list):current['current_update_evidence'].extend(evidence)
    else:current['current_update_evidence']['restriction_compact_declarations_733_734']=evidence
    write(target,current)
    write(PACKET/'ACCOUNTING_UPDATE_001.json',{'recorded_at':timestamp,'previous':pin(previous),
        'current':pin(target),'updates':updates,'all_other_rows_and_top_fields_unchanged':True,
        'pending_feedback_and_FBA_work_preserved':True,'all_R1_R7_open':True,
        'whole_tool_link_group_increment':0})
    print(json.dumps({'progress':pin(target),'changed_rows':[x['changed_row_indices'] for x in updates],
        'all_R1_R7_open':True,'new_component_cases':106,'current_regressions':21}))


if __name__=='__main__':record()
