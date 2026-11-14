"""Real private selector/root transport controls; no autonomous scientific work."""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from ..decision_context import state_frame
from .root_delivery_state import snapshot, changed_state, assert_rendered, INSTRUCTION_TEXT, LOOKUP_TEXT
from .root_delivery_fixtures import (HOMES, own, root_provider, controlled_root,
    selected_task, invoke, expression, invoke_mutation, presenter_session)






@pytest.mark.parametrize('home',HOMES)
def test_own_presenter_reconstructs_real_frames_and_selected_renderer(home):
    presenter,session=presenter_session();task,binding=selected_task(home,SimpleNamespace())
    first=snapshot();second=changed_state();before=deepcopy((first,second))
    initial=state_frame(first);delta=state_frame(second,first)
    text,_=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,initial,binding.decision_prompt_renderer)
    assert_rendered(text)
    text,instructions=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,delta,binding.decision_prompt_renderer)
    assert_rendered(text,changed=True)
    assert text==binding.decision_prompt_renderer(second,INSTRUCTION_TEXT,lookup_results=[])
    assert instructions==own.text_instructions(INSTRUCTION_TEXT)
    assert session.scientific_prompt_states[('episode','REASONING')]==second
    result={'status':'completed','text':LOOKUP_TEXT}
    lookup={'version':'decision_context_v1','kind':'decision_lookup_result','decision_index':8,'exchange_index':2,'result':result}
    text,_=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,lookup,binding.decision_prompt_renderer)
    assert_rendered(text,changed=True);assert LOOKUP_TEXT in text
    assert text==binding.decision_prompt_renderer(second,INSTRUCTION_TEXT,lookup_results=[result])
    assert (first,second)==before

@pytest.mark.parametrize('case,error_type,message',(
    ('missing_base',TypeError,'previous_model_state_requires_object'),
    ('base_conflict',ValueError,'decision_frame_base_conflict'),
    ('unknown_removed_field',ValueError,'decision_frame_removes_unknown_field'),
    ('revision_conflict',ValueError,'decision_frame_revision_conflict'),
    ('partial_restoration',ValueError,'invalid_decision_restoration')))
def test_presenter_original_errors_preserve_state(case,error_type,message):
    presenter,session=presenter_session();task,binding=selected_task(HOMES[0],SimpleNamespace())
    first=snapshot();frame=state_frame(changed_state(),first)
    if case!='missing_base':presenter(session,'episode','REASONING',INSTRUCTION_TEXT,state_frame(first),binding.decision_prompt_renderer)
    if case=='base_conflict':frame['base_revision']='wrong'
    elif case=='unknown_removed_field':frame['removed_fields']=['not_an_original_field']
    elif case=='revision_conflict':frame['revision']='wrong'
    elif case=='partial_restoration':frame=state_frame(first);frame['restored_public_exchanges']=[]
    before=deepcopy((frame,session.scientific_prompt_states))
    with pytest.raises(error_type) as caught:presenter(session,'episode','REASONING',INSTRUCTION_TEXT,frame,binding.decision_prompt_renderer)
    assert type(caught.value) is error_type and str(caught.value)==message
    assert (frame,session.scientific_prompt_states)==before

@pytest.mark.parametrize('already_pending',(True,False))
def test_presenter_retains_restored_lookup_and_pending_order(already_pending):
    presenter,session=presenter_session();task,binding=selected_task(HOMES[0],SimpleNamespace())
    state=changed_state();state['contract_information_profile']='operation_contract_information_v1'
    pending=[{'status':'completed','text':LOOKUP_TEXT},{'status':'completed','text':'Controlled second contract note.'}]
    frame=state_frame(state);frame.update(restored_pending_decision_index=9,
        restored_public_exchanges=[{'exchange_index':3,'lookup_result':deepcopy(pending[0])},
            {'exchange_index':4,'response':{'private_extra':'DO_NOT_RENDER_RESPONSE_TRANSCRIPT'}}])
    before=deepcopy(frame)
    text,_=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,frame,binding.decision_prompt_renderer)
    assert text==binding.decision_prompt_renderer(state,INSTRUCTION_TEXT,lookup_results=[pending[0]])
    assert frame==before and 'DO_NOT_RENDER_RESPONSE_TRANSCRIPT' not in text
    result=deepcopy(pending[1]) if already_pending else {'status':'completed','text':'Controlled new contract note.'}
    lookup={'version':'decision_context_v1','kind':'decision_lookup_result','pending_contract_information':deepcopy(pending),'result':result}
    before=deepcopy((lookup,session.scientific_prompt_states))
    text,_=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,lookup,binding.decision_prompt_renderer)
    expected=pending if already_pending else [*pending,result]
    assert text==binding.decision_prompt_renderer(state,INSTRUCTION_TEXT,lookup_results=expected)
    for item in expected:assert item['text'] in text
    assert (lookup,session.scientific_prompt_states)==before


def test_presenter_lookup_without_base_preserves_raw_context():
    presenter,session=presenter_session();task,binding=selected_task(HOMES[0],SimpleNamespace())
    context={'version':'decision_context_v1','kind':'decision_lookup_result','result':{'text':LOOKUP_TEXT}}
    before=deepcopy(context)
    text,instructions=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,context,binding.decision_prompt_renderer)
    assert text==json.dumps(context,allow_nan=False) and instructions==INSTRUCTION_TEXT
    assert context==before and session.scientific_prompt_states=={}
