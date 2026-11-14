"""Selected waits retain original failure, credit and replay semantics.

Tests actual private Task.execute, including Monitor's newly private wait helper.
No clock, native worker or external event provider is run.
"""
from __future__ import annotations
import importlib
from types import SimpleNamespace
import pytest
ROOT='gene_annotation_episode.episodic_workflow.root'
helpers=importlib.import_module(ROOT+'.execution_monitoring.tests.test_private_returned_action_admission')


class WaitPorts(helpers.WorkflowPorts):
    def __init__(self,scenario):super().__init__('completed',False);self.scenario=scenario
    async def perform_selected_wait(self,source,condition,index):
        self.events.append(('wait',source.episode_id,condition,index))
        if self.scenario=='target_error':
            raise importlib.import_module(ROOT+'.method_loop.durable').EventTargetError(
                'wait_target_not_visible',affected_refs=['execution:original'])
        return {'status':'failed' if self.scenario=='returned_failure' else 'completed',
                'record_refs':[],'changed_record_refs':[],
                'feedback':{'code':'controlled_wait_result'}}
    def last_observed_credit(self,source):
        self.events.append(('last_credit',source.episode_id));return 2.5


def run(method,cls,home,role,scenario):
    workflow=WaitPorts(scenario);source=object.__new__(cls) if cls else SimpleNamespace()
    source.workflow=workflow;source.episode_id='episode:original'
    source.path=(('annotation','root'),(role,home));source.scope={}
    source.feedback=None;source.last_outcome=None;source.last_outcome_index=None
    source.checkpoint=lambda:workflow.events.append(('checkpoint',source.episode_id))
    selected={'kind':'wait','condition':{'version':'event_condition_v1',
        'events':[{'handle':'execution:original','event':'returned','after_cursor':0}],'reconsider_at':None}}
    first=helpers.call(method,source,selected)
    replay=helpers.call(method,source,selected)
    return first,replay,workflow.events,workflow.journal.records,source.last_outcome


@pytest.mark.parametrize('home,name,role',helpers.CASES)
@pytest.mark.parametrize('scenario',('completed','returned_failure','target_error'))
def test_original_selected_wait_receipt_credit_and_replay(home,name,role,scenario):
    original=helpers.original_execute()
    original.__globals__.update(EventTargetError=importlib.import_module(ROOT+'.method_loop.durable').EventTargetError,
        _wait_target_feedback=importlib.import_module(ROOT+'.waiting')._wait_target_feedback)
    cls=getattr(importlib.import_module(ROOT+'.'+home.replace('/','.')+'.task'),name)
    expected=run(original,None,home,role,scenario);actual=run(cls.execute,cls,home,role,scenario)
    assert actual==expected and actual[0]==actual[1]
    kinds=[row[0] for row in actual[2]]
    assert kinds.count('wait')==1 and 'execute' not in kinds
    assert 'credit' not in kinds and 'score_boundary' not in kinds
    if scenario=='completed':
        assert actual[0][0]=='returned' and actual[0][1]['credit']==2.5
        assert kinds.count('receive')==kinds.count('last_credit')==1
    else:
        assert actual[0][1] is importlib.import_module(ROOT+'.task_action_units').ActionFailure
        assert 'receive' not in kinds and 'last_credit' not in kinds
        assert actual[4]['status']=='failed'
    if scenario=='target_error':
        assert actual[4]['feedback']=={'status':'failed','category':'wait_target',
            'code':'wait_target_not_visible','affected_refs':['execution:original'],'detail':'wait_target_not_visible'}
