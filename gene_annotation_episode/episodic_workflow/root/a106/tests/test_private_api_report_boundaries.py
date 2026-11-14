"""Characterize original report boundaries; controlled reads are not saved scientific proof."""
from types import SimpleNamespace
import pytest
from ..api_service_execution import APIServiceExecution
from ..bvbrc_appservice_host import BVBRCAppServiceHost, SUPPORT_SOURCE
from ..bvbrc_appservice_publication import AppServicePublications
from ..execution_contracts import digest
from ..episode_bindings import BindingContext
from .private_analysis_exchange_fixtures import analysis_workflow,module


def runtime_path(registry,home):
    parts=home.split('/');result=[('annotation','original-annotation')]
    for index in range(len(parts)):
        owner=registry.for_binding_path('/'.join(parts[:index+1]))
        result.append((owner.roles[0],'original-invocation-'+str(index)))
    return tuple(result)


@pytest.mark.parametrize('family',['root','scientific'])
@pytest.mark.parametrize('role',['launch_api','results'])
def test_actual_same_role_registry_identity_is_stricter_than_host_context_kind(analysis_workflow,family,role):
    store,workflow,_=analysis_workflow;registry=workflow.episode_bindings
    prefix='' if family=='root' else 'scientific_process/'
    suffix='execution_job_submission/api_job_execution' if role=='launch_api' else 'execution_result_acquisition'
    left=registry.for_binding_path(prefix+suffix)
    right=registry.for_binding_path(prefix+'published_evidence_assessment/'+suffix)
    assert left is not right and left.roles==right.roles==(role,)
    path=runtime_path(registry,right.binding_path)
    assert registry.for_path(path) is right and registry.for_path(runtime_path(registry,left.binding_path)) is left
    assignment={'service':'bvbrc_appservice'} if role=='launch_api' else {'selector':{'version':'bvbrc_appservice_result_selector_v1'}}
    context=BindingContext(workflow.run_id,'controlled-context-identity',role,path,{},assignment,{})
    # Existing owns_context classifies the protocol, not this private object's identity.
    assert left.api_execution.appservice.owns_context(context) is True
    assert right.api_execution.appservice.owns_context(context) is True
    assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==0


@pytest.mark.parametrize('home',['execution_job_submission.api_job_execution','execution_result_acquisition'])
@pytest.mark.parametrize('services_kind',['none','custom'])
def test_actual_private_constructor_does_not_require_workflow_registry(analysis_workflow,home,services_kind):
    store,workflow,configuration=analysis_workflow;reader=lambda *args,**kwargs:None
    services=None if services_kind=='none' else SimpleNamespace(read_received_molecular_input=reader)
    owner=module(home+'.episode').ExecutionEpisode(services,**configuration)
    assert owner.services is services
    assert owner.api_execution.received_input_reader is (None if services is None else reader)
    assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==0
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]==0


def publications(adapter,outcomes):
    value=AppServicePublications.__new__(AppServicePublications);calls=[]
    def authenticate(context,**kwargs):calls.append(('authenticate',context,kwargs))
    value.host=SimpleNamespace(custody=SimpleNamespace(authenticate=authenticate))
    value.api=SimpleNamespace(_own_outcomes=lambda context:iter(outcomes))
    context=SimpleNamespace(role='results',episode_id='original',scope={'actual':'scope'},assignment={'selector':{'adapter':adapter}})
    return value,context,calls


@pytest.mark.parametrize('adapter_id',['bvbrc_tnseq','bvbrc_rnaseq'])
def test_selected_latest_publication_without_result_refs_blocks_older_success(adapter_id):
    rows=[(None,{'result':{'publication_ref':'old','result_record_refs':['old-result']}}),
        (None,{'result':{'publication_ref':'new','result_record_refs':[]}})]
    value,context,calls=publications({'adapter_id':adapter_id,'adapter_version':'1'},rows)
    def forbidden(*args,**kwargs):raise AssertionError('older successful publication must not replace newest empty result')
    value.read=forbidden;value.own_results=forbidden
    assert value.completion(context) is None
    assert calls==[('authenticate',context,{'allow_unsaved':True})]


@pytest.mark.parametrize('adapter_id',['bvbrc_tnseq','bvbrc_rnaseq'])
@pytest.mark.parametrize('has_proof',[False,True])
def test_selected_publication_keeps_last_reference_exact_proof_or_none(adapter_id,has_proof):
    rows=[(None,{'result':{'publication_ref':'selected','result_record_refs':['first','last']}}),
        (None,{'result':{'unrelated':'outcome'}})]
    value,context,calls=publications({'adapter_id':adapter_id,'adapter_version':'1'},rows)
    proof={'original':'proof'} if has_proof else None
    def read(reference,scope,**kwargs):calls.append(('read',reference,scope,kwargs));return {'publication':{'completion_proof':proof}}
    value.read=read
    assert value.completion(context) is proof
    assert calls==[('authenticate',context,{'allow_unsaved':True}),('read','last',context.scope,{'episode_id':context.episode_id})]


def test_generic_completion_preserves_reverse_nonempty_proof_selection():
    value,context,calls=publications(None,[]);proof={'original':'generic proof'}
    value.own_results=lambda c:['old','usable','latest-empty']
    def read(reference,scope,**kwargs):calls.append(reference);return {'publication':{'completion_proof':proof if reference=='usable' else None}}
    value.read=read
    assert value.completion(context) is proof and calls==['latest-empty','usable']


@pytest.mark.parametrize('role',['annotation','launch','monitor'])
def test_raw_host_unknown_completion_roles_and_publication_refs_remain_empty(role):
    host=BVBRCAppServiceHost.__new__(BVBRCAppServiceHost)
    value=AppServicePublications.__new__(AppServicePublications);context=SimpleNamespace(role=role)
    assert host.completion(context) is None and value.own_results(context)==[]


@pytest.mark.parametrize('conflict',[False,True])
def test_host_facts_preserve_actual_source_merge_conflict(conflict):
    host=BVBRCAppServiceHost.__new__(BVBRCAppServiceHost);calls=[]
    host._own_receipts=lambda c:[{'source_ref':'h','contract':'TaskHandoff'},{'source_ref':'s','contract':'CommonReceipt'}]
    host.publications=SimpleNamespace(own_results=lambda c:['r']);host.completion=lambda c:None
    supplied={'execution_completed':True} if conflict else {'original_descriptive_context':['actual-context']}
    def facts(context,schema):calls.append((context,schema));return supplied
    host.api=SimpleNamespace(application_returns=SimpleNamespace(facts=facts))
    schema={'properties':{'actual':'schema'}};context=SimpleNamespace(request={'report_contract':{'measurements':{'schema':schema}}})
    if conflict:
        with pytest.raises(ValueError,match='appservice_own_fact_source_conflict'):host.facts(context)
    else:assert host.facts(context)=={'execution_handoff_refs':['h'],SUPPORT_SOURCE:['s'],'execution_result_refs':['r'],'execution_completed':False,**supplied}
    assert calls==[(context,schema)]


def test_original_handoff_completion_retains_actual_operation_and_receipt_digest():
    host=BVBRCAppServiceHost.__new__(BVBRCAppServiceHost);host.run_id='run';calls=[]
    common={'origin':{'operation_key':'original-action'},'actual':'receipt'}
    host._own_receipts=lambda c:[{'contract':'TaskHandoff','source_ref':'handoff','value':{'receipt':common}}, {'contract':'CommonReceipt','source_ref':'later-support'}]
    host.read_handoff=lambda reference,scope:calls.append((reference,scope))
    context=SimpleNamespace(role='launch_api',episode_id='episode',assignment={'actual':'assignment'},scope={'actual':'scope'})
    assert host.completion(context)=={'version':'practical_completion_v1','run_id':'run','episode_id':'episode',
        'assignment_sha256':digest(context.assignment),'endpoint':'usable_handoff','operation_key':'original-action',
        'receipt_sha256':digest(common),'validation_keys':['usable_handoff']}
    assert calls==[('handoff',context.scope)]


def test_actual_raw_api_constructor_preserves_completion_without_registry(analysis_workflow):
    store,workflow,c=analysis_workflow
    api=APIServiceExecution(store,run_id=workflow.run_id,directory=workflow.directory,
        configuration=c['resources'],tool_registry=workflow.tools,handoff_unit=2,acquired_record_unit=3)
    context=SimpleNamespace(role='monitor')
    assert api._completion(context) is None and api.completion_for_action(context,'unselected') is None
    assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==0
