"""Provider transport preserves state reconstruction and accepts a declared renderer."""
import asyncio
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace
import pytest

AXES=('a101','a102','a103','a104','a106','a107','a110')

@pytest.fixture(params=AXES)
def provider(request):
    return importlib.import_module('gene_annotation_episode.episodic_workflow.root.'+request.param+'.providers')


def connection(provider):
    value=object.__new__(provider._SessionConnection)
    value.scientific_prompt_states={}
    return value


def test_legacy_generic_context_keeps_its_original_presentation(provider):
    value=connection(provider)
    context={'unrelated':'original information'}
    assert value._presentation('episode','REASONING','Original instructions',context)==(json.dumps(context,allow_nan=False),'Original instructions')


def test_declared_renderer_reconstructs_bootstrap_update_and_lookup(provider):
    value=connection(provider);seen=[]
    def render(state,instructions,*,lookup_results=()):
        seen.append((deepcopy(state),list(lookup_results)))
        return 'declared monitor: '+str(state['current_credit'])
    state={'monitor_assignment':{'version':'monitor_assignment_v1'},'hpc_commission':{},'current_credit':0}
    first=provider.state_frame(state,None) if hasattr(provider,'state_frame') else importlib.import_module(provider.__package__+'.decision_context').state_frame(state,None)
    updated={**state,'current_credit':2.5}
    frame_module=importlib.import_module(provider.__package__+'.decision_context')
    value._presentation('episode','REASONING','Original instructions',first,prompt_renderer=render)
    value._presentation('episode','REASONING','Original instructions',frame_module.state_frame(updated,state),prompt_renderer=render)
    value._presentation('episode','REASONING','Original instructions',{'version':'decision_context_v1',
        'kind':'decision_lookup_result','result':{'actual':'lookup'}},prompt_renderer=render)
    assert [row[0]['current_credit'] for row in seen]==[0,2.5,2.5]
    assert seen[-1][1]==[{'actual':'lookup'}]
    assert value.scientific_prompt_states[('episode','REASONING')]==updated


def test_native_call_records_the_declared_wire_presentation(provider,tmp_path):
    value=connection(provider);value.directory=tmp_path;value.call_index=0
    value.roles={'REASONING':SimpleNamespace(model='controlled-model',reasoning_effort='controlled')}
    value.image_resolver=None;sent=[]
    async def session(*args):return 'original-thread'
    async def rpc(method,body):sent.append((method,deepcopy(body)));return {'turn':{'id':'original-turn'}}
    async def collect(*args):return '{"result":"controlled"}'
    value._session=session;value._rpc=rpc;value._collect_turn=collect
    def render(state,instructions,*,lookup_results=()):return 'Private renderer: '+state['actual']
    response=asyncio.run(value.complete('episode','REASONING','Original instructions',{'actual':'received value'},
        {'type':'object'},prompt_renderer=render))
    assert response=={'result':'controlled'}
    assert sent[0][1]['input']==[{'type':'text','text':'Private renderer: received value'}]
    saved=json.loads((tmp_path/'call-00001/request.json').read_text())
    assert saved['context']=={'actual':'received value'} and saved['instructions']=='Original instructions'
    assert saved['input']==sent[0][1]['input']
    assert saved['presentation']['qualname']==render.__qualname__


def test_model_connection_forwards_only_opted_in_presentation(provider,tmp_path):
    value=object.__new__(provider.ModelConnection)
    value.worker_lock=asyncio.Lock();value.workers={};value.session_index=0;value.maximum_active_workers=0
    value.config={};value.directory=tmp_path;value.cwd=tmp_path;value.image_resolver=None
    calls=[]
    class Worker:
        def __init__(self,*args,**kwargs):pass
        async def __aenter__(self):return self
        async def complete(self,*args,**kwargs):calls.append((args,kwargs));return {'ok':True}
    async def release(episode):
        for key in list(value.workers):
            if key[0]==episode:value.workers.pop(key)
    value.session_type=Worker;value.release=release
    def render(*args,**kwargs):return 'declared'
    assert asyncio.run(value.complete('ordinary','REASONING','instructions',{},{}))=={'ok':True}
    assert calls[-1][1]=={}
    assert asyncio.run(value.complete_with_presentation('monitor','REASONING','instructions',{}, {},prompt_renderer=render))=={'ok':True}
    assert calls[-1][1]=={'prompt_renderer':render}
    assert not value.workers
