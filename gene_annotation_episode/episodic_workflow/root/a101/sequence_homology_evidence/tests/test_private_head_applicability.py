"""Actual fresh head actions and preserved historical/vector state are distinct."""
from contextlib import nullcontext
from types import SimpleNamespace
import json
import pytest
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.tests.test_scientific_task import Binding,make_task,runtime


def test_actual_head_schema_admits_reason_wait_and_original_children_not_job_children():
    binding=Binding(SimpleNamespace(),library=SimpleNamespace(as_record=lambda:{'version':'fixture'},headers=lambda:[]),
        tool_library=SimpleNamespace(as_record=lambda:{'version':'fixture'}),child_roles=('sequence_homology_evidence','literature'))
    binding.validate_context=lambda context:None
    context=SimpleNamespace(role='sequence_homology_evidence',scope={})
    source=SimpleNamespace(path=(('sequence_homology_evidence','original'),),scope={},interpret_schema={'type':'object','properties':{}})
    workflow=SimpleNamespace(specialist=lambda source:binding,binding_context=lambda source:context,
        permits_common_action=lambda source,kind:kind in binding.permitted_common_actions(context),
        is_job_source=lambda source:False,reasoning_action_schema=lambda source:{'type':'object','properties':{'kind':{'const':'reason'}}},
        catalog=lambda *args,**kwargs:[],annotation_child_roles=None,project_credit=SimpleNamespace(),
        sequence_homology_evidence_binding=binding,job_episodes=SimpleNamespace(commission_schemas=lambda schema:pytest.fail('head cannot acquire a legacy job_child')),
        episode_bindings=SimpleNamespace(for_child=lambda *args:SimpleNamespace(assignment_schema=lambda role:{'type':'object'})),
        services=SimpleNamespace(capabilities=lambda:()),root_child_return_sources=lambda *args:())
    branches=runtime.Workflow.action_schema(workflow,source)['properties']['selection']['anyOf']
    assert {branch['properties']['kind']['const'] for branch in branches}=={'reason','wait','episode_child','redeliver_report'}
    assert {branch['properties']['role']['const'] for branch in branches if 'role' in branch['properties']}=={'sequence_homology_evidence','literature'}


def head_state(vector=False):
    task,_,_,_=make_task({})
    task.last_outcome={'status':'failed','record_refs':['old-ref'],'changed_record_refs':[]} if vector else None
    task.last_outcome_index=3 if vector else None
    task.feedback={'actual':'historical failure'} if vector else None
    task.report_values={};task.report_basis=[];task.interpret_schema={'type':'object','properties':{}}
    task.request=SimpleNamespace(goal=SimpleNamespace(as_record=lambda:{'objective':'Original head question'}),report_contract=None)
    wf=task.workflow
    wf.store=SimpleNamespace(read_snapshot=nullcontext,get=lambda ref:pytest.fail('No scientific record is requested by this state fixture'))
    wf.journal.db=SimpleNamespace(execute=lambda *args:SimpleNamespace(fetchone=lambda:None))
    wf.journal.elapsed_view=lambda *args:{}
    wf.journal.row=lambda *args:{'action':json.dumps({'kind':'job_child','role':'legacy-job'})}
    wf.working_state=lambda source:{}
    wf.local_outcome_preview=lambda outcome,**kwargs:outcome
    wf.source_credit_view=lambda source:({'credit':{'mode':'annotation_axis_credit'},'proposed_annotations':[],'comparisons':[]} if vector else {'credit':2.5})
    wf.receipt_projection=lambda source:False
    wf.source_credit_binding=lambda source:{'original':'binding'}
    wf.pending_work=lambda source:[]
    wf.delivery_status=lambda episode:[]
    wf.controller_binding={'original':'controller'}
    wf.catalog=lambda *args,**kwargs:[]
    wf.knowledge=SimpleNamespace(context=lambda:{})
    wf.job_episode_options=lambda source:{'legacy_job':{'not_in_current_schema':True}}
    wf.extra_report_sources=lambda source:{}
    wf.is_scientific_source=lambda source:True
    wf.annotation_context=lambda *args,**kwargs:{}
    wf.specialist=lambda source:SimpleNamespace(decision_context=lambda *args:{})
    wf.tools=SimpleNamespace()
    controller={'arms':[],'annotation_credits':[],'root_score':2.5,'decision':'continue','private_extra':'omit'} if vector else {'original':'scalar'}
    view=SimpleNamespace(child_reports=(),controller_state=controller,model_inputs=lambda value,**kwargs:value)
    return task.decision_state(view)

