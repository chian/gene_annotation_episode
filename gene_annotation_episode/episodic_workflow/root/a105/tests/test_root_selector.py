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


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_actual_private_path_root_transport(home,method,tmp_path,monkeypatch):
    provider,sent,workers=controlled_root(monkeypatch,tmp_path)
    task,binding=selected_task(home,provider)
    context=state_frame(snapshot());before=deepcopy(context)
    assert asyncio.run(invoke(task,home,method,context))=={'fixture':True}
    turn,=[params for name,params in sent if name=='turn/start']
    assert_task(turn['input'][0]['text']);assert_no_bookkeeping(turn['input'][0]['text'])
    saved=json.loads((tmp_path/'connection/session-0001/call-00001/request.json').read_text())
    assert saved['context']==before==context and saved['instructions']==INSTRUCTION_TEXT
    assert saved['presentation']['module']==binding.decision_prompt_renderer.__module__
    assert saved['presentation']['declared_presenter']=={
        'module':own.__name__,'qualname':'_SessionConnection._declared_presentation'}
    assert 'protocol' not in saved['presentation']
    assert provider.workers=={} and len(workers)==1
    # This is the original release bookkeeping over a controlled lifecycle only.
    assert workers[0].scientific_prompt_states=={}


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_original_custom_callee_identity_and_order(home,method):
    traces=[];sentinel=object()
    class Provider:
        @property
        def complete(self):
            traces.append('complete_lookup')
            async def call(*args): traces.append(('completed',args));return sentinel
            return call
        @property
        def complete_with_presentation(self):
            raise AssertionError('custom provider presentation lookup changed')
    source=Provider();task,binding=selected_task(home,source)
    context=state_frame(snapshot())
    assert asyncio.run(invoke(task,home,method,context,original=True)) is sentinel
    original=traces[:];traces.clear()
    assert asyncio.run(invoke(task,home,method,context)) is sentinel
    assert traces==original
    assert traces[0]=='complete_lookup' and len(traces)==2


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


@pytest.mark.parametrize('mutation',('instance_hook','raising_class_hook','custom_getattribute'))
def test_root_override_preserves_original_complete(mutation,tmp_path,monkeypatch):
    from .root_selector_fixtures import root_provider
    provider,sent,workers=controlled_root(monkeypatch,tmp_path)
    def forbidden(*args):
        raise AssertionError('explicit presentation override was consulted')
    if mutation=='instance_hook':
        provider.complete_with_presentation=forbidden
    elif mutation=='raising_class_hook':
        monkeypatch.setattr(root_provider.ModelConnection,'complete_with_presentation',property(forbidden))
    else:
        class Custom(root_provider.ModelConnection):
            def __getattribute__(self,name):
                if name=='complete_with_presentation': return forbidden()
                return object.__getattribute__(self,name)
        provider.__class__=Custom
    task,binding=selected_task(HOMES[0],provider)
    context=state_frame(snapshot())
    assert asyncio.run(invoke(task,HOMES[0],'call',context))=={'fixture':True}
    saved=json.loads((tmp_path/'connection/session-0001/call-00001/request.json').read_text())
    assert 'presentation' not in saved
    assert saved['context']==context


@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_actual_call_expression_resolves_callee_before_arguments(method):
    from .root_selector_fixtures import expression
    failure=LookupError('controlled complete lookup')
    traces=[]
    class Provider:
        @property
        def complete(self):
            traces.append('callee');raise failure
    class Request(dict):
        def __getitem__(self,key): traces.append('argument:'+key);return super().__getitem__(key)
    task,binding=selected_task(HOMES[0],Provider())
    for original in (True,False):
        code,namespace=expression(HOMES[0],method,original=original)
        # A namespace wrapper observes the genuine schema helper, without any
        # production monkeypatch or change to the captured call expression.
        original_schema=namespace['_action_generation_schema']
        def schema(value): traces.append('schema');return original_schema(value)
        namespace['_action_generation_schema']=schema
        traces.clear()
        async def run():
            return await eval(code,namespace,dict(self=task,instructions='unchanged',
                context={},schema={},request=Request(instructions='unchanged',context={},output_schema={})))
        with pytest.raises(LookupError) as caught: asyncio.run(run())
        assert caught.value is failure and traces==['callee']


@pytest.mark.parametrize('kind',('metaclass','borrowed_bound_complete','nonstring_dictionary_key'))
@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_genuine_root_ineligible_receiver_matches_original(kind,method,tmp_path,monkeypatch):
    from .root_selector_fixtures import unusual_root_receiver
    observations=[]
    for original in (True,False):
        directory=tmp_path/('original' if original else 'selected')
        provider,sent,workers=controlled_root(monkeypatch,directory)
        events=[]
        receiver=unusual_root_receiver(provider,kind,directory,events)
        task,binding=selected_task(HOMES[0],receiver)
        context=state_frame(snapshot());unchanged=deepcopy(context)
        assert asyncio.run(invoke(task,HOMES[0],method,context,original=original))=={'fixture':True}
        saved=json.loads((receiver.directory/'session-0001/call-00001/request.json').read_text())
        assert 'presentation' not in saved
        assert saved['context']==context==unchanged
        assert saved['instructions']==INSTRUCTION_TEXT
        assert events==[]
        observations.append({key:saved[key] for key in ('episode_id','role','instructions','context','output_schema','input')})
    assert observations[0]==observations[1]


@pytest.mark.parametrize('method',('call','exchange_decision'))
@pytest.mark.parametrize('change',('provider','episode'))
@pytest.mark.parametrize('fails',(False,True))
def test_original_argument_effect_keeps_captured_root_callee(method,change,fails,tmp_path,monkeypatch):
    from .root_selector_fixtures import invoke_argument_mutation
    failure=RuntimeError('controlled original argument failure')
    observed=[]
    for original in (True,False):
        provider,sent,workers=controlled_root(monkeypatch,tmp_path/('original' if original else 'selected'))
        task,binding=selected_task(HOMES[0],provider)
        initial_episode=task.episode_id
        context=state_frame(snapshot());unchanged=deepcopy(context);events=[]
        work=invoke_argument_mutation(task,HOMES[0],method,context,original=original,
            change=change,events=events,failure=failure if fails else None)
        if fails:
            with pytest.raises(RuntimeError) as caught: asyncio.run(work)
            assert caught.value is failure
            assert sent==[] and workers==[]
            assert provider.session_index==0
            assert not (provider.directory/'session-0001').exists()
            observed.append(events)
        else:
            assert asyncio.run(work)=={'fixture':True}
            saved=json.loads((provider.directory/'session-0001/call-00001/request.json').read_text())
            assert saved['episode_id']==initial_episode
            assert saved['context']==context==unchanged and saved['instructions']==INSTRUCTION_TEXT
            if original:
                assert 'presentation' not in saved
            else:
                assert saved['presentation']['declared_presenter']['module']==own.__name__
                assert_task(saved['input'][0]['text']);assert_no_bookkeeping(saved['input'][0]['text'])
            observed.append((events,{key:saved[key] for key in ('episode_id','role','instructions','context','output_schema')}))
        assert events[0]=='argument_mutation' and 'replacement_called' not in events
        if change=='provider': assert task.workflow.provider is not provider
        else: assert task.episode_id=='changed-during-argument-evaluation'
    assert observed[0]==observed[1]


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
