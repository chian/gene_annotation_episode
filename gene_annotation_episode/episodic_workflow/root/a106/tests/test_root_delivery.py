"""Unpromoted actual A106 binding/root transport boundaries, no scientific grading."""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from ..decision_context import state_frame
from .root_delivery_fixtures import (HOMES, MANIFEST, selected_task, controlled_root,
    state_for, assert_visible, invoke, expression, invoke_argument_mutation,
    genuine_presenter_session, unusual_root_receiver, own, root_provider,
    INSTRUCTION_TEXT, OUTPUT_SCHEMA)

REPRESENTATIVES=('published_evidence_assessment','scientific_process/published_evidence_assessment',
    'execution_progress_assessment','scientific_process/execution_progress_assessment')

@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_actual_binding_default_root_delivery(home,method,tmp_path,monkeypatch):
    provider,sent,workers=controlled_root(monkeypatch,tmp_path)
    task,binding=selected_task(home,provider)
    state=state_for(home);context=state_frame(state);before=deepcopy(context)
    assert asyncio.run(invoke(task,home,method,context))=={'fixture':True}
    turn,=[params for name,params in sent if name=='turn/start']
    assert_visible(home,turn['input'][0]['text'])
    expected_state=own.apply_state_frame(None,context)
    assert turn['input'][0]['text']==binding.decision_prompt_renderer(expected_state,INSTRUCTION_TEXT,lookup_results=[])
    saved=json.loads((provider.directory/'session-0001/call-00001/request.json').read_text())
    assert saved['context']==context==before and saved['instructions']==INSTRUCTION_TEXT
    assert saved['presentation']['module']==binding.decision_prompt_renderer.__module__
    assert saved['presentation']['qualname']==binding.decision_prompt_renderer.__qualname__
    assert saved['presentation']['declared_presenter']=={'module':own.__name__,'qualname':'_SessionConnection._declared_presentation'}
    assert 'protocol' not in saved['presentation']
    assert provider.workers=={} and len(workers)==1
    assert workers[0].scientific_prompt_states=={}


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('method',('call','exchange_decision'))
@pytest.mark.parametrize('has_forbidden_hook',(False,True))
def test_real_custom_complete_and_no_hook_preserve_original(home,method,has_forbidden_hook):
    events=[];answer=object()
    class Provider:
        @property
        def complete(self):
            events.append('complete_lookup')
            async def callback(*args):events.append(('complete',args));return answer
            return callback
    class WithHook(Provider):
        @property
        def complete_with_presentation(self):raise AssertionError('custom hook must not be consulted')
    task,binding=selected_task(home,(WithHook if has_forbidden_hook else Provider)())
    context=state_frame(state_for(home));observed=[]
    for original in (True,False):
        events.clear()
        assert asyncio.run(invoke(task,home,method,context,original=original)) is answer
        observed.append(events[:])
    assert observed[0]==observed[1] and observed[0][0]=='complete_lookup'
    assert len(observed[0])==2 and len(observed[0][1][1])==5


@pytest.mark.parametrize('home',REPRESENTATIVES)
@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_complete_lookup_error_precedes_argument_evaluation(home,method):
    failure=LookupError('original complete lookup');events=[]
    class Provider:
        @property
        def complete(self):events.append('callee');raise failure
    class Request(dict):
        def __getitem__(self,key):events.append(key);return super().__getitem__(key)
    task,binding=selected_task(home,Provider())
    for original in (True,False):
        code,namespace=expression(home,method,original=original)
        actual=namespace['_action_generation_schema']
        def schema(value):events.append('schema');return actual(value)
        namespace['_action_generation_schema']=schema;events.clear()
        async def exercise():
            return await eval(code,namespace,dict(self=task,instructions=INSTRUCTION_TEXT,
                context={},schema=OUTPUT_SCHEMA,request=Request(instructions=INSTRUCTION_TEXT,context={},output_schema=OUTPUT_SCHEMA)))
        with pytest.raises(LookupError) as caught:asyncio.run(exercise())
        assert caught.value is failure and events==['callee']


@pytest.mark.parametrize('home',REPRESENTATIVES)
@pytest.mark.parametrize('method',('call','exchange_decision'))
@pytest.mark.parametrize('change',('provider','episode'))
@pytest.mark.parametrize('fails',(False,True))
def test_original_argument_mutation_preserves_root_callee(home,method,change,fails,tmp_path,monkeypatch):
    failure=RuntimeError('original argument failure');observations=[]
    for original in (True,False):
        provider,sent,workers=controlled_root(monkeypatch,tmp_path/('original' if original else 'selected'))
        task,binding=selected_task(home,provider);initial_episode=task.episode_id
        context=state_frame(state_for(home));before=deepcopy(context);events=[]
        work=invoke_argument_mutation(task,home,method,context,original=original,change=change,events=events,failure=failure if fails else None)
        if fails:
            with pytest.raises(RuntimeError) as caught:asyncio.run(work)
            assert caught.value is failure and sent==[] and workers==[] and provider.session_index==0
            assert not (provider.directory/'session-0001').exists()
            observations.append(events)
        else:
            assert asyncio.run(work)=={'fixture':True}
            saved=json.loads((provider.directory/'session-0001/call-00001/request.json').read_text())
            assert saved['episode_id']==initial_episode and saved['context']==context==before
            if original:assert 'presentation' not in saved
            else:
                assert saved['presentation']['declared_presenter']['module']==own.__name__
                assert_visible(home,saved['input'][0]['text'])
            observations.append((events,{k:saved[k] for k in ('episode_id','role','instructions','context','output_schema')}))
        assert events[0]=='argument_mutation' and 'replacement_called' not in events
        if change=='provider':assert task.workflow.provider is not provider
        else:assert task.episode_id=='changed-during-argument-evaluation'
    assert observations[0]==observations[1]


@pytest.mark.parametrize('home',REPRESENTATIVES)
@pytest.mark.parametrize('method',('call','exchange_decision'))
@pytest.mark.parametrize('kind',('metaclass','borrowed_bound_complete','nonstring_dictionary_key'))
def test_root_ineligible_protocol_matches_original(home,method,kind,tmp_path,monkeypatch):
    observations=[]
    for original in (True,False):
        directory=tmp_path/('original' if original else 'selected')
        provider,sent,workers=controlled_root(monkeypatch,directory);events=[]
        receiver=unusual_root_receiver(provider,kind,directory,events)
        task,binding=selected_task(home,receiver);context=state_frame(state_for(home))
        assert asyncio.run(invoke(task,home,method,context,original=original))=={'fixture':True}
        saved=json.loads((receiver.directory/'session-0001/call-00001/request.json').read_text())
        assert 'presentation' not in saved and saved['context']==context and events==[]
        observations.append({k:saved[k] for k in ('episode_id','role','instructions','context','output_schema','input')})
    assert observations[0]==observations[1]


@pytest.mark.parametrize('home',REPRESENTATIVES)
@pytest.mark.parametrize('mutation',('instance_hook','raising_class_hook','custom_getattribute'))
def test_root_explicit_hook_keeps_original_complete(home,mutation,tmp_path,monkeypatch):
    observations=[]
    def forbidden(*args):raise AssertionError('explicit presentation override consulted')
    for original in (True,False):
        with monkeypatch.context() as patch:
            provider,sent,workers=controlled_root(patch,tmp_path/('original' if original else 'selected'))
            if mutation=='instance_hook':provider.complete_with_presentation=forbidden
            elif mutation=='raising_class_hook':patch.setattr(root_provider.ModelConnection,'complete_with_presentation',property(forbidden))
            else:
                class Custom(root_provider.ModelConnection):
                    def __getattribute__(self,name):
                        if name=='complete_with_presentation':return forbidden()
                        return object.__getattribute__(self,name)
                provider.__class__=Custom
            task,binding=selected_task(home,provider);context=state_frame(state_for(home))
            assert asyncio.run(invoke(task,home,'call',context,original=original))=={'fixture':True}
            saved=json.loads((provider.directory/'session-0001/call-00001/request.json').read_text())
            assert 'presentation' not in saved
            observations.append({k:saved[k] for k in ('episode_id','role','instructions','context','output_schema','input')})
    assert observations[0]==observations[1]


@pytest.mark.parametrize('home',REPRESENTATIVES)
def test_genuine_presenter_bootstrap_delta_and_lookup(home):
    presenter,session=genuine_presenter_session();task,binding=selected_task(home,SimpleNamespace())
    state=state_for(home);frame=state_frame(state);unchanged=deepcopy(frame)
    first=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,frame,binding.decision_prompt_renderer)
    assert_visible(home,first[0]);assert frame==unchanged
    changed=deepcopy(state);changed['feedback']={'code':'condition_mismatch'}
    second=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,state_frame(changed,state),binding.decision_prompt_renderer)
    assert_visible(home,second[0]);assert 'condition_mismatch' in second[0]
    result={'status':'completed','text':'Actual explicitly requested source-method note.'}
    lookup={'version':'decision_context_v1','kind':'decision_lookup_result','decision_index':2,'exchange_index':1,'result':result}
    before=deepcopy((lookup,session.scientific_prompt_states))
    text,instructions=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,lookup,binding.decision_prompt_renderer)
    expected=own.apply_state_frame(None,state_frame(changed))
    assert text==binding.decision_prompt_renderer(expected,INSTRUCTION_TEXT,lookup_results=[result])
    assert result['text'] in text and instructions==own.text_instructions(INSTRUCTION_TEXT)
    assert (lookup,session.scientific_prompt_states)==before


@pytest.mark.parametrize('home',REPRESENTATIVES)
def test_lookup_without_base_retains_original_raw_fallback(home):
    presenter,session=genuine_presenter_session();task,binding=selected_task(home,SimpleNamespace())
    frame={'version':'decision_context_v1','kind':'decision_lookup_result','decision_index':2,'exchange_index':1,'result':{'text':'controlled lookup'}}
    before=deepcopy(frame)
    text,instructions=presenter(session,'episode','REASONING',INSTRUCTION_TEXT,frame,binding.decision_prompt_renderer)
    assert text==json.dumps(frame,allow_nan=False) and instructions==INSTRUCTION_TEXT
    assert frame==before and session.scientific_prompt_states=={}


@pytest.mark.parametrize('home',REPRESENTATIVES)
@pytest.mark.parametrize('case,error_type,message',(
    ('missing_base',TypeError,'previous_model_state_requires_object'),
    ('base_conflict',ValueError,'decision_frame_base_conflict'),
    ('unknown_removed_field',ValueError,'decision_frame_removes_unknown_field'),
    ('revision_conflict',ValueError,'decision_frame_revision_conflict'),
    ('partial_restoration',ValueError,'invalid_decision_restoration')))
def test_original_frame_errors_preserve_exact_type_text_and_state(home,case,error_type,message):
    presenter,session=genuine_presenter_session();task,binding=selected_task(home,SimpleNamespace())
    state=state_for(home);changed=deepcopy(state);changed['feedback']={'code':'condition_mismatch'}
    frame=state_frame(changed,state)
    if case!='missing_base':presenter(session,'episode','REASONING',INSTRUCTION_TEXT,state_frame(state),binding.decision_prompt_renderer)
    if case=='base_conflict':frame['base_revision']='wrong-base'
    elif case=='unknown_removed_field':frame['removed_fields']=['unknown_original_field']
    elif case=='revision_conflict':frame['revision']='wrong-revision'
    elif case=='partial_restoration':frame=state_frame(state);frame['restored_public_exchanges']=[]
    before=deepcopy((frame,session.scientific_prompt_states))
    with pytest.raises(error_type) as caught:presenter(session,'episode','REASONING',INSTRUCTION_TEXT,frame,binding.decision_prompt_renderer)
    assert type(caught.value) is error_type and str(caught.value)==message
    assert (frame,session.scientific_prompt_states)==before


@pytest.mark.parametrize('home',REPRESENTATIVES)
@pytest.mark.parametrize('method',('call','exchange_decision'))
def test_custom_complete_failure_keeps_original_exception_identity(home,method):
    failure=RuntimeError('original custom complete failure');events=[]
    class Provider:
        @property
        def complete(self):
            events.append('lookup')
            async def callback(*args):events.append(('call',args));raise failure
            return callback
        @property
        def complete_with_presentation(self):raise AssertionError('custom hook lookup')
    task,binding=selected_task(home,Provider());traces=[]
    for original in (True,False):
        events.clear()
        with pytest.raises(RuntimeError) as caught:
            asyncio.run(invoke(task,home,method,state_frame(state_for(home)),original=original))
        assert caught.value is failure
        traces.append(events[:])
    assert traces[0]==traces[1]
