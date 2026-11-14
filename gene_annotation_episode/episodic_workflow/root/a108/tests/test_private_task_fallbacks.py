"""Preserve original failure-operand fallbacks while relocating task methods.

The selected-work port exposes the original generic-runtime failure handler.
Literature private tasks exclude this unavailable job-child responsibility.
"""
from importlib import import_module
from types import SimpleNamespace

import pytest
from .test_private_literature_boundaries import AXIS,HOMES

@pytest.mark.parametrize('handoff',['missing',None,{}])
def test_original_failure_fallback_preserves_absent_or_empty_handoff(handoff):
    from gene_annotation_episode.episodic_workflow.root.a108.runtime import DecisionSource
    task=object.__new__(DecisionSource)
    task.episode_id='parent';task._delivery_resolution_ref=None
    effects=[];task.record_effect=lambda index,state:effects.append((index,state))
    def unavailable(*args):raise OSError('controlled pre-acquisition storage failure')
    task.workflow=SimpleNamespace(journal=SimpleNamespace(row=lambda *args:None),
        decision_exchanges=None,execution_binding=None,
        permits_common_action=lambda *args:False,selected=unavailable)
    selection={'kind':'job_child','role':'fixture_only'}
    if handoff!='missing':selection['handoff']=handoff
    schema={'type':'object','properties':{'selection':{'type':'object'},'report_update':{'type':'object'}}}
    assert task.apply_response({'selection':selection,'report_update':{}},5,{},schema) is None
    assert task.feedback['category']=='job_assignment' and task.feedback['job_ref'] is None
    assert task.feedback['code']=='job_operation_failed'
    assert effects==[(5,'rejected')]
