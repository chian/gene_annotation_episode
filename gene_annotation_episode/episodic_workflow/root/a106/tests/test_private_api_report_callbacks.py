"""Execute selected private report/endpoint callbacks through original public methods.

Readers are explicit controlled ports; constructed bindings/registry/Store are real.
These controls do not manufacture historical records or scientific observations.
"""
import asyncio
from types import SimpleNamespace
import pytest
from ..api_service_execution import APIServiceExecution
from ..bvbrc_appservice_host import BVBRCAppServiceHost,SUPPORT_SOURCE
from ..bvbrc_appservice_publication import AppServicePublications
from ..execution_contracts import digest
from ..domain import identity
from ..episode_bindings import BindingContext
from .private_analysis_exchange_fixtures import analysis_workflow
from .test_private_api_report_boundaries import runtime_path,publications
PARENTS=('','published_evidence_assessment/','perturbation_evidence/','perturbation_evidence/published_evidence_assessment/')
APIS=tuple(p+'execution_job_submission/api_job_execution' for p in PARENTS)
RESULTS=tuple(p+'execution_result_acquisition' for p in PARENTS)
HOMES=tuple(h for pair in zip(APIS,RESULTS) for h in pair)


def selected(analysis_workflow,home):
    _,workflow,_=analysis_workflow
    return workflow.episode_bindings.for_binding_path(home)


@pytest.mark.parametrize('home',HOMES)
def test_actual_private_facts_callback_retains_same_role_sibling_context(analysis_workflow,home):
    _,workflow,_=analysis_workflow;owner=selected(analysis_workflow,home)
    callback=owner.api_execution.appservice._facts_projector
    assert callback.__self__ is owner and callback.__func__ is type(owner)._appservice_report_facts
    sibling=next(b for b in workflow.episode_bindings._bindings if b is not owner and b.roles==owner.roles)
    path=runtime_path(workflow.episode_bindings,sibling.binding_path)
    context=BindingContext(workflow.run_id,'controlled-original',owner.roles[0],path,{}, {}, {'report_contract':{'measurements':{'schema':{'actual':'schema'}}}})
    assert workflow.episode_bindings.for_path(context.path) is sibling
    host=BVBRCAppServiceHost.__new__(BVBRCAppServiceHost);host._facts_projector=callback;calls=[]
    def receipts(c):calls.append(('receipts',c));return [{'source_ref':'handoff','contract':'TaskHandoff'}]
    def results(c):calls.append(('results',c));return ['result']
    def complete(c):calls.append(('completion',c));return None
    def facts(c,s):calls.append(('application_facts',c,s));return {'original_context':['actual']}
    host._own_receipts=receipts;host.publications=SimpleNamespace(own_results=results);host.completion=complete
    host.api=SimpleNamespace(application_returns=SimpleNamespace(facts=facts))
    assert host.facts(context)=={'execution_handoff_refs':['handoff'],SUPPORT_SOURCE:[], 'execution_result_refs':['result'],'execution_completed':False,'original_context':['actual']}
    assert calls==[('receipts',context),('results',context),('completion',context),('application_facts',context,{'actual':'schema'})]


@pytest.mark.parametrize('home',HOMES)
def test_actual_private_endpoint_keeps_unknown_raw_context_none(analysis_workflow,home):
    owner=selected(analysis_workflow,home);host=BVBRCAppServiceHost.__new__(BVBRCAppServiceHost)
    host._completion_projector=owner.api_execution.appservice._completion_projector
    assert host._completion_projector.__self__ is owner and host._completion_projector.__func__ is type(owner)._appservice_completion
    assert host.completion(SimpleNamespace(role='monitor')) is None


def handoff_host(owner,context):
    host=BVBRCAppServiceHost.__new__(BVBRCAppServiceHost);host._completion_projector=owner.api_execution.appservice._completion_projector
    host.run_id=context.run_id;calls=[];common={'origin':{'operation_key':'original-action'},'actual':'receipt'}
    host._own_receipts=lambda c:[{'contract':'TaskHandoff','source_ref':'handoff','value':{'receipt':common}}]
    host.read_handoff=lambda reference,scope:calls.append((reference,scope))
    expected={'version':'practical_completion_v1','run_id':context.run_id,'episode_id':context.episode_id,'assignment_sha256':digest(context.assignment),
        'endpoint':'usable_handoff','operation_key':'original-action','receipt_sha256':digest(common),'validation_keys':['usable_handoff']}
    return host,calls,expected


@pytest.mark.parametrize('home',APIS)
def test_actual_private_handoff_body_executes_original_source_identity(analysis_workflow,home):
    owner=selected(analysis_workflow,home);context=SimpleNamespace(run_id=owner.run_id,role='launch_api',episode_id='actual-context',assignment={'original':'assignment'},scope={'actual':'scope'})
    host,calls,expected=handoff_host(owner,context)
    assert host.completion(context)==expected and calls==[('handoff',context.scope)]


@pytest.mark.parametrize('home',RESULTS)
@pytest.mark.parametrize('adapter_id',['bvbrc_tnseq','bvbrc_rnaseq'])
def test_actual_private_publication_body_preserves_latest_empty_refs(analysis_workflow,home,adapter_id):
    owner=selected(analysis_workflow,home)
    rows=[(None,{'result':{'publication_ref':'older','result_record_refs':['older-result']}}),(None,{'result':{'publication_ref':'newer','result_record_refs':[]}})]
    value,context,calls=publications({'adapter_id':adapter_id,'adapter_version':'1'},rows)
    value._completion_projector=owner.api_execution.appservice.publications._completion_projector
    assert value._completion_projector.__self__ is owner and value._completion_projector.__func__ is type(owner)._appservice_publication_completion
    def forbidden(*args,**kwargs):raise AssertionError('newest empty result cannot claim older success')
    value.read=forbidden;value.own_results=forbidden
    assert value.completion(context) is None and calls==[('authenticate',context,{'allow_unsaved':True})]


@pytest.mark.parametrize('home',RESULTS)
def test_actual_private_results_endpoint_preserves_publication_override(analysis_workflow,home):
    owner=selected(analysis_workflow,home);host=BVBRCAppServiceHost.__new__(BVBRCAppServiceHost)
    host._completion_projector=owner.api_execution.appservice._completion_projector
    context=SimpleNamespace(role='results');proof={'controlled':'original override'};calls=[]
    def custom(c):calls.append(c);return proof
    host.publications=SimpleNamespace(completion=custom)
    assert host.completion(context) is proof and calls==[context]


def api_arguments(analysis_workflow):
    store,workflow,c=analysis_workflow
    return dict(store=store,run_id=workflow.run_id,directory=workflow.directory,
        configuration=c['resources'],tool_registry=workflow.tools,handoff_unit=2,acquired_record_unit=3)


@pytest.mark.parametrize('port',['report_facts','completion_projector','publication_completion'])
def test_actual_raw_constructor_rejects_only_noncallable_new_port(analysis_workflow,port):
    with pytest.raises(ValueError,match='api_'+port+'_must_be_callable'):
        APIServiceExecution(**api_arguments(analysis_workflow),**{port:object()})


@pytest.mark.parametrize('port',['report_facts','completion_projector','publication_completion'])
@pytest.mark.parametrize('disposition',['return','raise'])
def test_actual_raw_custom_port_retains_exact_receiver_context_and_error(analysis_workflow,port,disposition):
    result={'actual':'callback result'};error=ValueError('original callback error');calls=[]
    def callback(receiver,context):
        calls.append((receiver,context))
        if disposition=='raise':raise error
        return result
    api=APIServiceExecution(**api_arguments(analysis_workflow),**{port:callback});context=object()
    receiver=api.appservice.publications if port=='publication_completion' else api.appservice
    read=receiver.facts if port=='report_facts' else receiver.completion
    if disposition=='raise':
        with pytest.raises(ValueError) as caught:read(context)
        assert caught.value is error
    else:assert read(context) is result
    assert calls==[(receiver,context)]


@pytest.mark.parametrize('home',HOMES)
def test_selected_operation_preserves_original_invalid_preflight_action(analysis_workflow,home,tmp_path):
    owner=selected(analysis_workflow,home)
    context=SimpleNamespace(run_id=owner.run_id,episode_id='original-episode',role=owner.roles[0],assignment={'original':'assignment'},scope={})
    host,calls,proof=handoff_host(owner,context)
    if context.role=='results':host.publications=SimpleNamespace(completion=lambda c:proof)
    def forbidden(*args,**kwargs):raise AssertionError('completed assignment must reject before binding inputs or invoking service')
    host.bind_inputs=forbidden
    key='original-selected-action'
    outcome=asyncio.run(host.execute_locked(context,context.assignment,SimpleNamespace(prepare=forbidden),None,
        'api.bvbrc_appservice.start',{},key,tmp_path))
    assert outcome=={'status':'invalid','operation_ref':identity('api_operation',{'key':key}),
        'record_refs':[],'changed_record_refs':[],'result':None,'feedback':{'category':'provider','code':'api_assignment_already_completed'}}
    assert list(tmp_path.iterdir())==[]
