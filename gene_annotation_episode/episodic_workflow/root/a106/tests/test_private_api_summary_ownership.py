"""Actual private/raw API summary methods with declared controlled reader ports."""
import importlib
from types import SimpleNamespace
import pytest
from ..api_service_execution import APIServiceExecution
from .test_actual_private_registry import constructed
PREFIX='gene_annotation_episode.episodic_workflow.root.a106.'
HOMES=tuple(p+'execution_job_submission.api_job_execution' for p in ('','published_evidence_assessment.','perturbation_evidence.','perturbation_evidence.published_evidence_assessment.'))


def ports(completed):
    api=APIServiceExecution.__new__(APIServiceExecution);calls=[]
    request={'actual':'original request'};assignment={'request':request}
    context=SimpleNamespace(episode_id='original-episode',assignment=assignment,role='launch_api')
    events=[{'name':'same','event':{'state':'earlier','kind':'original-kind','facts':{'original':1},'failure_code':None}},
        {'name':'different','event':{'state':'failed','kind':'other-kind','facts':{'qualified':True},'failure_code':'source-unavailable'}},
        {'name':'same','event':{'state':'later','kind':'original-kind','facts':{'original':2},'failure_code':None}}]
    def initialize(value):calls.append(('initialize',value))
    def inputs(value):calls.append(('context',value));return assignment,SimpleNamespace(service='bvbrc_appservice'),object()
    def read(identity):calls.append(('events',identity));return events
    def completion(value):calls.append(('completion',value));return {'original':'proof'} if completed else None
    api.initialize=initialize;api._context=inputs;api._events=read;api._completion=completion
    expected={'api_service':'bvbrc_appservice','api_request':request,'api_received_progress':{
        'same':{'state':'later','kind':'original-kind','facts':events[-1]['event']['facts'],'failure_code':None},
        'different':{'state':'failed','kind':'other-kind','facts':events[1]['event']['facts'],'failure_code':'source-unavailable'}},
        'api_execution_completed':completed}
    return api,context,calls,expected


@pytest.mark.parametrize('completed',[False,True])
def test_raw_original_summary_preserves_read_order_qualifications_and_last_event(completed):
    api,context,calls,expected=ports(completed);actual=api.decision_context(context,{'unused':'original view'})
    assert actual==expected and actual['api_request'] is expected['api_request']
    assert calls==[('initialize',context),('context',context),('events',context.episode_id),('completion',context)]


def test_raw_original_initialization_failure_precedes_other_reads():
    api,context,calls,_=ports(False);error=ValueError('original-initialization-error')
    def rejected(value):calls.append(('initialize',value));raise error
    api.initialize=rejected
    with pytest.raises(ValueError) as caught:api.decision_context(context)
    assert caught.value is error and calls==[('initialize',context)]


@pytest.mark.parametrize('home',HOMES)
@pytest.mark.parametrize('completed',[False,True])
def test_actual_private_summary_callback_executes_original_statements(home,completed):
    cls=importlib.import_module(PREFIX+home+'.internal_summary').OperationalSummary
    api,context,calls,expected=ports(completed);binding=SimpleNamespace();invocations=[]
    owned=cls._api_decision_summary.__get__(binding,type(binding))
    def selected(a,c,v):invocations.append((a,c,v));return owned(a,c,v)
    api._decision_summary=selected;view={'actual':'view'}
    assert api.decision_context(context,view)==expected
    assert invocations==[(api,context,view)]
    assert calls==[('initialize',context),('context',context),('events',context.episode_id),('completion',context)]


@pytest.mark.parametrize('home',HOMES)
def test_existing_private_outer_summary_preserves_api_override(home):
    cls=importlib.import_module(PREFIX+home+'.internal_summary').OperationalSummary
    context=SimpleNamespace(role='launch_api',assignment={'original':'assignment'});view=object();calls=[]
    def kind(role):calls.append(('role',role))
    def facts(c,s):calls.append(('facts',c,s));return {'original':'progress'}
    def summary(c,v):calls.append(('summary',c,v));return {'custom_summary':{'original':True}}
    binding=SimpleNamespace(credit_kind=kind,facts=facts,api_execution=SimpleNamespace(decision_context=summary))
    assert cls.decision_context(binding,context,view)=={'execution_assignment':context.assignment,'execution_progress':{'original':'progress'},'custom_summary':{'original':True}}
    assert calls==[('role','launch_api'),('facts',context,{}),('summary',context,view)]


def arguments(constructed):
    store,host,_,bindings,_=constructed
    return dict(store=store,run_id=host.run_id,directory=host.directory,tool_registry=host.tools,
        handoff_unit=2.,acquired_record_unit=3.,configuration={'api':{'kind':'api','service':'bvbrc_appservice',
            'execution_contract':'bvbrc_appservice_execution_v1',
            'endpoints':{'AppService':'https://construction.invalid/app','Workspace':'https://construction.invalid/workspace'},'scientific_adapters':[]}})


@pytest.mark.parametrize('home',HOMES)
def test_actual_private_constructor_binds_summary_to_that_object(constructed,home):
    store,host,_,bindings,_=constructed;kw=arguments(constructed);config=kw.pop('configuration')
    cls=importlib.import_module(PREFIX+home+'.episode').ExecutionEpisode
    binding=cls(bindings[0].services,**kw,resources=config,initial_information={},log_window_bytes=128,log_roles=('stdout','stderr'))
    callback=binding.api_execution._decision_summary
    assert callback.__self__ is binding and callback.__func__ is type(binding)._api_decision_summary
    assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==0
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]==0


@pytest.mark.parametrize('home',HOMES)
def test_private_summary_keeps_original_reader_error_identity(home):
    cls=importlib.import_module(PREFIX+home+'.internal_summary').OperationalSummary
    api,context,calls,_=ports(False);error=KeyError('original-event-read')
    def failed(identity):calls.append(('events',identity));raise error
    api._events=failed;binding=SimpleNamespace()
    api._decision_summary=cls._api_decision_summary.__get__(binding,type(binding))
    with pytest.raises(KeyError) as caught:api.decision_context(context)
    assert caught.value is error and calls==[('initialize',context),('context',context),('events',context.episode_id)]


@pytest.mark.parametrize('disposition',['return','raise'])
def test_actual_raw_constructor_custom_summary_identity(constructed,disposition):
    result={'original':'summary'};error=ValueError('custom-summary');calls=[]
    def callback(api,context,view):
        calls.append((api,context,view))
        if disposition=='raise':raise error
        return result
    api=APIServiceExecution(**arguments(constructed),decision_summary=callback);context=object();view=object()
    if disposition=='raise':
        with pytest.raises(ValueError) as caught:api.decision_context(context,view)
        assert caught.value is error
    else:assert api.decision_context(context,view) is result
    assert calls==[(api,context,view)]


def test_actual_raw_constructor_rejects_noncallable_summary(constructed):
    with pytest.raises(ValueError,match='api_decision_summary_must_be_callable'):
        APIServiceExecution(**arguments(constructed),decision_summary=object())
