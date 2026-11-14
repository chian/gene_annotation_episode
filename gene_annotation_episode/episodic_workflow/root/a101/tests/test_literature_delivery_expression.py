"""Original versus selected actual call expressions, no provider/native worker."""
import asyncio
from types import SimpleNamespace
import pytest
from .literature_delivery_controls import record,expression,install_selector

@pytest.mark.parametrize('home',record()['homes'])
@pytest.mark.parametrize('method',['call','exchange_decision'])
@pytest.mark.parametrize('selected',[False,True])
@pytest.mark.parametrize('mutation',[False,True])
def test_custom_complete_captured_before_original_operands(home,method,selected,mutation):
    boundary,module=expression(home,method,selected);events=[];received=[];sentinel=object()
    async def original(*args):events.append('original invoked');received.append(args);return sentinel
    async def forbidden(*args):raise AssertionError('later complete lookup changed original callable')
    class Provider:
        @property
        def complete(self):events.append('complete lookup');return self.replacement
        replacement=staticmethod(original)
        async def complete_with_presentation(self,*args,**kwargs):raise AssertionError('custom complete lost authority')
    provider=Provider()
    class Subject:
        @property
        def episode_id(self):
            events.append('episode operand')
            if mutation:provider.replacement=forbidden
            return 'actual-boundary-episode'
    subject=Subject();subject.workflow=SimpleNamespace(provider=provider,specialist=lambda source:(_ for _ in ()).throw(AssertionError('custom provider must not query binding')))
    if selected:install_selector(subject,module)
    instructions='Own supplied instruction';context={'own_literature_outcomes':[{'status':'invalid','qualification':'unresolved'}]}
    schema={'type':'object','properties':{},'additionalProperties':False}
    request={'instructions':instructions,'context':context,'output_schema':schema}
    assert asyncio.run(boundary(subject,instructions,context,schema,request)) is sentinel
    assert events==['complete lookup','episode operand','original invoked']
    args,=received;assert args[:4]==('actual-boundary-episode','REASONING',instructions,context)
    expected=module._action_generation_schema(schema) if method=='call' else schema
    assert args[4]==expected

@pytest.mark.parametrize('home',record()['homes'])
@pytest.mark.parametrize('method',['call','exchange_decision'])
def test_genuine_own_model_capture_selects_declared_projection(home,method):
    from importlib import import_module
    module=import_module(__package__.rsplit('.tests',1)[0]+'.providers')
    boundary,owner=expression(home,method,True)
    provider=object.__new__(module.ModelConnection);provider.worker_lock=asyncio.Lock();received=[]
    async def serial(*args,**kwargs):received.append((args,kwargs));return {'controlled_serial':True}
    provider._complete_serial=serial
    home_module=import_module(__package__.rsplit('.tests',1)[0]+'.'+home.replace('/','.')+'.episode')
    binding=home_module.LiteratureEpisode(SimpleNamespace())
    subject=SimpleNamespace(episode_id='own-boundary',workflow=SimpleNamespace(provider=provider,specialist=lambda source:binding))
    install_selector(subject,owner);schema={'type':'object','properties':{},'additionalProperties':False}
    context={'literature_assignment':{'source_ref':'original-source','target_correspondence':'unresolved'}}
    request={'instructions':'Original instructions','context':context,'output_schema':schema}
    assert asyncio.run(boundary(subject,'Original instructions',context,schema,request))=={'controlled_serial':True}
    args,kw=received[0];assert len(received)==1 and args[:4]==('own-boundary','REASONING','Original instructions',context)
    assert set(kw)=={'prompt_renderer'} and kw['prompt_renderer'] is binding.decision_prompt_renderer
    presenter=object.__new__(module._SessionConnection);presenter.scientific_prompt_states={}
    rendered,instructions=module._ORIGINAL_DECLARED_PRESENTATION(presenter,*args[:4],kw['prompt_renderer'])
    assert 'unresolved' in rendered and 'original-source' in rendered
    assert presenter.scientific_prompt_states[('own-boundary','REASONING')]==context
