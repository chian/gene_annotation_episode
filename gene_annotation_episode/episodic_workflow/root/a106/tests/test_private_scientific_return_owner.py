"""Original head return functions through their actual private caller namespace.

Controlled closed-context records only: no provider, native job or historical Store.
These exercise real validators and copied closure values, not a scientific grade.
"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from ..scientific_process import to_parent as owner
from ..scientific_process_records import (OPTION_REF_VERSION, LEGACY_SELECTION_VERSION,
    scientific_invocation_ref)


def original_closed_context(ended_by='exhausted'):
    def option(slot,identifier):
        return {'version':OPTION_REF_VERSION,'library_id':'1'*64,'slot':slot,
            'option_id':identifier,'entry_sha256':'2'*64}
    selection={'version':LEGACY_SELECTION_VERSION,'annotation_ref':option('annotation_distinction','A106'),
        'thought_ref':option('thought_pattern','P01'),'tools':[]}
    assignment={'selection':selection,'proposed_annotation_ref':'hypothesis_'+'a'*24}
    path=(('scientific_process','0'),);run='actual-head-return-control'
    context=SimpleNamespace(run_id=run,path=path,assignment=assignment,
        request={'message':{'episode_assignment':deepcopy(assignment),
            'scientific_invocation_ref':scientific_invocation_ref(run,path)}})
    snapshot={'completion':{'ended_by':ended_by,'end_reason':'source_failed' if ended_by=='source_failed' else '',
        'units_consumed':2},'own_action_count':2,'parent_invocation_ref':None,
        'controller_credit':{'credit_kind':'scientific','credit_binding':{'version':'controlled_original_binding_v1'}},
        'initial_credit':-0.5,'credit':-0.125,'episode_yield':None}
    return context,snapshot


@pytest.mark.parametrize('ended_by',['exhausted','incomplete','source_failed','yield_stop'])
def test_original_closure_values_and_identity_are_copied(ended_by):
    context,snapshot=original_closed_context(ended_by);before=(deepcopy(context.assignment),deepcopy(snapshot))
    row=owner.build_process_result(context,snapshot)
    assert row['initial_credit']==-0.5 and row['credit']==-0.125 and row['completed_actions']==2
    assert row['invocation_ref']==context.request['message']['scientific_invocation_ref']
    assert row['parent_invocation_ref'] is None and row['origin_kind']=='ordinary_child'
    assert row['credit_kind']=='scientific' and row['credit_binding_ref'].startswith('scientific_credit_binding_')
    assert row['selection']==context.assignment['selection'] and row['episode_yield'] is None
    assert row['proposed_annotation_ref']==context.assignment['proposed_annotation_ref']
    assert before==(context.assignment,snapshot)


def test_no_closure_still_has_no_process_result():
    context,snapshot=original_closed_context();snapshot['completion']=None
    assert owner.build_process_result(context,snapshot) is None


@pytest.mark.parametrize('mutation,code',[
    ('count','scientific_process_completion_count_mismatch'),
    ('assignment','scientific_process_result_assignment_mismatch'),
    ('invocation','scientific_process_result_invocation_mismatch'),
    ('parent','scientific_process_result_parent_mismatch'),
    ('metadata','scientific_process_credit_metadata_invalid'),
    ('binding','scientific_process_credit_metadata_invalid'),
])
def test_actual_original_identity_validation_rejects_changed_operand(mutation,code):
    context,snapshot=original_closed_context()
    if mutation=='count':snapshot['own_action_count']=1
    elif mutation=='assignment':context.request['message']['episode_assignment']['proposed_annotation_ref']='hypothesis_'+'b'*24
    elif mutation=='invocation':context.request['message']['scientific_invocation_ref']=scientific_invocation_ref('another-run',context.path)
    elif mutation=='parent':snapshot['parent_invocation_ref']=scientific_invocation_ref(context.run_id,(('scientific_process','1'),))
    elif mutation=='metadata':snapshot['controller_credit']['credit_kind']='invented_kind'
    elif mutation=='binding':snapshot['controller_credit']['credit_binding']={}
    with pytest.raises(ValueError,match=code):owner.build_process_result(context,snapshot)


def test_exact_duplicate_forwarding_is_stable_and_detached():
    context,snapshot=original_closed_context();row=owner.build_process_result(context,snapshot)
    result=owner.merge_process_results(row,[deepcopy(row),deepcopy(row)])
    assert result==[row] and result[0] is not row
    result[0]['selection']['annotation_ref']['option_id']='A999'
    assert row['selection']['annotation_ref']['option_id']=='A106'


def test_conflicting_same_invocation_is_not_silently_deduplicated():
    context,snapshot=original_closed_context();row=owner.build_process_result(context,snapshot)
    changed=deepcopy(row);changed['credit']=0.75
    with pytest.raises(ValueError,match='scientific_process_result_conflict'):
        owner.merge_process_results(row,[changed])


def test_received_order_and_own_first_are_preserved():
    context,snapshot=original_closed_context();own=owner.build_process_result(context,snapshot)
    changed=deepcopy(own);changed['invocation_ref']=scientific_invocation_ref('different-run',context.path)
    assert owner.merge_process_results(own,[changed,deepcopy(own)])==[own,changed]
    assert owner.merge_process_results(None,[changed,own])==[changed,own]
