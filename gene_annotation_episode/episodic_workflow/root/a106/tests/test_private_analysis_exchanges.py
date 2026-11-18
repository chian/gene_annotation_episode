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
        if scientific:path+=(('perturbation_evidence','science'),)
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
    prefix='perturbation_evidence/published_evidence_assessment/'
    expected={prefix+home for home in ('execution_job_submission',
        'execution_job_submission/api_job_execution','execution_result_acquisition')}
    assert expected<=set(descriptors)
    for name in expected:
        original='perturbation_evidence/'+name.removeprefix(prefix)
        assert descriptors[name]['configuration']==descriptors[original]['configuration']
    for role in ('launch','launch_api','results'):
        project=service.role_credit_bindings[role]['project']
        assert project.__self__.binding_path.startswith('perturbation_evidence/execution_')
        assert service.role_credit_bindings[role]['definition']['handoff_unit']==2
        assert service.role_credit_bindings[role]['definition']['acquired_record_unit']==3
