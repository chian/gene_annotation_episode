"""Actual private next/call/exchange with explicit engineering input ports.

Real Store/Journal rows exercise saved replay and prior-invalid-result display.
The context producer and final admission port are controlled seams; this is not
scientific projection, native execution, a new observation or workflow completion.
"""
import asyncio
from copy import deepcopy
from hashlib import sha256
from importlib import import_module
import json
from types import SimpleNamespace
import pytest
from .test_literature_private_boundaries import PACKAGE, HOMES


def module(name):
    return import_module(PACKAGE+'.'+name)


@pytest.fixture(scope='module')
def records(tmp_path_factory):
    with module('state').Store(tmp_path_factory.mktemp('private-presentation')/'state') as store:
        store.create_problem(raw_sequence='MAAA',molecule='protein')
        journal=module('episode_journal').Journal(store,'engineering-presentation-boundaries')
        yield store,journal,module('decision_exchanges').DecisionExchanges(journal)


def control(records,home,node_id,protocol,root_credit,*,failure=None):
    store,journal,exchanges=records;runtime=module('runtime')
    binding=module(home.replace('/','.')+'.episode').LiteratureEpisode
    task=object.__new__(binding.decision_source_type)
    task.episode_id='presentation_'+sha256(node_id.encode()).hexdigest()[:24]
    task.path=((binding.roles[0],task.episode_id),);task.scope=store.validate_scope();task.calls=1
    task._execution_context=None;task._model_snapshot=None;task._presented_conversation_key=None;task._delivery_resolution_ref=None
    task.request=SimpleNamespace(message=SimpleNamespace(as_record=lambda:{'episode_assignment':{}}))
    task.report_values={'inspected':False};task.report_basis=[]
    task.interpret_schema={'type':'object','properties':{'inspected':{'type':'boolean'}},'required':['inspected'],'additionalProperties':False}
    prior={'status':'invalid','record_refs':[],'changed_record_refs':[],
           'feedback':{'category':'engineering_fixture','code':'original_invalid_input'},
           'result':{'engineering_only':True,'science_attempted':False}}
    task.last_outcome=deepcopy(prior);task.last_outcome_index=0;task.feedback=task.last_outcome['feedback']
    with store.transaction():
        journal.save('runtime_actions',{'episode_id':task.episode_id,'decision_index':0,
            'action':json.dumps({'kind':'tool','tool':'engineering.fixture','arguments':{}}),'result':json.dumps(prior),'credit':0.0})
    original=journal.row('runtime_actions',task.episode_id,0)
    schema={'type':'object','properties':{'selection':{'type':'object','properties':{'kind':{'const':'engineering_intent'}},'required':['kind'],'additionalProperties':False},'report_update':deepcopy(task.interpret_schema)},'required':['selection','report_update'],'additionalProperties':False}
    response={'selection':{'kind':'engineering_intent'},'report_update':deepcopy(task.report_values)}
    credit={'mode':'annotation_axis_credit','root_score':0.0} if root_credit else 0.0
    trace={'context':[],'service':[],'provider':[],'admission':[]};error=RuntimeError('controlled '+str(failure)+' boundary failure')
    def context(view):
        trace['context'].append(view)
        return {'working_state':{},'visible_record_refs':[],'current_credit':deepcopy(credit),
                'controller':{'arms':[],'scores':[]},'credit_binding':{'kind':'engineering_metadata'},
                'pending_work':[],'last_local_outcome':deepcopy(prior),'feedback':deepcopy(prior['feedback']),
                'monitoring_information_credit':2.0,'monitoring_information_binding':{'kind':'engineering_duration_metadata'},
                '_completed_work_axis_results':{}}
    def instructions(source,context):
        assert source is task;trace['service'].append(deepcopy(context))
        if failure=='service':raise error
        return 'Caller-owned engineering instructions'
    async def complete(episode,role,instructions,context,output_schema):
        trace['provider'].append((episode,role,instructions,deepcopy(context),deepcopy(output_schema)))
        if failure=='provider':raise error
        return {'response':{'response_type':'select_action',**deepcopy(response)}} if protocol=='exchange' else deepcopy(response)
    workflow=SimpleNamespace(store=store,journal=journal,run_id=journal.run_id,
        inprocess_replay=None,execution_binding=None,decision_exchanges=exchanges,
        decision_protocol=runtime.DECISION_EXCHANGE_PROTOCOL if protocol=='exchange' else None,
        provider=SimpleNamespace(complete=complete),services=SimpleNamespace(instructions=instructions,decision_exchange_instructions=lambda:'Original exchange contract'),
        action_schema=lambda source:deepcopy(schema),contract_information_profile=lambda source:None,
        resource_context=lambda source:None,shared_information_context=lambda source:None,
        launch_instructions=SimpleNamespace(context=lambda:{},materialize=lambda value:None),
        available_child_roles=lambda source:(),binding_context=lambda source:SimpleNamespace(path=source.path,scope=source.scope,received_record_refs=()),
        episode_bindings=SimpleNamespace(initial_decision_context=lambda context:{}),
        execution_expectations=None,resource_estimator=None,native_estimation_context=lambda *args:None,
        native_event_information=None,permits_common_action=lambda source,kind:False,
        freeze_literature_numerical_contracts=lambda *args:None,receipts=None,
        history_preview=lambda *args,**kwargs:[],scientific_library_available=lambda source:False,
        controller_binding={},pending_work=lambda source:[])
    task.workflow=workflow;task.decision_state=context;marker=object()
    def admission(result,index,actual_context,actual_schema):
        trace['admission'].append((deepcopy(result),index,deepcopy(actual_context),deepcopy(actual_schema)));return marker
    task.apply_response=admission
    return SimpleNamespace(task=task,trace=trace,error=error,marker=marker,view=SimpleNamespace(units_consumed=0),
        journal=journal,exchanges=exchanges,store=store,original=original,prior=prior,response=response,schema=schema,credit=credit)


def no_new_work(c):
    assert c.journal.row('runtime_actions',c.task.episode_id,0)==c.original
    assert c.journal.row('runtime_actions',c.task.episode_id,1) is None
    assert c.store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=? AND episode_id=?',(c.journal.run_id,c.task.episode_id)).fetchone()[0]==0
    assert c.task.last_outcome==c.prior and c.task.last_outcome_index==0 and c.task.feedback is c.task.last_outcome['feedback']


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('protocol',('direct','exchange'))
@pytest.mark.parametrize('root_credit',(False,True))
def test_actual_private_boundary_and_saved_replay(records,request,home,protocol,root_credit):
    c=control(records,home,request.node.nodeid,protocol,root_credit)
    assert asyncio.run(c.task.next(c.view)) is c.marker
    assert len(c.trace['context'])==len(c.trace['service'])==len(c.trace['provider'])==1
    response,index,context,schema=c.trace['admission'][0]
    assert response==c.response and index==1 and schema==c.schema and context['current_credit']==c.credit
    assert context['monitoring_information_credit']==2.0 and context['monitoring_information_binding']=={'kind':'engineering_duration_metadata'}
    assert context['last_local_outcome']==c.prior and '_completed_work_axis_results' not in context
    if root_credit:assert 'completed_action_reports' not in context
    else:
        report,=context['completed_action_reports'];assert report['original_decisions']==[0] and report['recorded_outcome']['status']=='invalid' and report['credit_receipts']==[]
    if protocol=='exchange':
        row,=c.exchanges.rows(c.task.episode_id,1);table=row['request']['restoration']['snapshot']['action_yields']
        if root_credit:assert table=={'version':'annotation_axis_yield_table_v1','rows':[],'forecast_unit':'another_whole_axis_invocation','source':'actual_root_controller'}
        else:
            assert table['completion_count_basis']=='saved_own_controller_observations' and table['yield_basis']=='saved_signed_marginal_credit_excluding_inherited_baseline'
            category,=table['rows'];assert category['completed_actions']==0 and category['total_yield']==0.0 and category['attempted_uncompleted']==1
    saved=c.journal.row('runtime_model_calls',c.task.episode_id,1);assert json.loads(saved['response'])==c.response
    no_new_work(c);c.task.calls=1
    assert asyncio.run(c.task.next(c.view)) is c.marker
    assert c.journal.row('runtime_model_calls',c.task.episode_id,1)==saved and c.trace['admission'][1]==c.trace['admission'][0]
    assert len(c.trace['context'])==len(c.trace['service'])==len(c.trace['provider'])==1
    no_new_work(c)


@pytest.mark.parametrize('home',(HOMES[0],HOMES[-1]))
@pytest.mark.parametrize('failure',('service','provider'))
def test_original_exception_identity(records,request,home,failure):
    c=control(records,home,request.node.nodeid,'direct',False,failure=failure)
    with pytest.raises(RuntimeError) as caught:asyncio.run(c.task.next(c.view))
    assert caught.value is c.error and c.trace['admission']==[]
    assert len(c.trace['service'])==1 and len(c.trace['provider'])==(1 if failure=='provider' else 0)
    assert c.journal.row('runtime_model_calls',c.task.episode_id,1)['response'] is None
    no_new_work(c)


@pytest.mark.parametrize('home',(HOMES[0],HOMES[-1]))
def test_actual_delivery_context_and_saved_identity_guard(records,request,home):
    c=control(records,home,request.node.nodeid,'direct',False);calls=[]
    def resolve(source,reference,context):
        assert source is c.task;calls.append(reference)
        return {**context,'pending_child_delivery':{'delivery_ref':reference}},deepcopy(c.schema)
    c.task.workflow.delivery_resolution_inputs=resolve
    assert asyncio.run(c.task.next(c.view,delivery_ref='original_engineering_delivery')) is c.marker
    saved=c.journal.row('runtime_model_calls',c.task.episode_id,1);c.task.calls=1
    with pytest.raises(module('runtime').WorkflowError,match='restored_delivery_resolution_identity_conflict') as caught:
        asyncio.run(c.task.next(c.view,delivery_ref='different_engineering_delivery'))
    assert type(caught.value) is module('runtime').WorkflowError and calls==['original_engineering_delivery']
    assert c.journal.row('runtime_model_calls',c.task.episode_id,1)==saved and len(c.trace['provider'])==1
    no_new_work(c)


@pytest.mark.parametrize('protocol',('direct','exchange'))
def test_axis_specific_provider_presentation_route(records,request,protocol):
    c=control(records,HOMES[-1],request.node.nodeid,protocol,False);calls=[];renderer=object()
    async def presented(episode,role,instructions,context,schema,*,prompt_renderer):
        calls.append(prompt_renderer)
        return await c.task.workflow.provider.complete(episode,role,instructions,context,schema)
    c.task.workflow.provider.complete_with_presentation=presented
    c.task.workflow.specialist=lambda source:SimpleNamespace(decision_prompt_renderer=renderer)
    assert asyncio.run(c.task.next(c.view)) is c.marker
    assert calls==[]
    assert len(c.trace['service'])==len(c.trace['provider'])==1
    no_new_work(c)
