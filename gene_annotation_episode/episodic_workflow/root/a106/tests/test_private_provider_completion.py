"""Actual original/private call-expression evaluation; controlled provider serial port.

No provider process, scientific action or application source is manufactured.
Both expressions are extracted from their actual defining source in this epoch.
"""
import ast
import asyncio
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from types import MethodType, SimpleNamespace
import pytest

BASE=__package__.rsplit('.tests',1)[0]
ROOT=Path(__file__).resolve().parents[1]
HOMES=tuple(sorted(str(p.parent.relative_to(ROOT)).replace('/','.') for p in ROOT.rglob('episode.py')
    if 'class LiteratureEpisode(' in p.read_text() or 'class MonitorEpisode(' in p.read_text()))

def boundary(module_path, class_name, method_name):
    tree=ast.parse(module_path.read_bytes())
    cls,=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name]
    method,=[n for n in cls.body if isinstance(n,ast.AsyncFunctionDef) and n.name==method_name]
    calls=[n for n in ast.walk(method) if isinstance(n,ast.Call) and (
        isinstance(n.func,ast.Attribute) and n.func.attr in ('complete','complete_decision')
        or isinstance(n.func,ast.Call) and isinstance(n.func.func,ast.Attribute) and n.func.func.attr=='decision_completion')]
    call,=calls
    # Execute precisely the original/current expression, not a hand-written
    # approximation which could move the provider descriptor lookup.
    wrapper=ast.parse('async def invoke(self,instructions,context,schema,request,_action_generation_schema):\n    pass\n')
    wrapper.body[0].body=[ast.Return(value=ast.Await(value=deepcopy(call)))]
    namespace={};exec(compile(ast.fix_missing_locations(wrapper),str(module_path),'exec'),namespace)
    return namespace['invoke']

CASES=('default','subclass_complete','instance_complete','complete_property',
    'presentation_property','instance_presentation','dynamic_presentation',
    'shadow_dict','dict_subclass','nonstring_key','string_subclass_key','lookup_error','custom_metaclass','callable_complete',
    'base_complete_replaced','callback_error','operand_error','operand_replaces_complete')

@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('method_name',('call','exchange_decision'))
@pytest.mark.parametrize('case',CASES)
def test_actual_original_and_private_provider_boundary(home,method_name,case,monkeypatch):
    providers=import_module(BASE+'.providers')
    module=import_module(BASE+'.'+home+'.episode')
    Binding=getattr(module,'LiteratureEpisode',None) or module.MonitorEpisode
    Task=Binding.decision_source_type
    decision=import_module(BASE+'.'+home+'.task_decision')
    cls=[v for v in vars(decision).values() if isinstance(v,type) and v.__module__==decision.__name__ and any(n in v.__dict__ for n in ('complete_decision','decision_completion'))]
    owner,=cls
    original=boundary(ROOT/'runtime.py','DecisionSource',method_name)
    current=boundary(ROOT/home.replace('.','/')/'task_decision.py',owner.__name__,method_name)
    original_complete=providers.ModelConnection.complete
    marker=Binding.decision_prompt_renderer
    answer=object();failure=RuntimeError('same callback error');operand_failure=ValueError('same operand error')
    instructions=object();context={};schema={};episodes=[]

    async def exercise(invoke):
        events=[]
        async def custom(*args):
            events.append(('complete',args))
            if case=='callback_error':raise failure
            return answer
        async def custom_method(self,*args):return await custom(*args)
        class Override(providers.ModelConnection):
            async def complete(self,*args):return await custom(*args)
        class CompleteProperty(providers.ModelConnection):
            @property
            def complete(self):
                events.append(('lookup',))
                if case=='lookup_error':raise failure
                return custom
        class PresentationProperty(providers.ModelConnection):
            @property
            def complete_with_presentation(self):raise AssertionError('dynamic presentation descriptor invoked')
        class DynamicPresentation(providers.ModelConnection):
            def __getattribute__(self,name):
                if name=='complete_with_presentation':raise AssertionError('dynamic presentation lookup')
                return super().__getattribute__(name)
        class ShadowDict(providers.ModelConnection):
            @property
            def __dict__(self):raise AssertionError('overridden instance dict lookup')
        meta_active=[]
        class Meta(type):
            def __getattribute__(self,name):
                if meta_active and name in ('__dict__','__mro__'):raise AssertionError('custom metaclass introspection')
                return super().__getattribute__(name)
        class CustomMeta(providers.ModelConnection,metaclass=Meta):pass
        kind={'subclass_complete':Override,'complete_property':CompleteProperty,'lookup_error':CompleteProperty,
              'presentation_property':PresentationProperty,'dynamic_presentation':DynamicPresentation,
              'shadow_dict':ShadowDict,'custom_metaclass':CustomMeta}.get(case,providers.ModelConnection)
        provider=object.__new__(kind);provider.worker_lock=asyncio.Lock()
        async def serial(self,*args,**kwargs):events.append(('serial',args,kwargs));return answer
        provider._complete_serial=MethodType(serial,provider)
        if case in ('instance_complete','callback_error','operand_error','operand_replaces_complete'):provider.complete=custom
        if case=='instance_presentation':
            async def forbidden(*args,**kwargs):raise AssertionError('instance presentation selected')
            provider.complete_with_presentation=forbidden
        if case=='dict_subclass':
            class InstanceDict(dict):
                def items(self):raise AssertionError('overridden dict.items invoked')
            provider.__dict__=InstanceDict(provider.__dict__)
        if case=='string_subclass_key':
            class StringKey(str):
                __hash__=str.__hash__
                def __eq__(self,other):raise AssertionError('string subclass equality invoked')
            provider.__dict__[StringKey('controlled_unique_nonbuiltin_key')]=True
        if case=='nonstring_key':
            class Key:
                def __hash__(self):return 230499
                def __eq__(self,other):raise AssertionError('nonstring-key equality invoked')
            provider.__dict__[Key()]=True
        if case=='callable_complete':
            class Callback:
                def __getattribute__(self,name):
                    if name in ('__func__','__self__'):raise AssertionError('callable identity probe')
                    return object.__getattribute__(self,name)
                async def __call__(self,*args):return await custom(*args)
            provider.complete=Callback()
        if case=='base_complete_replaced':monkeypatch.setattr(providers.ModelConnection,'complete',custom_method)
        def specialist(source):events.append(('specialist',));return Binding
        class Source(Task):
            @property
            def episode_id(self):
                events.append(('episode',))
                if case=='operand_error':raise operand_failure
                if case=='operand_replaces_complete':
                    async def replaced(*args):raise AssertionError('provider complete was reloaded after operands')
                    provider.complete=replaced
                return 'original-call-episode'
        source=object.__new__(Source);source.workflow=SimpleNamespace(provider=provider,specialist=specialist)
        class Request(dict):
            def __getitem__(self,key):events.append(('request',key));return super().__getitem__(key)
        request=Request(instructions=instructions,context=context,output_schema=schema)
        def generated(value):events.append(('schema',));assert value is schema;return schema
        meta_active.append(True)
        try:result=await invoke(source,instructions,context,schema,request,generated)
        except BaseException as caught:
            assert (case in ('callback_error','lookup_error') and caught is failure) or (case=='operand_error' and caught is operand_failure)
            result=caught
        finally:
            if case=='base_complete_replaced':monkeypatch.setattr(providers.ModelConnection,'complete',original_complete)
        return result,events

    old_result,old_events=asyncio.run(exercise(original))
    new_result,new_events=asyncio.run(exercise(current))
    assert old_result is new_result
    private_default=case in ('default','dynamic_presentation','shadow_dict','dict_subclass')
    if private_default:
        assert [e for e in new_events if e[0]!='specialist'][:-1]==old_events[:-1]
        assert new_events[-2][0]=='specialist'
        assert old_events[-1]==('serial',('original-call-episode','REASONING',instructions,context,schema),{})
        assert new_events[-1]==('serial',old_events[-1][1],{'prompt_renderer':marker})
    else:assert new_events==old_events
    if case=='complete_property':assert old_events[0]==('lookup',) and old_events.count(('lookup',))==1
    if case=='operand_error':assert old_result is operand_failure and not any(e[0] in ('complete','serial','specialist') for e in new_events)
    if case=='operand_replaces_complete':assert old_events[-1][0]=='complete'
