"""Exact own-axis scientific snapshot/selection preservation with controlled inputs.

Actual declared ScientificTask.next runs; model acquisition is stopped after
capturing its inputs. Constructor/scientific services are controlled, so this
claims the decision presentation boundary, not autonomous scientific validation.
"""
from __future__ import annotations
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
PREFIX='gene_annotation_episode.episodic_workflow.root.a110'
runtime=importlib.import_module(PREFIX+'.runtime')
episode=importlib.import_module(PREFIX+'.scientific_process.episode')
FIXTURE=json.loads((Path(__file__).parent/'fixtures/organization_original/scientific_task_summary.json').read_text())
def original(name):
    namespace=dict(vars(runtime));exec(compile(FIXTURE[name+'_function'],'<original-own-axis-scientific-task>','exec'),namespace)
    return namespace['_decision_snapshot' if name=='snapshot' else 'next']
class SnapshotCaptured(Exception):
    def __init__(self,context,schema):self.context,self.schema=deepcopy(context),deepcopy(schema)
class Journal:
    def __init__(self,events):
        self.events=events;self.actions={};self.model=None;self.closed=None
        self.db=SimpleNamespace(execute=lambda *args:SimpleNamespace(fetchone=lambda:None))
    def row(self,table,episode_id,index=None):
        if table=='runtime_actions':return self.actions.get(index)
        if table=='runtime_model_calls':return self.model
        if table=='runtime_episodes':return self.closed
        raise AssertionError(table)
    def elapsed_view(self,episode_id):return {'elapsed':0.0}
def harness(mode):
    source=object.__new__(episode.ScientificProcessEpisode.decision_source_type)
    source.path=(('annotation','root'),('scientific_process','private'))
    source.episode_id='controlled-scientific-episode';source.scope={'subject_refs':[]}
    source._delivery_resolution_ref=source._execution_context=None;source._restored=False;source.calls=0
    source.report_values,source.report_basis={},[]
    source.interpret_schema={'type':'object','properties':{},'required':[],'additionalProperties':False}
    source.request=SimpleNamespace(goal=SimpleNamespace(as_record=lambda:{'goal':'Preserve qualified scientific findings'}),report_contract=None)
    events=[];workflow=SimpleNamespace(run_id='controlled-scientific-run',journal=Journal(events),inprocess_replay=None,execution_binding=None)
    source.workflow=workflow
    source.last_outcome={'status':'failed','feedback':{'status':'failed','detail':'original failed observation'}}
    if mode=='invalid':source.last_outcome['status']=source.last_outcome['feedback']['status']='invalid'
    if mode=='unavailable':source.last_outcome['status']=source.last_outcome['feedback']['status']='unavailable'
    source.feedback=source.last_outcome['feedback'];source.last_outcome_index=3
    action='child' if mode=='annotation_child' else 'tool'
    workflow.journal.actions[3]={'action':json.dumps({'kind':action}),'result':json.dumps(source.last_outcome),'credit':0.375}
    @contextmanager
    def snapshot():
        events.append(('snapshot_enter',))
        try:yield
        finally:events.append(('snapshot_exit',))
    workflow.store=SimpleNamespace(read_snapshot=snapshot,get=lambda ref:None,reference_subset=lambda refs,scope:refs)
    def working_state(actual):events.append(('working_state',));return {'retained_qualification':'unresolved'}
    workflow.working_state=working_state;workflow.local_outcome_preview=lambda value,**kwargs:deepcopy(value)
    credit={'credit':0.375,'retained_finding_count':0,'a107_sheet':[],'a110_sheet':[],'target_sheets':[],'tool_attachments':[],'source_contributions':[]}
    if mode in ('annotation','annotation_child'):
        credit={'credit':{'mode':'annotation_axis_credit','root_score':0.375},'proposed_annotations':[],'comparisons':[],'axis_components':{}}
    workflow.source_credit_view=lambda actual:deepcopy(credit);workflow.receipt_projection=lambda actual:True
    workflow.source_credit_binding=lambda actual:{'version':'controlled_original_scientific_binding'}
    workflow.pending_work=lambda actual:{'items':[]};workflow.delivery_status=lambda ident:[]
    workflow.controller_binding={'version':'controlled_iterator_binding'};workflow.catalog=lambda scope,**kwargs:[]
    workflow.knowledge=SimpleNamespace(context=lambda:{});workflow.job_episode_options=lambda actual:None
    workflow.extra_report_sources=lambda actual:{};workflow.is_scientific_source=lambda actual:True
    workflow.annotation_context=lambda scope,**kwargs:{'retained_scientific_context':True}
    def specialist_context(context,view):events.append(('specialist_context',));return {'private_context':'original'}
    workflow.specialist=lambda actual:SimpleNamespace(decision_context=specialist_context)
    workflow.binding_context=lambda actual:SimpleNamespace(role='scientific_process')
    workflow.tools=SimpleNamespace(model_contract_catalog=lambda context:context['available_report_facts'])
    workflow.action_schema=lambda actual:{'type':'object','const':'controlled_original_schema'}
    def delivery(actual,reference,context):
        events.append(('delivery_inputs',reference));return {**context,'pending_child_delivery':{'delivery_ref':reference}},{'type':'object','const':'controlled_delivery_schema'}
    workflow.delivery_resolution_inputs=delivery
    view=SimpleNamespace(units_consumed=0,child_reports=(),controller_state={'arms':[],'annotation_credits':{},'root_score':0.375,'decision':'continue'})
    def model_inputs(context,*,reports):events.append(('model_inputs',deepcopy(context),len(reports)));return deepcopy(context)
    view.model_inputs=model_inputs
    async def call(context,schema):raise SnapshotCaptured(context,schema)
    source.call=call
    return source,view,events
@pytest.mark.parametrize('mode',('plain','annotation','annotation_child','invalid','unavailable','delivery'))
def test_actual_declared_task_uses_own_summary_and_original_inputs(mode,monkeypatch):
    delivery_ref='original-delivery' if mode=='delivery' else None
    original_source,original_view,original_events=harness(mode)
    expected=original('snapshot')(original_source,original_view,delivery_ref)
    source,view,events=harness(mode)
    summary_module=importlib.import_module(PREFIX+'.scientific_process.internal_summary')
    selected=getattr(summary_module,'ScientificDecisionSummary',None);calls=[]
    if selected is not None:
        method=selected._decision_snapshot
        def observe(actual,current_view,reference=None):
            calls.append((actual is source,current_view is view,reference));return method(actual,current_view,reference)
        monkeypatch.setattr(selected,'_decision_snapshot',observe)
    assert episode.ScientificProcessEpisode.decision_source_type is episode.ScientificTask
    with pytest.raises(SnapshotCaptured) as captured:asyncio.run(source.next(view,delivery_ref=delivery_ref))
    assert (captured.value.context,captured.value.schema)==expected
    assert events==original_events
    assert calls==[(True,True,delivery_ref)]
@pytest.mark.parametrize('with_response',(False,True))
def test_original_saved_model_context_bypasses_new_summary(with_response):
    results=[]
    for old in (True,False):
        source,view,events=harness('plain')
        request={'context':{'original_context':True},'schema':{'original_schema':True},'contract_information':{}}
        source.workflow.journal.model={'request':json.dumps(request),'response':'original response' if with_response else None}
        with pytest.raises(SnapshotCaptured) as caught:asyncio.run(original('next')(source,view) if old else source.next(view))
        assert not events
        results.append((caught.value.context,caught.value.schema))
    assert results==[({'original_context':True},{'original_schema':True})]*2

def test_original_failed_source_stops_before_decision_presentation():
    results=[]
    for old in (True,False):
        source,view,events=harness('plain')
        source.workflow.journal.closed={'state':'yielded','completion':json.dumps({'ended_by':'source_failed','actions':0})}
        result=asyncio.run(original('next')(source,view) if old else source.next(view))
        assert type(result) is runtime.SourceEnd and not events
        results.append(result)
    assert results[0]==results[1]
