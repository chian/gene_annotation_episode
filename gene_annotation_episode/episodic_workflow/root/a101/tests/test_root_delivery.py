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
@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_real_registry_renderer_reaches_root_transport(home,method,tmp_path,monkeypatch):
    provider,sent,workers=controlled_root(monkeypatch,tmp_path)
    task,binding=selected_task(home,provider)
    context=state_frame(snapshot());before=deepcopy(context)
    assert asyncio.run(invoke(task,home,method,context))=={'fixture':True}
    turn,=[params for name,params in sent if name=='turn/start']
    assert_rendered(turn['input'][0]['text'])
    saved=json.loads((provider.directory/'session-0001/call-00001/request.json').read_text())
    assert saved['context']==before==context and saved['instructions']==INSTRUCTION_TEXT
    assert saved['presentation']['module']==binding.decision_prompt_renderer.__module__
    assert saved['presentation']['declared_presenter']=={'module':own.__name__,'qualname':'_SessionConnection._declared_presentation'}
    assert 'protocol' not in saved['presentation']
    assert saved['input']==turn['input'] and saved['output_schema']==turn['outputSchema']
    assert provider.workers=={} and len(workers)==1 and workers[0].scientific_prompt_states=={}

@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_custom_descriptor_callee_and_five_arguments_match_original(home,method):
    traces=[];answer=object()
    class Provider:
        @property
        def complete(self):
            traces.append('get_complete')
            async def complete(*args):traces.append(('complete',args));return answer
            return complete
        @property
        def complete_with_presentation(self):raise AssertionError('custom hook was consulted')
    task,binding=selected_task(home,Provider());context=state_frame(snapshot())
    assert asyncio.run(invoke(task,home,method,context,original=True)) is answer
    before=deepcopy(traces);traces.clear()
    assert asyncio.run(invoke(task,home,method,context)) is answer
    assert traces==before and traces[0]=='get_complete'
    assert len(traces)==2 and len(traces[1][1])==5

@pytest.mark.parametrize('method',('call','exchange_decision'))
@pytest.mark.parametrize('case',('no_binding','instance_hook','class_hook','serial_shadow','metaclass'))
def test_root_ineligible_and_no_hook_preserve_original_request(case,method,tmp_path,monkeypatch):
    observed=[]
    for original in (True,False):
        with monkeypatch.context() as patch:
            provider,sent,workers=controlled_root(patch,tmp_path/str(original))
            def forbidden(*args):raise AssertionError('ineligible hook was consulted')
            if case=='instance_hook':provider.complete_with_presentation=forbidden
            elif case=='class_hook':patch.setattr(root_provider.ModelConnection,'complete_with_presentation',property(forbidden))
            elif case=='serial_shadow':
                # Same genuine callable in instance dictionary is deliberately
                # an explicit override; root selector must fall back.
                provider._complete_serial=provider._complete_serial
            elif case=='metaclass':
                class Meta(type):
                    def __getattribute__(cls,name):
                        if name=='__dict__':raise AssertionError('metaclass dictionary consulted')
                        return type.__getattribute__(cls,name)
                class Custom(root_provider.ModelConnection,metaclass=Meta):pass
                provider.__class__=Custom
            task,binding=selected_task(HOMES[0],provider)
            if case=='no_binding':
                # Exact existing Workflow.specialist empty-path contract. Not a
                # claimed valid scientific invocation or invented binding.
                task.path=();assert task.workflow.specialist(task) is None
            context=state_frame(snapshot());before=deepcopy(context)
            assert asyncio.run(invoke(task,HOMES[0],method,context,original=original))=={'fixture':True}
            saved=json.loads((provider.directory/'session-0001/call-00001/request.json').read_text())
            assert 'presentation' not in saved and saved['context']==context==before
            observed.append({k:saved[k] for k in ('episode_id','role','instructions','context','output_schema','input')})
    assert observed[0]==observed[1]

@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_complete_descriptor_error_precedes_all_argument_effects(method):
    failure=LookupError('controlled complete lookup');events=[]
    class Provider:
        @property
        def complete(self):events.append('callee');raise failure
    class Request(dict):
        def __getitem__(self,key):events.append('argument:'+key);return super().__getitem__(key)
    task,binding=selected_task(HOMES[0],Provider())
    for original in (True,False):
        code,namespace=expression(HOMES[0],method,original=original)
        actual=namespace['_action_generation_schema']
        def schema(value):events.append('schema');return actual(value)
        namespace['_action_generation_schema']=schema;events.clear()
        async def run():
            return await eval(code,namespace,dict(self=task,instructions='unchanged',context={},schema={},
                request=Request(instructions='unchanged',context={},output_schema={})))
        with pytest.raises(LookupError) as caught:asyncio.run(run())
        assert caught.value is failure and events==['callee']

@pytest.mark.parametrize('method',('call','exchange_decision'))
@pytest.mark.parametrize('change',('provider','episode'))
@pytest.mark.parametrize('fails',(False,True))
def test_argument_mutation_keeps_original_captured_callee_and_identity(method,change,fails,tmp_path,monkeypatch):
    observed=[];failure=RuntimeError('controlled argument error')
    for original in (True,False):
        provider,sent,workers=controlled_root(monkeypatch,tmp_path/str(original))
        task,binding=selected_task(HOMES[0],provider);episode=task.episode_id
        context=state_frame(snapshot());before=deepcopy(context);events=[]
        work=invoke_mutation(task,HOMES[0],method,context,original=original,change=change,
            events=events,failure=failure if fails else None)
        if fails:
            with pytest.raises(RuntimeError) as caught:asyncio.run(work)
            assert caught.value is failure and not sent and not workers
            observed.append(events)
        else:
            assert asyncio.run(work)=={'fixture':True}
            saved=json.loads((provider.directory/'session-0001/call-00001/request.json').read_text())
            assert saved['episode_id']==episode and saved['context']==before==context
            if original:assert 'presentation' not in saved
            else:
                assert saved['presentation']['declared_presenter']['module']==own.__name__
                assert_rendered(saved['input'][0]['text'])
            observed.append((events,{k:saved[k] for k in ('episode_id','role','instructions','context','output_schema')}))
        assert events[0]=='argument_mutation'
        if change=='provider':assert task.workflow.provider is not provider
        else:assert task.episode_id=='changed-during-argument-evaluation'
    assert observed[0]==observed[1]

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

@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_custom_complete_exception_identity_is_not_wrapped(method):
    error=RuntimeError('controlled custom completion error');received=[]
    class Provider:
        async def complete(self,*args):received.append(args);raise error
        @property
        def complete_with_presentation(self):raise AssertionError('custom hook consulted')
    task,binding=selected_task(HOMES[0],Provider());context=state_frame(snapshot())
    for original in (True,False):
        with pytest.raises(RuntimeError) as caught:asyncio.run(invoke(task,HOMES[0],method,context,original=original))
        assert caught.value is error
    assert received[0]==received[1] and len(received[0])==5

def test_presenter_lookup_without_base_preserves_raw_context():
    presenter,session=presenter_session();task,binding=selected_task(HOMES[0],SimpleNamespace())
    context={'version':'decision_context_v1','kind':'decision_lookup_result','result':{'text':LOOKUP_TEXT}}
    before=deepcopy(context)
    text,instructions=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,context,binding.decision_prompt_renderer)
    assert text==json.dumps(context,allow_nan=False) and instructions==INSTRUCTION_TEXT
    assert context==before and session.scientific_prompt_states=={}
