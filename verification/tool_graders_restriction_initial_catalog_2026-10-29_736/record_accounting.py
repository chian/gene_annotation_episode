"""Add verified735/736 facts; preserve every fixed row and unfinished obligation."""
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
    target=PROGRESS/'PROGRESS_067.json'
    assert not target.exists(),'Never replace a recorded progress update'
    previous=PROGRESS/'PROGRESS_066.json'
    old=json.loads(previous.read_text());current=deepcopy(old)
    verified=json.loads((PACKET/'VERIFICATION_001.json').read_text())
    assert verified['total_distinct_checks']==96 and verified['remaining_unrepaired_case_failures']==0
    now=datetime.now(timezone.utc).isoformat()
    evidence=[str((PACKET/x).relative_to(ROOT)) for x in ('CONTRACT_001.md','CONTRACT_001_A.md',
        'HANDOFF_001.md','CASE_IDS_001.json','SOURCE_PINS_001.json','VERIFICATION_001.json','ROOT_REVIEW_001.json')]
    remaining=[
        'Production scientific contract-information presentation/TASK/STEERING remains unimplemented and needs its concrete decision trace and running feedback',
        'Public alias ToolInfo/catalog draft002 feedback and authentic nonempty selected native/saved scientific parent return, credit/controller and configured-resource/model verification remain open',
        'Initial parent-catalog identifier custody is verified with an explicitly labelled publication/job authority seam; it does not establish a newly selectable native scientific tool',
        'All earlier FBA/tool/template and R1-R7 requirements remain open']
    boundary={'state':'explicit_original_initial_names_original_commissions_and_frozen_parent_catalog_cutoffs_verified_engineering',
        'cutoff735_new_component_checks':56,'receiver736_new_component_checks':28,
        'new_component_checks':84,'existing_regressions':12,'total_distinct_checks':96,
        'previous_restriction_component_union':492,'cumulative_restriction_component_union':576,
        'single_fresh576_case_suite':False,'all_original_handles_collected':True,
        'new_scientific_native_searches_or_calculations':0,'new_whole_tools_or_links_or_groups':0,
        'actual_engineering_example':deepcopy(verified['actual_engineering_example']),
        'remaining':remaining,'evidence':evidence}
    updates=[]
    for relative,indices,names in [
        ('research/tool_grader_inventory_2026-10-24/WORK_STATUS.json',[182,183],['find_restriction_sites','find_restriction_enzymes']),
        ('research/tool_grader_goal_2026-10-24/WORK_STATUS.json',[126,127],['B-L171-find_restriction_sites','B-L172-find_restriction_enzymes'])]:
        path=ROOT/relative;before=json.loads(path.read_text());after=deepcopy(before);before_pin=pin(path)
        inventory='inventory_' in relative
        fields=('completion','resource_tests','remaining','note') if inventory else (
            'production_result_binding','integration_verification','remaining','note')
        for index,name in zip(indices,names):
            row=after['rows'][index]
            assert row['name' if inventory else 'id']==name
            row.setdefault('history',[]).append({'recorded_at':now,'record':str(target.relative_to(ROOT)),
                'scope':'explicit initial names from original parent catalog, original commission and frozen source receipts; engineering authority seam',
                'previous_current_fields':{k:deepcopy(row.get(k)) for k in fields}})
            row['initial_catalog_cutoff_verification']=deepcopy(boundary)
            row['remaining']=deepcopy(remaining)
            row['note']='735/736:84 new custody/receiver component cases +12 regressions,96 distinct passing cases;576 cumulative scoped component union. Explicit initial names, bounded original own-source receipts, multigeneration explicit handoff, rollback/replay and immutable manifests verified with an engineering publication/job authority seam. Public native scientific execution remains unfinished.719/723 numerical authority/projection unchanged; prior facts retained in history.'
            if inventory:
                row['completion']['result_path_binding']='literal_compact_received_and_explicit_initial_parent_catalog_identifier_proofs_verified_public_scientific_path_pending'
                row['completion']['verification']='576_cumulative_component_union_84_new_catalog_initial_plus12_current_regressions_not_whole_tool'
                row['resource_tests']='Four original735/736 bounded verification handles collected, terminal/quiescent, clean audits/all five pin classes unchanged.20GiB RAM/4GiB monitored scratch/per-file bound,swap0,no wall cap. No scientific native search/calculation/external model/network/install or original scientific Store access. Earlier real native/resource facts retained; current authority seam is engineering only.'
            else:
                assert row['overall']=='in_progress'
                row['production_result_binding']='explicit_initial_and_requested_received_forms_original_catalog_cutoff_and_commission_proofs_verified_public_native_scientific_path_pending'
                row['integration_verification']='84_new_catalog_initial_component_cases12_existing_regressions_engineering_nested_and_multigeneration_Workflow_verified_authentic_public_scientific_execution_pending'
        changed=[i for i,(a,b) in enumerate(zip(before['rows'],after['rows'])) if a!=b]
        assert changed==indices
        assert {k:v for k,v in before.items() if k!='rows'}=={k:v for k,v in after.items() if k!='rows'}
        write(path,after)
        updates.append({'path':relative,'rows':len(after['rows']),'changed_rows':2,
            'changed_row_indices':changed,'all_other_rows_and_top_fields_unchanged':True,
            'before_sha256':before_pin['sha256'],'after_sha256':pin(path)['sha256']})
    current['recorded_at']=now
    current['previous_progress_record']=str(previous.relative_to(ROOT))
    current['previous_progress_sha256']=pin(previous)['sha256']
    current['previous_turn_classification']=deepcopy(old['current_turn_classification'])
    current['previous_record_classification']=deepcopy(old['current_turn_classification'])
    current['previous_record_verification']=deepcopy(old['current_turn_verification'])
    current['previous_record_next_continuation']=deepcopy(old['next_continuation'])
    current['previous_turn_accounting']=deepcopy(old['current_turn_accounting'])
    current['current_turn_classification']={'classification':'progress','basis':
        'Demonstrated and repaired original parent-catalog initial-name construction and frozen cutoff validation.84 new component cases +12 regressions pass; original failure retained. No whole-tool/name/group completion or fabricated scientific measurements.'}
    current['restriction_initial_catalog_current_boundary']=deepcopy(boundary)
    current['current_turn_verification']['restriction_initial_catalog_735_736']=deepcopy(boundary)
    current['current_turn_verification']['root_reviews'].append(str((PACKET/'ROOT_REVIEW_001.json').relative_to(ROOT)))
    current['current_turn_accounting']={'inventory_changes':updates,'new_complete_inventory_rows':0,
        'new_connected_operation_names':0,'shared_group_census_changed':False,'all_R1_to_R7_open':True,
        'restriction_initial_catalog_735_736':deepcopy(boundary)}
    current['current_turn_connected_operation_names']=[]
    current['current_turn_connected_operation_name_increment']=0
    current['current_turn_native_work']={'scientific_native_searches':0,'scientific_calculations':0,
        'external_model_network_calls':0,'bounded_verification_jobs':4}
    next_work=('The initial-name catalog cutoff mechanics are now verified, alongside732 construction and733/734 compact declarations. Do not reopen them without a demonstrated defect. Inspect the remaining get_gene_coding_sequence/get_plasmid_sequence wrapper and actual extraction/acquisition handoff gaps from715 source evidence; resolve aliases to existing sequence extraction/calculation and actual NCBI/GenBank/plasmid paths before new code. Read the full affected paths and fixed rows, then freeze precise independent ownership. In parallel in scope, preserve production scientific presentation and public restriction/FBA ToolInfo feedback as explicit pending message work; do not silently install engineering callbacks. Full selected native scientific return/credit/controller/resource and all R1-R7 obligations remain open.')
    current['current_next_action']=next_work
    current['next_continuation']['previous_required_next_work']=old['next_continuation']['required_next_work']
    current['next_continuation']['required_next_work']=next_work
    current['next_continuation']['fresh_owners']=[]
    current['next_continuation']['closed_owners_this_record']=['/root/restriction_catalog_cutoff_735']
    current['next_continuation']['initial_catalog_cutoff_evidence']=evidence
    current['next_continuation']['current_shared_contract']=evidence[:2]
    current['previous_accounting_review']=old['accounting_review']
    current['accounting_review']='Exactly the same2 restriction rows per fixed table changed additively; previous current fields and all earlier work retained in history. Other rows/top fields, FBA, pending feedback and full census unchanged.84 new component cases +12 regressions; no whole-tool/name/group increment. All R1-R7 open.'
    for key in ('pending_message_feedback','current_combined_sheet_operation_census','deliverables',
        'current_workloads','shared_scientific_grader_counts'):
        assert current[key]==old[key]
    assert all(row['status']=='open' for row in current['deliverables'])
    if isinstance(current['current_update_evidence'],list):current['current_update_evidence'].extend(evidence)
    else:current['current_update_evidence']['restriction_initial_catalog_735_736']=evidence
    write(target,current)
    write(PACKET/'ACCOUNTING_UPDATE_001.json',{'recorded_at':now,'previous':pin(previous),
        'current':pin(target),'updates':updates,'all_other_rows_and_top_fields_unchanged':True,
        'pending_feedback_and_FBA_work_preserved':True,'all_R1_R7_open':True,'whole_tool_link_group_increment':0})
    print(json.dumps({'progress':pin(target),'changed_rows':[x['changed_row_indices'] for x in updates],
        'new_components':84,'regressions':12,'all_R1_R7_open':True}))


if __name__=='__main__':record()
