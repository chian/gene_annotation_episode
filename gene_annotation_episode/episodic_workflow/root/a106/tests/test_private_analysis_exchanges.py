"""Offline full named requests and typed receipt custody for original analysis edges.

Real private constructors, schemas, assignment methods, Journal and EpisodeReceipts
are used. A retained-handoff read and already-admitted report are controlled ports;
these checks establish wiring, not a native service execution or scientific result.
"""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest

from .private_analysis_exchange_fixtures import (
    AXIS, analysis_workflow, module, api_assignment, launch_assignment, refs_schema, results_assignment,
)


@pytest.mark.parametrize('scientific',[False,True])
@pytest.mark.parametrize('role',['launch','launch_api','results'])
@pytest.mark.parametrize('redelivery',[False,True])
def test_private_analysis_request_and_saved_typed_return(
        analysis_workflow,scientific,role,redelivery,monkeypatch):
    store,host,_=analysis_workflow
    case=f'{scientific}-{role}-{redelivery}'
    path=(('annotation','root-'+case),)
    if scientific:path+=(('scientific_process','science-'+case),)
    path+=(('literature','literature-'+case),)
    if role=='launch_api':path+=(('launch','launch-'+case),)
    registry=host.episode_bindings
    parent=registry.for_path(path);child=registry.for_child(path,role)
    assert child.commissioning_parent==parent.binding_path
    endpoint=parent.child_request_preparer_for_binding(role,child.binding_path)
    assert endpoint.__module__==AXIS+'.'+parent.binding_path.replace('/','.')+'.to_child_'+child.binding_path.rsplit('/',1)[1]
    scope=store.validate_scope()
    identity=module('method_loop.identities').EpisodeRef
    source=SimpleNamespace(path=path,role=path[-1][0],scope=scope,run_id=host.run_id,
        episode_id=identity(host.run_id,path).episode_id,request={},
        assignment=launch_assignment() if role=='launch_api' else {})
    handoff='original-retained-handoff-'+case
    assignment=launch_assignment() if role=='launch' else api_assignment() if role=='launch_api' else results_assignment(handoff)
    reads=[]
    if role=='results':
        target={'assignment':api_assignment(),'scope':scope,'resource_id':'original-api'}
        def retained_handoff(reference,received_scope):
            reads.append((reference,deepcopy(received_scope)))
            assert reference==handoff and received_scope==scope
            return deepcopy(target)
        monkeypatch.setattr(child.job_progress_provider.targets,'read_target',retained_handoff)
    schema=refs_schema();declaration={'original':'closed-typed-report'}
    selected={'kind':'episode_child','role':role,'scope':scope,'assignment':assignment,
        'goal':'Validate the original offline exchange','purpose':'Return only selected retained evidence'}
    requests=[]
    boundary=SimpleNamespace(run_id=host.run_id,store=store,journal=host.journal,
        episode_bindings=SimpleNamespace(for_child=registry.for_child,received_form_references=lambda *args:[]),
        specialist=lambda source:parent,binding_context=lambda source:source,
        expanded_contract_form=lambda *args:(schema,declaration),child_initial_report_input=lambda *args:'{}',
        annotation_child_roles=None,services=SimpleNamespace(capabilities=lambda:()),
        launch_instructions=SimpleNamespace(materialize=lambda choice:requests.append(choice)))
    original=deepcopy(selected)
    prepared=endpoint(boundary,source,selected,5)
    assert prepared=={'scope':scope,'role':role,'schema':schema,'report_declaration':declaration,
        'initial':{},'episode_assignment':assignment,'scientific_process':None,'assignment':None}
    assert selected==original and requests==[None]
    assert reads==([(handoff,scope)] if role=='results' else [])

    # The common receiver has already admitted this closed typed form. Test its
    # original named recipient and actual persistent reference custody here.
    artifact=store.artifact('Explicit synthetic boundary output '+case,'text/plain')
    assert store.reference_subset([artifact],scope)==[]
    store.put('source',{'provider':'explicit_synthetic_exchange_boundary','accession':None,
        'uri':None,'artifact_ref':artifact,'text_ref':None,'request_ref':None,
        'version':None,'retrieved_at':None,'parent_source_refs':[]},origin='caller')
    assert store.reference_subset([artifact],scope)==[artifact]
    form={'refs':[artifact]}
    available=store.references(scope)
    module('communication').validate_form(form,schema,
        lambda ref,namespace:ref in available.get(namespace,()))
    child_path=path+((role,'child_5'),)
    child_id=identity(host.run_id,child_path).episode_id
    host.journal.save('runtime_episodes',{'episode_id':child_id,'path':json.dumps(child_path),
        'request':'{}','initial_credit':0,'state':'yielded','completion':None,'archive':None})
    action={'kind':'redeliver_report','delivery_ref':'delivery-'+case} if redelivery else {'kind':'episode_child','role':role}
    host.journal.save('runtime_actions',{'episode_id':source.episode_id,'decision_index':5,
        'action':json.dumps(action),'result':None,'credit':None})
    host.journal.save('runtime_report_attempts',{'parent_episode_id':source.episode_id,'decision_index':5,
        'delivery_ref':'delivery-'+case,'child_episode_id':child_id,'contract':'{}','form':json.dumps(form),'failure':None})
    receipts=module('episode_receipts').EpisodeReceipts(store,host.run_id)
    receipts.bind(source.episode_id)
    assert list(receipts.known(source.episode_id))==[]
    # This is a fresh admitted delivery, not a replay of a previously credited one.
    monkeypatch.setattr(module('episode_return_records').EpisodeReturnRecords,
        'recorded_admission_references',lambda *args:None)
    boundary.receipts=receipts;boundary.is_job_source=lambda source:False
    boundary.progress_provider=None;boundary.native_timing_information=None;boundary.job_episodes=None
    received=module('runtime').Workflow._receive_form(boundary,source,form,schema,5,redelivery=redelivery)
    assert received==[artifact] and list(receipts.known(source.episode_id))==[artifact]
    row=store.db.execute('SELECT receipt_kind,source_index FROM runtime_record_receipts '
        'WHERE run_id=? AND episode_id=? AND record_ref=?',(host.run_id,source.episode_id,artifact)).fetchone()
    assert tuple(row)==('report_redelivery' if redelivery else 'child_form',5)


def test_new_private_analysis_descriptors_reopen_exact_configuration(analysis_workflow):
    store,host,configuration=analysis_workflow
    selected=[binding for binding in host.episode_bindings._bindings
        if type(binding).__name__=='ExecutionEpisode' and '/published_evidence_assessment/' in '/'+binding.binding_path]
    assert len(selected)==6
    descriptors=[binding.as_record() for binding in selected]
    credit={role:{'definition':{'version':'explicit-original-analysis-credit'},'project':binding.project_credit}
        for binding in selected for role in binding.roles}
    composed=module('episode_composition').compose_episode_bindings(host.services,store=store,journal=host.journal,
        execution_backend=None,descriptors=descriptors,job_episodes=None,resource_estimator=None,
        role_credit_bindings=credit,directory=host.directory,tool_registry=host.tools)
    assert [type(binding) for binding in composed.bindings]==[type(binding) for binding in selected]
    assert [binding.as_record() for binding in composed.bindings]==descriptors
    for binding in composed.bindings:
        assert binding.resources==configuration['resources']
        assert binding.initial_information==configuration['initial_information']
        assert (binding.handoff_unit,binding.acquired_record_unit)==(2,3)
        assert (binding.log_window_bytes,binding.log_roles)==(128,('stdout','stderr'))


@pytest.mark.parametrize('scientific',[False,True])
@pytest.mark.parametrize('role',['launch','launch_api','results'])
def test_named_endpoint_rejects_other_literature_parents_same_role(analysis_workflow,scientific,role):
    store,host,_=analysis_workflow
    def parent_path(scientific):
        path=(('annotation','root'),)
        if scientific:path+=(('scientific_process','science'),)
        path+=(('literature','literature'),)
        return path+((('launch','launch'),) if role=='launch_api' else ())
    expected_path=parent_path(scientific);foreign_path=parent_path(not scientific)
    registry=host.episode_bindings
    parent=registry.for_path(expected_path);child=registry.for_child(expected_path,role)
    callback=parent.child_request_preparer_for_binding(role,child.binding_path)
    scope=store.validate_scope()
    source=SimpleNamespace(path=foreign_path,scope=scope)
    boundary=SimpleNamespace(store=store,episode_bindings=registry,
        expanded_contract_form=lambda *args:(refs_schema(),{}))
    with pytest.raises(ValueError,match='child_binding_path_conflict'):
        callback(boundary,source,{'scope':scope},5)


def test_original_service_factory_includes_scientific_literature_children_without_repricing(analysis_workflow):
    store,host,configuration=analysis_workflow
    factory=module('execution_service_setup').ExecutionServiceFactory(
        resources=configuration['resources'],initial_information=configuration['initial_information'],
        handoff_unit=2,acquired_record_unit=3,monitoring_information_unit=7,
        log_window_bytes=128,log_roles=('stdout','stderr'))
    declaration=deepcopy(factory.as_record())
    service=factory(store,run_id=host.run_id,directory=host.directory,tool_registry=host.tools)
    assert factory.as_record()==declaration
    descriptors={row['binding_id']:row for row in service.episode_binding_descriptors}
    prefix='scientific_process/published_evidence_assessment/'
    expected={prefix+home for home in ('execution_job_submission',
        'execution_job_submission/api_job_execution','execution_result_acquisition')}
    assert expected<=set(descriptors)
    for name in expected:
        original='scientific_process/'+name.removeprefix(prefix)
        assert descriptors[name]['configuration']==descriptors[original]['configuration']
    for role in ('launch','launch_api','results'):
        project=service.role_credit_bindings[role]['project']
        assert project.__self__.binding_path.startswith('scientific_process/execution_')
        assert service.role_credit_bindings[role]['definition']['handoff_unit']==2
        assert service.role_credit_bindings[role]['definition']['acquired_record_unit']==3
