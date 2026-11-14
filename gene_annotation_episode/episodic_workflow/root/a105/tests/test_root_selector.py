"""DRAFT original call boundary controls; requires source promotion review first."""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest

from ..decision_context import state_frame
from .literature_prompt_fixtures import assert_task, assert_no_bookkeeping, snapshot, INSTRUCTION_TEXT
from .root_selector_fixtures import (HOMES, controlled_root, selected_task, invoke,
    own, root_session)






def test_genuine_presenter_globals_and_frame_state():
    from .. import decision_context
    from .. import scientific_process_prompt
    presenter=own._ORIGINAL_DECLARED_PRESENTATION
    assert presenter is own._SessionConnection._declared_presentation
    assert presenter.__globals__ is vars(own)
    assert presenter.__globals__['apply_state_frame'] is decision_context.apply_state_frame
    assert presenter.__globals__['text_instructions'] is scientific_process_prompt.text_instructions
    session=object.__new__(root_session._SessionConnection)
    session.scientific_prompt_states={}
    state=snapshot();frame=state_frame(state)
    task,binding=selected_task(HOMES[0],SimpleNamespace())
    first=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,frame,binding.decision_prompt_renderer)
    changed=deepcopy(state);changed['feedback']={'category':'arguments_or_reference','code':'condition_mismatch'}
    delta=state_frame(changed,state)
    second=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,delta,binding.decision_prompt_renderer)
    assert_task(first[0]);assert_task(second[0]);assert 'condition_mismatch' in second[0]
    assert session.scientific_prompt_states[('episode','REASONING')]==changed
    assert state==snapshot()










PRESENTATION_HOMES=(
    'published_evidence_assessment',
    'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
)


def qualified_text(text):
    from .literature_prompt_fixtures import SOURCE_TEXT,QUALIFICATION
    assert_task(text);assert_no_bookkeeping(text)
    assert SOURCE_TEXT in text and QUALIFICATION in text


@pytest.mark.parametrize('home',PRESENTATION_HOMES)
def test_original_presenter_lookup_without_base_is_raw_context(home):
    from .root_selector_fixtures import genuine_presenter_session
    from .literature_prompt_fixtures import LOOKUP_TEXT
    presenter,session=genuine_presenter_session()
    task,binding=selected_task(home,SimpleNamespace())
    frame={'version':'decision_context_v1','kind':'decision_lookup_result',
        'decision_index':8,'exchange_index':2,'result':{'status':'completed','text':LOOKUP_TEXT}}
    before=deepcopy(frame)
    text,instructions=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,frame,binding.decision_prompt_renderer)
    assert text==json.dumps(frame,allow_nan=False)
    assert instructions==INSTRUCTION_TEXT and session.scientific_prompt_states=={}
    assert frame==before


@pytest.mark.parametrize('home',PRESENTATION_HOMES)
@pytest.mark.parametrize('case,error_type,message',(
    ('missing_base',TypeError,'previous_model_state_requires_object'),
    ('base_conflict',ValueError,'decision_frame_base_conflict'),
    ('unknown_removed_field',ValueError,'decision_frame_removes_unknown_field'),
    ('revision_conflict',ValueError,'decision_frame_revision_conflict'),
    ('partial_restoration',ValueError,'invalid_decision_restoration'),
))
def test_original_presenter_state_errors_leave_inputs_and_state(home,case,error_type,message):
    from .root_selector_fixtures import genuine_presenter_session,source_qualified_state
    presenter,session=genuine_presenter_session()
    task,binding=selected_task(home,SimpleNamespace())
    state=source_qualified_state();updated=deepcopy(state)
    updated['feedback']={'category':'arguments_or_reference','code':'condition_mismatch'}
    frame=state_frame(updated,state)
    if case!='missing_base':
        presenter(session,'episode','REASONING',INSTRUCTION_TEXT,state_frame(state),binding.decision_prompt_renderer)
    if case=='base_conflict': frame['base_revision']='different-base'
    elif case=='unknown_removed_field': frame['removed_fields']=['field_not_in_original_state']
    elif case=='revision_conflict': frame['revision']='different-revision'
    elif case=='partial_restoration':
        frame=state_frame(state);frame['restored_public_exchanges']=[]
    before=deepcopy((frame,session.scientific_prompt_states))
    with pytest.raises(error_type) as caught:
        presenter(session,'episode','REASONING',INSTRUCTION_TEXT,frame,binding.decision_prompt_renderer)
    assert type(caught.value) is error_type and str(caught.value)==message
    assert (frame,session.scientific_prompt_states)==before


@pytest.mark.parametrize('home',PRESENTATION_HOMES)
def test_actual_renderer_restored_and_same_decision_lookup_qualifications(home):
    from .root_selector_fixtures import genuine_presenter_session,source_qualified_state
    from .literature_prompt_fixtures import LOOKUP_TEXT
    presenter,session=genuine_presenter_session()
    task,binding=selected_task(home,SimpleNamespace())
    state=source_qualified_state()
    result={'status':'completed','text':LOOKUP_TEXT,'content_sha256':'PRIVATE_PIN'}
    frame=state_frame(state)
    frame.update(restored_pending_decision_index=9,restored_public_exchanges=[
        {'exchange_index':3,'response':{'private_extra':'DO_NOT_RENDER_RESPONSE_TRANSCRIPT'},'lookup_result':deepcopy(result)},
        {'exchange_index':4,'response':{'private_extra':'DO_NOT_RENDER_RESPONSE_TRANSCRIPT'}},
    ])
    before=deepcopy(frame)
    text,instructions=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,frame,binding.decision_prompt_renderer)
    qualified_text(text);assert LOOKUP_TEXT in text
    expected_state=own.apply_state_frame(None,frame)
    assert text==binding.decision_prompt_renderer(expected_state,INSTRUCTION_TEXT,lookup_results=[result])
    assert instructions==own.text_instructions(INSTRUCTION_TEXT)
    assert frame==before and session.scientific_prompt_states[('episode','REASONING')]==state
    lookup={'version':'decision_context_v1','kind':'decision_lookup_result',
        'decision_index':9,'exchange_index':5,'result':deepcopy(result)}
    lookup_before=deepcopy(lookup)
    text_after,instructions_after=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,lookup,binding.decision_prompt_renderer)
    assert text_after==text and instructions_after==instructions
    qualified_text(text_after)
    assert lookup==lookup_before and session.scientific_prompt_states[('episode','REASONING')]==state


@pytest.mark.parametrize('home',PRESENTATION_HOMES)
@pytest.mark.parametrize('already_pending',(True,False))
def test_actual_renderer_pending_information_retains_original_list_semantics(home,already_pending):
    from .root_selector_fixtures import genuine_presenter_session,source_qualified_state
    presenter,session=genuine_presenter_session()
    task,binding=selected_task(home,SimpleNamespace())
    state=source_qualified_state()
    state['contract_information_profile']='operation_contract_information_v1'
    pending=[{'status':'completed','text':'Controlled pending source-method note one.'},
        {'status':'completed','text':'Controlled pending source-method note two.'}]
    result=deepcopy(pending[1]) if already_pending else {'status':'completed','text':'Controlled newly received source-method note.'}
    presenter(session,'episode','REASONING',INSTRUCTION_TEXT,state_frame(state),binding.decision_prompt_renderer)
    frame={'version':'decision_context_v1','kind':'decision_lookup_result','decision_index':9,
        'exchange_index':5,'pending_contract_information':deepcopy(pending),'result':result}
    before=deepcopy((frame,state,session.scientific_prompt_states))
    text,instructions=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,frame,binding.decision_prompt_renderer)
    expected=pending if already_pending else [*pending,result]
    expected_state=own.apply_state_frame(None,state_frame(state))
    assert text==binding.decision_prompt_renderer(expected_state,INSTRUCTION_TEXT,lookup_results=expected)
    assert instructions==own.text_instructions(INSTRUCTION_TEXT)
    qualified_text(text)
    for record in expected: assert record['text'] in text
    assert (frame,state,session.scientific_prompt_states)==before
