"""Live private-return boundaries with explicit engineering ports.

These do not authenticate synthetic completion records as scientific work. They
check the original call ordering, early returns, values and exception identities.
"""
import asyncio
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace
import pytest

PACKAGE='gene_annotation_episode.episodic_workflow.root.a106'
PARENTS=('', 'published_evidence_assessment/', 'perturbation_evidence/',
         'perturbation_evidence/published_evidence_assessment/')
NATIVE=[('execution_job_submission/api_job_execution','launch_api'),('execution_result_acquisition','results')]


def binding(parent,suffix):
    return object.__new__(import_module(PACKAGE+'.'+(parent+suffix).replace('/','.')+'.episode').ExecutionEpisode)


@pytest.mark.parametrize('parent',PARENTS)
def test_launch_live_capability_return_and_argument_error(parent):
    b=binding(parent,'execution_job_submission');ctx=SimpleNamespace(role='launch')
    original={'recorded_inventory':'explicit engineering fixture'}
    calls=[]
    b.initial_decision_context=lambda c:calls.append(c) or original
    outcome=asyncio.run(b.execute(ctx,'execution.capabilities',{},'original-key'))
    assert outcome['status']=='completed' and outcome['result'] is original and calls==[ctx]
    invalid=asyncio.run(b.execute(ctx,'execution.capabilities',{'unexpected':True},'original-key'))
    assert invalid['status']=='invalid' and invalid['feedback']['code']=='invalid_execution_operation_arguments'
    assert calls==[ctx]


@pytest.mark.parametrize('parent',PARENTS)
def test_api_live_await_keeps_check_order_and_uncaught_exception(parent):
    b=binding(parent,'execution_job_submission/api_job_execution');ctx=SimpleNamespace(role='launch_api')
    calls=[];answer={'status':'unavailable','record_refs':[],'changed_record_refs':[],'result':None}
    b._check_parent_inputs=lambda c:calls.append(('parent',c))
    async def execute(c,name,args,key):
        calls.append(('execute',c,name,args,key));return answer
    b.api_execution=SimpleNamespace(execute=execute)
    assert asyncio.run(b.execute(ctx,'selected.operation',{'original':True},'original-key')) is answer
    assert calls==[('parent',ctx),('execute',ctx,'selected.operation',{'original':True},'original-key')]
    error=ValueError('controlled original asynchronous failure')
    async def failed(*args):raise error
    b.api_execution.execute=failed
    with pytest.raises(ValueError) as caught:asyncio.run(b.execute(ctx,'selected.operation',{},'original-key'))
    assert caught.value is error


@pytest.mark.parametrize('parent',PARENTS)
@pytest.mark.parametrize('suffix,role',NATIVE)
def test_native_empty_children_keeps_role_guard(parent,suffix,role):
    b=binding(parent,suffix)
    assert b.allowed_children(SimpleNamespace(role=role),())==()
    with pytest.raises(ValueError,match='^unknown_execution_episode_role$'):
        b.allowed_children(SimpleNamespace(role='launch'),())


@pytest.mark.parametrize('parent',PARENTS)
def test_api_initialization_checks_original_parent_before_delegate(parent):
    b=binding(parent,'execution_job_submission/api_job_execution');ctx=SimpleNamespace(role='launch_api')
    calls=[];result=object()
    b._check_parent_inputs=lambda c:calls.append(('parent',c))
    b.api_execution=SimpleNamespace(initialize=lambda c:calls.append(('initialize',c)) or result)
    assert b.initialize(ctx) is result and calls==[('parent',ctx),('initialize',ctx)]
    error=LookupError('controlled missing original parent')
    def missing(c):raise error
    b._check_parent_inputs=missing
    with pytest.raises(LookupError) as caught:b.initialize(ctx)
    assert caught.value is error and calls==[('parent',ctx),('initialize',ctx)]


@pytest.mark.parametrize('parent',PARENTS)
@pytest.mark.parametrize('suffix,role',NATIVE)
def test_live_credit_and_facts_preserve_receiver_objects(parent,suffix,role):
    b=binding(parent,suffix);ctx=SimpleNamespace(role=role);selection={'fixture':'original selection'}
    credit=object();facts=object();calls=[]
    b.api_execution=SimpleNamespace(credit_view=lambda c,s:calls.append(('credit',c,s)) or credit,
        facts=lambda c,s:calls.append(('facts',c,s)) or facts)
    assert b._live_project_credit(ctx,selection) is credit
    assert b._live_facts(ctx,selection) is facts
    assert calls==[('credit',ctx,selection),('facts',ctx,selection)]
    error=RuntimeError('controlled original fact failure')
    def failed(c,s):raise error
    b.api_execution.facts=failed
    with pytest.raises(RuntimeError) as caught:b._live_facts(ctx,selection)
    assert caught.value is error


@pytest.mark.parametrize('parent',PARENTS)
def test_assignment_schema_uses_only_current_role_inputs(parent):
    launch=binding(parent,'execution_job_submission');calls=[]
    launch.resources={'original-api':{'kind':'api'}}
    def schema(key,*,selected,internal):
        calls.append((key,selected,internal));return {'type':'object','properties':{},'additionalProperties':False}
    launch._request_schema=schema
    result=launch.assignment_schema('launch',internal=True)
    assert result['properties']['version']=={'const':'execution_launch_assignment_v1'}
    assert calls==[('original-api',False,True)] and 'launch_instructions' in result['properties']
    results=binding(parent,'execution_result_acquisition')
    first=results.assignment_schema('results');second=results.assignment_schema('results')
    assert first==second and first is not second
    assert first['properties']['version']=={'const':'execution_results_assignment_v1'}
    first['properties'].clear();assert second['properties']


@pytest.mark.parametrize('parent',PARENTS)
def test_launch_assignment_retains_actual_input_version_callback(parent):
    b=binding(parent,'execution_job_submission');b.resources={'original-api':{'kind':'api'}}
    b._request_schema=lambda *a,**k:{'type':'object','properties':{},'additionalProperties':False}
    selection={'version':'execution_launch_assignment_v1','requests':{'original-api':{}},'immutable_input_versions':[],'constraints':{}}
    owner=SimpleNamespace(role='literature');scope={'fixture':'original scope'};calls=[]
    def launch(value,*,scope):calls.append(('launch',deepcopy(value),scope));return value
    b._launch=launch
    b._versions=lambda versions,s,**kw:calls.append(('versions',versions,s,kw))
    assert b.prepare_assignment(owner,'launch',selection,scope,'original-key')==selection
    assert calls==[('launch',selection,scope),('versions',[],scope,{'context':owner})]


@pytest.mark.parametrize('parent',PARENTS)
@pytest.mark.parametrize('recorded',[True,False])
def test_results_assignment_keeps_recorded_branch_and_live_selector_order(parent,recorded):
    b=binding(parent,'execution_result_acquisition');owner=SimpleNamespace(role='literature')
    selected={'version':'execution_results_assignment_v1','handoff_ref':'fixture-original-handoff','selector':{}}
    scope={'fixture':'scope'};calls=[];prior=object();target={'fixture':'owned target'}
    def original(p,value,s,key):
        calls.append(('recorded',p,value,s,key));return prior if recorded else None
    b._recorded_results_assignment=original
    b.job_progress_provider=SimpleNamespace(targets=SimpleNamespace(read_target=lambda ref,s:calls.append(('target',ref,s)) or target))
    b._selector=lambda value,t:calls.append(('selector',value,t))
    answer=b.prepare_assignment(owner,'results',selected,scope,'original-key')
    if recorded:
        assert answer is prior and calls==[('recorded',owner,selected,scope,'original-key')]
    else:
        assert answer==selected
        assert calls==[('recorded',owner,selected,scope,'original-key'),('target','fixture-original-handoff',scope),('selector',selected,target)]


@pytest.mark.parametrize('parent',PARENTS)
@pytest.mark.parametrize('suffix,role',NATIVE)
def test_completion_verdict_preserves_invalid_historical_and_api_paths(parent,suffix,role):
    b=binding(parent,suffix);ctx=SimpleNamespace(role=role);calls=[]
    proof={'version':'practical_completion_v1','run_id':'fixture-run','episode_id':'fixture-episode',
        'assignment_sha256':'a'*64,'endpoint':'usable_handoff','operation_key':'fixture-key',
        'receipt_sha256':'b'*64,'validation_keys':['fixture-not-scientific-authority']}
    b._closed_completion_verdict=lambda c,p:calls.append(('history',c,p)) or False
    b.api_execution=SimpleNamespace(verify_completion=lambda c,p:calls.append(('api',c,p)) or True)
    assert b.verify_completion(ctx,{}) is False and calls==[]
    assert b.verify_completion(ctx,proof) is False and calls==[('history',ctx,proof)]
    b._closed_completion_verdict=lambda c,p:None
    assert b.verify_completion(ctx,proof) is True and calls[-1]==('api',ctx,proof)
