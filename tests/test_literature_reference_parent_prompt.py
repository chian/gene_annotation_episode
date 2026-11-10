"""Synthetic states only: parent source-integration TASK and factual STEERING."""
from copy import deepcopy
from types import MappingProxyType

import pytest

from gene_annotation_episode.decision_context import INSTRUCTIONS
from gene_annotation_episode.literature_assay_prompt import ASSAY_TASK
from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK
from gene_annotation_episode.literature_reference_parent_prompt import (
    REFERENCE_PARENT_TASK, VERSION, render_reference_evidence_parent_prompt,
)


def state():
    return {
        'literature_experimental_work': {'version':'literature_experimental_task_v1',
                                         'aspect':'reference_evidence_parent'},
        'reference_evidence_parent': {'version':VERSION,'source_refs':['source_assigned'],
            'source_custody':[
                {'source_ref':'source_assigned','artifact_ref':'artifact_original','text_ref':'artifact_text',
                 'version':'publisher-original','implementation_sha256':'PRIVATE_PIN'},
                {'source_ref':'source_unassigned','artifact_ref':'PRIVATE_UNASSIGNED_ARTIFACT'}],
            'private_history':'PRIVATE_PARENT_PROFILE_HISTORY'},
        'goal': {'goal_id':'PRIVATE_GOAL','objective':'Evaluate the reference preparation and its observed signal.',
                 'task_context': {'reference_molecule':'Protein P','constraint':'Assigned source experiment only'},
                 'result_contract': {'scope':'source evidence only'}},
        'scope': {'subject_refs':['input_material']},
        'constraints': {'experimental_boundary':'Keep growth and catalytic measurements separate'},
        'working_state': {
            'subjects':[{'id':'input_material','name':'supplied protein snippet','sequence_ref':'artifact_sequence',
                         'record_type':'input'}],
            'materials':[{'name':'input.faa','source_ref':'source_material'}],
            'references':[{'id':'reference_requested','label':'Source construct P','source_ref':'source_assigned'},
                          {'id':'reference_unrelated','label':'PRIVATE_UNRELATED_REFERENCE'}],
            'sources':[{'id':'source_unrelated','label':'PRIVATE_SOURCE_INVENTORY'}]},
        'tools':[{'name':'source.read','description':'Read an exact source window.',
                  'input_schema': {'type':'object','properties':{
                      'source_ref':{'type':'string','format':'reference'},
                      'offset':{'type':'integer','minimum':0}},
                      'required':['source_ref','offset'],'additionalProperties':False}}],
        'child_options':'A literature child can investigate a narrower source question; no fixed order.',
        'available_report_facts':{
            'literature_assay_cells':{'meaning':'Source endpoint components with conditional assumptions.',
                'report_schema':{'type':'array','items':{'type':'number'},'x-source':'literature_assay_cells'}},
            'unrelated_fact':{'meaning':'PRIVATE_UNREQUESTED_FACT'}},
        'requested_report_purpose':'Return the source measurements needed for the next comparison.',
        'requested_form': {'type':'object','properties':{
            'measurements':{'type':'array','items':{'type':'number'},'x-source':'literature_assay_cells'}},
            'required':['measurements'],'additionalProperties':False},
        'report_lifecycle':'Later facts do not silently rewrite a prior interpretation.',
        'action_yields': {'rows':[{'category':'tool/source.read','completed_actions':2,'total_yield':-.25,
            'attempted_uncompleted':1,'expected_yield':{'status':'unavailable','unavailable_reason':'parameters_unbound','band':None}}]},
        'controller': {'scores':[998],'estimate':{'turns':2,'expected_next_gain':{
            'value':.1,'lower':-.2,'upper':.4,'status_code':0,'uncertainty_code':2,'alpha':.05}},
            'decision':{'continuation_cost':.001},'diagnostics':'PRIVATE_FIT'},
        'last_local_outcome':None,'feedback':None,'child_reports':[],
        'current_report_update':{},'current_report_basis_refs':[], 'pending_work':{'items':[]},
        'literature_assignment':{'source_refs':['PRIVATE_CHILD_SOURCE'],'instructions':'PRIVATE_CHILD_TASK'},
        'parent_history':'PRIVATE_PARENT_HISTORY',
        'restored_episode_history':{'entries':['PRIVATE_RESTORED_HISTORY']},
    }


def render(value=None, *, instructions=None, lookup_results=()):
    return render_reference_evidence_parent_prompt(state() if value is None else value,
        'Choose useful evidence integration work iteratively.\n'+INSTRUCTIONS if instructions is None else instructions,
        lookup_results=lookup_results)


def split(text):
    assert text.count('\n\nSTEERING\n')==1
    return text.split('\n\nSTEERING\n')


def test_parent_own_task_and_actual_assignment_repeat_after_outcomes_repair_and_lookup():
    initial=state()
    later=deepcopy(initial)
    later['last_local_outcome']={'status':'invalid','feedback':{'code':'source_scope_mismatch'}}
    later['feedback']={'code':'source_scope_mismatch'}
    later['restored_episode_history']={'entries':['PRIVATE_NEW_RESTORE']}
    for value,lookups in ((initial,()),(later,()),(later,({'result':{'text':'A scoped source qualification.'}},))):
        text=render(value,lookup_results=lookups)
        task,steering=split(text)
        assert text.startswith('TASK\n\n')
        assert REFERENCE_PARENT_TASK in task
        assert 'Evaluate the reference preparation and its observed signal.' in task
        assert 'Protein P' in task and 'Assigned source experiment only' in task
        assert 'Keep growth and catalytic measurements separate' in task
        assert 'source_assigned' in task and 'artifact_original' in task and 'publisher-original' in task
        assert 'supplied protein snippet' in task and 'input.faa' in task
        assert 'source.read' in task and 'arguments.source_ref' in task
        assert 'A literature child can investigate a narrower source question' in task
        assert 'Return the source measurements needed for the next comparison.' in task
        assert 'Source endpoint components with conditional assumptions.' in task
        assert 'child_return.literature_assay_cells' in task
        assert 'return.measurements' in task
        assert ASSAY_TASK not in task and EXPERIMENTAL_TASK not in task
        assert 'source_scope_mismatch' not in task
        assert '| tool/source.read | 2 | -0.25 | unavailable | parameters_unbound | 1 |' in steering
        assert 'PRIVATE_' not in text


def test_substantive_parent_questions_preserve_endpoint_amount_transfer_and_credit_boundaries():
    task,_=split(render())
    for distinction in (
        'a reference preparation from the supplied annotation target',
        'A recovery-growth result is not an enzyme activity measurement',
        'A band-signal ratio is not calibrated molar or active protein amount',
        'whether molecules replace one another or coexist',
        'separate from isolation of the measured effect',
        'same paper or equal number',
    ):
        if distinction=='same paper or equal number':
            assert 'A shared name, source paper or equal number' in task
        else:
            assert distinction in task
    assert 'Source findings may qualify or weaken a proposed function' in task
    assert 'Do not manufacture target assessments' in task
    assert 'The configured controller owns continuation' in task
    assert 'no source-completion gate or fixed action count' in task
    assert 'an initial annotation or public searchable name is not required' in task


def test_child_return_is_evidence_in_steering_and_does_not_replace_parent_task():
    value=state()
    value['child_reports']=[{'measurements':[
        {'component':'corrected_activity','value':-.3,'unit':'per_min','origin':'derived',
         'assayed_subject_ref':'reference_requested','qualification':'Endpoint was oxygen consumption.'},
        {'component':'source_presence_index','value':None,'unit':'dimensionless',
         'status':'unavailable','unavailable_reason':'correction_inputs_unreported',
         'private_instructions':'PRIVATE_CHILD_INSTRUCTIONS'}]}]
    task,steering=split(render(value))
    assert REFERENCE_PARENT_TASK in task
    assert 'Endpoint was oxygen consumption.' not in task
    assert 'Admitted requested child returns' in steering
    assert 'Endpoint was oxygen consumption.' in steering
    assert '-0.3' in steering and 'per_min' in steering
    assert 'correction_inputs_unreported' in steering and 'unknown' in steering
    assert 'Source construct P' in steering
    assert 'PRIVATE_' not in task+steering


def test_own_source_outcome_preserves_censoring_and_uncertainty_as_evidence():
    value=state()
    quote='Measured preparation signal was <0.1 µM/min; product coupling was not measured.'
    value['last_local_outcome']={'status':'partial','operation_key':'PRIVATE_OPERATION','result':{
        'text':quote,'source_ref':'source_assigned','artifact_ref':'artifact_original',
        'start':12,'end':94,'coordinate_unit':'utf8_bytes','content_sha256':'PRIVATE_SOURCE_HASH',
        'qualification':'Nondetection is not an observed zero.'}}
    task,steering=split(render(value))
    assert quote not in task
    assert quote in steering and 'Nondetection is not an observed zero.' in steering
    assert '| start | 12 |' in steering and '| end | 94 |' in steering
    assert 'PRIVATE_' not in steering


def test_lookup_return_keeps_parent_task_and_supplies_qualification_only_in_steering():
    result={'result':{'text':'Band signal was not calibrated to molecule count.',
                     'source_ref':'source_assigned','artifact_ref':'artifact_original','start':30,'end':79}}
    task,steering=split(render(lookup_results=[result]))
    assert REFERENCE_PARENT_TASK in task
    assert 'Band signal was not calibrated to molecule count.' not in task
    assert 'Band signal was not calibrated to molecule count.' in steering
    assert '| start | 30 |' in steering and '| end | 79 |' in steering


def test_unrequested_histories_source_inventory_and_other_fact_definitions_are_not_rendered():
    text=render()
    assert 'PRIVATE_' not in text
    assert 'source_unassigned' not in text
    assert 'reference_unrelated' not in text
    assert 'source_unrelated' not in text
    assert 'unrelated_fact' not in text
    assert '"reference_evidence_parent"' not in text
    assert 'scoring_rubric' not in text


def test_renderer_is_pure_and_accepts_frozen_mapping_input():
    value=state()
    before=deepcopy(value)
    result=render(MappingProxyType(value))
    assert value==before
    assert isinstance(result,str)


def test_parent_task_already_in_instructions_is_not_repeated_and_protocol_survives():
    text=render(instructions=REFERENCE_PARENT_TASK+'\n'+INSTRUCTIONS+'\nCaller-specific instruction.')
    task,_=split(text)
    assert task.count(REFERENCE_PARENT_TASK)==1
    assert 'Caller-specific instruction.' in task
    assert 'request_context' in task and 'select_action' in task


@pytest.mark.parametrize('change',[
    lambda value:value.pop('reference_evidence_parent'),
    lambda value:value['literature_experimental_work'].update(aspect='source_rate_comparison'),
    lambda value:value['reference_evidence_parent'].update(version='unrecognized'),
    lambda value:value['reference_evidence_parent'].update(source_refs=None),
    lambda value:value['reference_evidence_parent'].update(source_refs=['source_assigned','source_assigned']),
])
def test_parent_rendering_requires_explicit_valid_caller_context(change):
    value=state()
    change(value)
    with pytest.raises(ValueError):
        render(value)


def test_empty_source_assignment_requests_discovery_from_supplied_material():
    value = state()
    value['reference_evidence_parent']['source_refs'] = []
    task, _ = split(render(value))
    assert 'Experimental source discovery' in task
    assert 'no experimental source' in task
    assert 'supplied protein snippet' in task
