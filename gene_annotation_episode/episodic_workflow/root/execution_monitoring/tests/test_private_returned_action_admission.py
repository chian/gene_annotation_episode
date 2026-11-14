"""Actual private Task.execute/MRO versus pinned original returned-action boundary.

Construction is controlled: this exercises the selected method, journal ordering,
provider return, receiver and iterator input. It does not assemble a full Workflow
or substitute for scientific grading, restoration or autonomous execution.
"""
from __future__ import annotations
import ast
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT='gene_annotation_episode.episodic_workflow.root'
MONITOR_HOMES=tuple(prefix+home for prefix in ('','legacy_annotation/','scientific_process/')
    for home in ('execution_monitoring','hpc_coordination/execution_monitoring',
                 'hpc_coordination/hpc_allocation_execution/execution_monitoring'))
HOMOLOGY=(('homology_job_submission','HomologySubmissionTask','job_launch'),
         ('homology_job_monitoring','HomologyMonitoringTask','job_monitor'),
         ('homology_result_acquisition','HomologyAcquisitionTask','job_results'))
CASES=tuple((home,'MonitorTask','monitor') for home in MONITOR_HOMES)+tuple(
    (prefix+home,('Legacy' if prefix else '')+name,role)
    for prefix in ('','legacy_annotation/') for home,name,role in HOMOLOGY)
ORIGINAL_SHA='a97428c084fa75d1eb1ae0a097e06d63d11e63d7f433a0a605530569c0351082'


def original_execute():
    path=Path(__file__).with_name('fixtures')/'original_boundary/runtime.py.source'
    raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()==ORIGINAL_SHA
    cls=next(node for node in ast.parse(raw).body if isinstance(node,ast.ClassDef) and node.name=='DecisionSource')
    method=next(node for node in cls.body if isinstance(node,ast.AsyncFunctionDef) and node.name=='execute')
    namespace=dict(globals(),__name__=ROOT+'.tests._original_returned_action_boundary',
        WorkflowError=importlib.import_module(ROOT+'.episode_journal').WorkflowError,
        ActionFailure=importlib.import_module(ROOT+'.task_action_units').ActionFailure,
        observes_action_outcome=importlib.import_module(ROOT+'.episode_completion').observes_action_outcome,
        _json=importlib.import_module(ROOT+'.task_values')._json)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),str(path),'exec'),namespace)
    return namespace['execute']


class Journal:
    def __init__(self,events): self.records={}; self.events=events
    def row(self,table,episode,index): return deepcopy(self.records.get((table,episode,index)))
    def save(self,table,row):
        self.events.append(('save',table,deepcopy(row)))
        self.records[(table,row['episode_id'],row['decision_index'])]=deepcopy(row)
    def measure(self,*args): self.events.append(('measure',args)); return nullcontext()


class WorkflowPorts:
    run_id='run:controlled'
    execution_binding=None
    wait_inputs_version='wait_inputs_binding_v1'
    completed_action_inputs_version=None
    def __init__(self,status,async_dispatch):
        self.events=[]; self.journal=Journal(self.events); self.async_dispatch=async_dispatch
        self.outcome={'status':status,'record_refs':[],'changed_record_refs':[],
                      'feedback':{'code':'controlled_return_'+status}}
    def execute(self,source,tool,arguments,**kwargs):
        self.events.append(('execute',source.episode_id,tool,deepcopy(arguments),kwargs))
        value=deepcopy(self.outcome)
        if self.async_dispatch:
            async def returned(): return value
            return returned()
        return value
    def receive_native_outcome(self,source,result,index):
        self.events.append(('native',source.episode_id,index,deepcopy(result)))
    def receive_outcome(self,source,selection,result,index):
        self.events.append(('receive',source.episode_id,index,deepcopy(selection),deepcopy(result)))
    async def automatic_score_updates(self,source,index,result):
        # This controlled port records original sequencing, not a scientific score.
        self.events.append(('score_boundary',source.episode_id,index)); return result
    def source_credit_view(self,source):
        self.events.append(('credit',source.episode_id)); return {'credit':2.5}
    def controller_value(self,source,index,credit):
        self.events.append(('controller',source.episode_id,index,credit))
        return {'episode_id':source.episode_id,'decision_index':index,'credit':credit}


def call(method,source,selection,index=7):
    try: return ('returned',asyncio.run(method(source,selection,index)))
    except Exception as error:
        return ('raised',type(error),str(error),getattr(error,'feedback',None))


def run(method,task_class,home,role,status,async_dispatch):
    workflow=WorkflowPorts(status,async_dispatch)
    # Instantiate the actual selected class without running unrelated full-store
    # constructor plumbing. execute is selected from that class's real MRO.
    source=object.__new__(task_class) if task_class else SimpleNamespace()
    source.workflow=workflow; source.episode_id='episode:controlled'
    source.path=(('annotation','root'),(role,home)); source.scope={'subject_refs':[]}
    source.feedback=None; source.last_outcome=None; source.last_outcome_index=None
    source.checkpoint=lambda:workflow.events.append(('checkpoint',source.episode_id))
    selected={'kind':'tool','tool':'controlled.observation','arguments':{'original':'identity'}}
    first=call(method,source,selected)
    replay=call(method,source,deepcopy(selected))
    changed=call(method,source,{**selected,'arguments':{'original':'changed'}})
    return (first,replay,changed,workflow.events,workflow.journal.records,
            source.last_outcome,source.last_outcome_index,source.feedback)


@pytest.mark.parametrize('home,name,role',CASES)
@pytest.mark.parametrize('status',('completed','partial','invalid','failed','unavailable','pending'))
@pytest.mark.parametrize('async_dispatch',(False,True))
def test_original_returned_action_admission_credit_and_replay(home,name,role,status,async_dispatch):
    cls=getattr(importlib.import_module(ROOT+'.'+home.replace('/','.')+'.task'),name)
    actual=cls.execute
    owner=next(base for base in cls.__mro__ if 'execute' in vars(base))
    assert owner.__module__.startswith(ROOT+'.'+home.replace('/','.')+'.')
    expected=run(original_execute(),None,home,role,status,async_dispatch)
    observed=run(actual,cls,home,role,status,async_dispatch)
    assert observed==expected
    events=observed[3]
    assert len([row for row in events if row[0]=='execute'])==1
    assert observed[0]==observed[1]
    assert observed[2][0]=='raised'
    assert observed[2][1] is importlib.import_module(ROOT+'.episode_journal').WorkflowError
    if status=='pending':
        assert observed[0][0]=='raised'
        assert observed[0][1] is importlib.import_module(ROOT+'.task_action_units').ActionFailure
        assert not any(row[0] in ('receive','credit','controller') for row in events)
    else:
        assert observed[0][1]['credit']==2.5
        kinds=[row[0] for row in events]
        assert kinds.count('receive')==kinds.count('credit')==kinds.count('score_boundary')==1
        assert kinds.index('receive')<kinds.index('score_boundary')<kinds.index('credit')<kinds.index('controller')
    assert observed[5]['status']==status and observed[6]==7
