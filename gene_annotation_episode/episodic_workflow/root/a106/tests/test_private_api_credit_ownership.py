"""Actual private operational-credit calls with declared saved-reader test ports.

This is a method boundary, not a real AppService/Store acquisition or scientific grade.
"""
import importlib
from types import SimpleNamespace
import pytest
from ..api_service_execution import APIServiceExecution

PREFIX='gene_annotation_episode.episodic_workflow.root.a106.'
PARENTS=('', 'published_evidence_assessment.', 'scientific_process.',
    'scientific_process.published_evidence_assessment.')
HOMES=tuple(parent+suffix for parent in PARENTS for suffix in (
    'execution_job_submission.api_job_execution','execution_result_acquisition'))


def reader_ports():
    api=APIServiceExecution.__new__(APIServiceExecution);calls=[]
    handoffs={'h_old':('resource','old'),'h_new':('resource','new'),'h_alias':('resource','new')}
    results={'r_old':('old-result',),'r_new':('new-result',),'r_alias':('new-result',)}
    def target(ref,scope):
        calls.append(('target',ref,scope))
        if ref not in handoffs:raise ValueError('not-a-handoff')
        resource,execution=handoffs[ref];return {'resource_id':resource,'execution_id':execution}
    def result(ref,scope):
        calls.append(('result',ref,scope))
        if ref not in results:raise ValueError('not-a-result')
        return results[ref]
    def facts(context,snapshot):
        calls.append(('facts',context,snapshot))
        return {'execution_handoff_refs':list(handoffs),'execution_result_refs':list(results)}
    api.read_target=target;api.result_identity=result;api.facts=facts
    api.handoff_unit=2.;api.acquired_record_unit=3.
    context=SimpleNamespace(scope={'declared':'controlled scope'})
    selection={'known_record_refs':[*handoffs,*results], 'initial_known_record_refs':['h_old','r_old']}
    return api,context,selection,calls


@pytest.mark.parametrize('home',HOMES)
def test_actual_private_credit_deduplicates_original_identities(home):
    cls=importlib.import_module(PREFIX+home+'.credit').ExecutionEpisodeCredit
    api,context,selection,calls=reader_ports();binding=SimpleNamespace(api_execution=api)
    view=cls._live_project_credit(binding,context,selection)
    assert view['credit']==view['operational_credit']==5
    assert view['new_handoff_count']==view['new_acquired_record_count']==1
    assert view['operational_credit_binding']['handoff_unit']==2.
    assert view['operational_credit_binding']['acquired_record_unit']==3.
    assert view['operational_credit_binding']['scientific_credit'] is False
    assert view['operational_credit_binding']['monitoring_credit'] is False
    assert calls[0]==('facts',context,{})
    assert all(call[2] is context.scope for call in calls if call[0]!='facts')


@pytest.mark.parametrize('home',HOMES)
def test_actual_private_initial_subset_guard_is_preserved(home):
    cls=importlib.import_module(PREFIX+home+'.credit').ExecutionEpisodeCredit
    api,context,selection,calls=reader_ports();selection['initial_known_record_refs'].append('not-known')
    with pytest.raises(ValueError,match='api_initial_references_must_be_known'):
        cls._live_project_credit(SimpleNamespace(api_execution=api),context,selection)
    assert calls==[('facts',context,{})]


@pytest.mark.parametrize('home',HOMES)
def test_actual_private_unknown_old_reference_does_not_fabricate_credit(home):
    cls=importlib.import_module(PREFIX+home+'.credit').ExecutionEpisodeCredit
    api,context,selection,calls=reader_ports()
    selection['known_record_refs'].append('unknown-old');selection['initial_known_record_refs'].append('unknown-old')
    view=cls._live_project_credit(SimpleNamespace(api_execution=api),context,selection)
    assert view['credit']==5 and view['new_handoff_count']==view['new_acquired_record_count']==1
    assert ('target','unknown-old',context.scope) in calls and ('result','unknown-old',context.scope) in calls


@pytest.mark.parametrize('home',HOMES)
def test_actual_private_new_identity_read_failure_is_not_swallowed(home):
    cls=importlib.import_module(PREFIX+home+'.credit').ExecutionEpisodeCredit
    api,context,selection,calls=reader_ports();original=api.read_target
    def rejected(ref,scope):
        if ref=='h_new':raise ValueError('controlled-new-identity-rejected')
        return original(ref,scope)
    api.read_target=rejected
    with pytest.raises(ValueError,match='controlled-new-identity-rejected'):
        cls._live_project_credit(SimpleNamespace(api_execution=api),context,selection)


@pytest.mark.parametrize('home',HOMES)
def test_actual_private_closed_credit_path_precedes_live_projection(home):
    cls=importlib.import_module(PREFIX+home+'.credit').ExecutionEpisodeCredit
    context=SimpleNamespace();selection={'declared':'original selection'};saved={'credit':-1.25,'historical':'controlled saved view'};calls=[]
    def closed(c,s):
        calls.append((c,s));return saved
    def unexpected(*args,**kwargs):raise AssertionError('closed credit must not be recomputed')
    binding=SimpleNamespace(_closed_operational_credit_view=closed,_live_project_credit=unexpected)
    assert cls.project_credit(binding,context,selection) is saved and calls==[(context,selection)]


from .test_actual_private_registry import constructed


def actual_arguments(constructed):
    store,host,_,bindings,_=constructed
    return dict(store=store,run_id=host.run_id,directory=host.directory,tool_registry=host.tools,
        handoff_unit=2.,acquired_record_unit=3.,configuration={
            'actual-api':{'kind':'api','service':'bvbrc_appservice','execution_contract':'bvbrc_appservice_execution_v1',
                'endpoints':{'AppService':'https://construction.invalid/app','Workspace':'https://construction.invalid/workspace'},
                'scientific_adapters':[]}})


@pytest.mark.parametrize('home',HOMES)
def test_actual_private_constructor_binds_its_own_credit_callback(constructed,home):
    arguments=actual_arguments(constructed);store,host,_,bindings,_=constructed
    cls=importlib.import_module(PREFIX+home+'.episode').ExecutionEpisode
    config=arguments.pop('configuration');binding=cls(bindings[0].services,**arguments,
        resources=config,initial_information={},log_window_bytes=128,log_roles=('stdout','stderr'))
    projector=binding.api_execution._credit_projector
    assert projector.__self__ is binding and projector.__func__ is type(binding)._api_operational_credit
    assert binding.api_execution.handoff_unit==2. and binding.api_execution.acquired_record_unit==3.
    assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==0
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]==0


@pytest.mark.parametrize('home',HOMES)
def test_existing_explicit_api_credit_override_stays_in_the_call_path(home):
    cls=importlib.import_module(PREFIX+home+'.credit').ExecutionEpisodeCredit
    context=SimpleNamespace();selection={'original':'selection'};result={'credit':0.375};calls=[]
    def custom(c,s):calls.append((c,s));return result
    binding=SimpleNamespace(api_execution=SimpleNamespace(credit_view=custom))
    assert cls._live_project_credit(binding,context,selection) is result and calls==[(context,selection)]


def test_actual_raw_constructor_default_keeps_the_original_credit_protocol(constructed):
    api=APIServiceExecution(**actual_arguments(constructed));ports,context,selection,_=reader_ports()
    api.facts=ports.facts;api.read_target=ports.read_target;api.result_identity=ports.result_identity
    assert api.credit_view(context,selection)['credit']==5


@pytest.mark.parametrize('disposition',['return','raise'])
def test_actual_raw_constructor_explicit_callback_preserves_identity_and_exception(constructed,disposition):
    calls=[];value={'credit':0.25};error=ValueError('original-explicit-projector-error')
    def projector(api,context,selection):
        calls.append((api,context,selection))
        if disposition=='raise':raise error
        return value
    api=APIServiceExecution(**actual_arguments(constructed),credit_projector=projector)
    context=SimpleNamespace();selection={'actual':'receiver'}
    if disposition=='raise':
        with pytest.raises(ValueError) as caught:api.credit_view(context,selection)
        assert caught.value is error
    else:assert api.credit_view(context,selection) is value
    assert calls==[(api,context,selection)]


def test_actual_raw_constructor_rejects_noncallable_new_credit_port(constructed):
    with pytest.raises(ValueError,match='api_credit_projector_must_be_callable'):
        APIServiceExecution(**actual_arguments(constructed),credit_projector=object())


@pytest.mark.parametrize('home',HOMES)
def test_actual_private_callback_executes_its_own_reader_prefix(home):
    cls=importlib.import_module(PREFIX+home+'.credit').ExecutionEpisodeCredit
    api,context,selection,calls=reader_ports()
    binding=SimpleNamespace(api_execution=api);dispatch=[]
    owned=cls._api_operational_credit.__get__(binding,type(binding))
    def selected(actual_api,actual_context,actual_selection):
        dispatch.append((actual_api,actual_context,actual_selection))
        return owned(actual_api,actual_context,actual_selection)
    api._credit_projector=selected
    result=cls._live_project_credit(binding,context,selection)
    assert dispatch==[(api,context,selection)]
    assert result['credit']==result['operational_credit']==5
    assert result['new_handoff_count']==result['new_acquired_record_count']==1
    assert calls[0]==('facts',context,{})
    assert all(row[2] is context.scope for row in calls if row[0]!='facts')
    assert result['operational_credit_binding']=={
        'version':importlib.import_module(PREFIX+'api_service_execution').VERSION,
        'handoff_unit':2.,'acquired_record_unit':3.,
        'scientific_credit':False,'monitoring_credit':False}
