"""Private A108 selected work and replay using real local journals.

Provider decisions/acquisition and credit projection are controlled ports. These
checks do not establish autonomous science or biological support.
"""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace

import pytest
from .test_private_literature_boundaries import AXIS, HOMES

@pytest.fixture(params=HOMES)
def private(request):
    module=import_module(f'{AXIS}.{request.param}.episode')
    return module.LiteratureEpisode(SimpleNamespace())

@pytest.mark.parametrize('status',['completed','partial','invalid','failed','unavailable'])
def test_actual_returned_outcome_is_observed_and_replayed_once(private,tmp_path,status):
    runtime=import_module(AXIS+'.runtime')
    Store=import_module(AXIS+'.state').Store
    Journal=import_module(AXIS+'.episode_journal').Journal
    task_type=getattr(private,'decision_source_type',runtime.DecisionSource)
    task=object.__new__(task_type)
    task.episode_id='episode-original';task.path=(('annotation','root'),(private.roles[0],'source'))
    task.scope={};task.last_outcome=task.last_outcome_index=task.feedback=None
    task.checkpoint=lambda: None
    selected={'kind':'tool','tool':'source.read','arguments':{'source_ref':'original-source'}}
    executions=[];receipts=[];grades=[];projections=[]
    result={'status':status,'record_refs':[],'changed_record_refs':[], 'result':None}
    async def execute(source,tool,args,**kwargs):
        executions.append((tool,args,kwargs['operation_key']))
        return deepcopy(result)
    async def score(source,index,outcome):
        grades.append((index,outcome['status']))
        return outcome
    def credit(source):
        projections.append((task.last_outcome_index,task.last_outcome['status']))
        return {'credit':0.0}
    with Store(tmp_path/'state') as store:
        journal=Journal(store,'private-a108')
        task.workflow=SimpleNamespace(run_id='private-a108',journal=journal,
            execution_binding=None,pending_work=lambda source:{'items':[]},
            execute=execute,receive_native_outcome=lambda *args: None,
            receive_outcome=lambda source,selection,outcome,index: receipts.append((index,outcome['status'])),
            automatic_score_updates=score,source_credit_view=credit,
            controller_value=lambda source,index,value:{'credit':value,'index':index})
        assert asyncio.run(task.execute(selected,7))=={'credit':0.0,'index':7}
        assert asyncio.run(task.execute(selected,7))=={'credit':0.0,'index':7}
        assert executions==[('source.read',{'source_ref':'original-source'},'private-a108:episode-original:7')]
        assert receipts==[(7,status)] and grades==[(7,status)] and projections==[(7,status)]
        saved=journal.row('runtime_actions','episode-original',7)
        assert json.loads(saved['action'])==selected
        assert json.loads(saved['result'])=={**result,'pending_work_after_action':{'items':[]}}
        assert saved['credit']==0.0
        assert runtime.observes_action_outcome('tool',status)


