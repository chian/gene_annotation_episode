"""Actual private child-role callbacks under their registry-selected contexts."""
from __future__ import annotations
import importlib
from types import SimpleNamespace
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a110'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'biochemical_feasibility_evidence', 'biochemical_feasibility_evidence/hpc_work_planning',
    'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution')
HOMES = [('/'.join(filter(None, (prefix, suffix))), role) for prefix in PREFIXES
    for suffix, role in (('execution_job_submission', 'launch'),
        ('execution_job_submission/local_job_execution', 'launch_local'),
        ('execution_job_submission/hpc_job_execution', 'launch_hpc'),
        ('execution_result_acquisition', 'results'))]

@pytest.mark.parametrize('home,role', HOMES, ids=[home for home, _ in HOMES])
def test_actual_declared_and_available_edges_are_private(home, role):
    from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
    module = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode')
    owner = object.__new__(module.ExecutionEpisode)
    assert owner.roles == (role,)
    calls = []
    owner.resources = {'local': {'kind': 'local'}, 'pbs': {'kind': 'pbs_ssh'}}
    context = BindingContext(run_id='controlled-edge', episode_id='controlled-parent', role=role,
        path=((role, 'controlled'),), scope={'subject_refs': []}, assignment={}, request={})
    def launch(assignment):
        calls.append('launch.decode')
        return {'controlled': 'assignment'}
    def permitted(assignment, resource_id):
        assert assignment == {'controlled': 'assignment'}
        calls.append('permitted:' + resource_id)
        return resource_id == 'local'
    owner._launch, owner._permitted = launch, permitted
    declared = owner.child_roles(role)
    available = owner.allowed_children(context, ())
    if role == 'launch':
        assert declared == ('launch_local', 'launch_hpc')
        assert available == ('launch_local',)
        assert calls == ['launch.decode', 'permitted:local', 'permitted:pbs']
    else:
        assert declared == available == () and calls == []

@pytest.mark.parametrize('home,role', HOMES, ids=[home for home, _ in HOMES])
def test_actual_selected_child_contract_keeps_parent_context_and_failures(home, role):
    from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
    module = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode')
    owner = object.__new__(module.ExecutionEpisode)
    calls = []
    def annotation_required():
        calls.append('annotation_required')
        return True
    owner.services = SimpleNamespace(annotation_task_required=annotation_required)
    parent = BindingContext(run_id='controlled-contract', episode_id='scientific-parent', role='biochemical_feasibility_evidence',
        path=(('biochemical_feasibility_evidence', 'controlled'),), scope={'subject_refs': []}, assignment={}, request={})
    expected = ('execution_handoff_refs',) if role == 'launch' else ('execution_result_refs',) if role == 'results' else ()
    assert owner.required_return_sources(parent, role) == expected
    assert calls == ['annotation_required']
    calls.clear()
    assert owner.required_return_sources(None, role) == () and calls == []
    request = {'resource_kind': 'hpc', 'original_request': 'kept'}
    launch = BindingContext(run_id='controlled-contract', episode_id='launch-parent', role='launch',
        path=(('hpc', 'controlled-plan'), ('launch', 'controlled-launch')), scope={'subject_refs': []},
        assignment={'requests': {'pbs': request}}, request={})
    owner._permitted = lambda assignment, resource_id: True
    def schema(selected_role):
        owner.credit_kind(selected_role)
        calls.append('own_schema:' + selected_role)
        return {'controlled_original_schema': selected_role}
    owner.assignment_schema = schema
    value = owner.child_assignment_schema(launch, role)
    if role == 'launch_hpc':
        assert value == {'type': 'object', 'enum': [request]} and calls == []
        empty = BindingContext(run_id=launch.run_id, episode_id=launch.episode_id, role=launch.role,
            path=launch.path, scope=launch.scope, assignment={'requests': {}}, request={})
        with pytest.raises(ValueError, match='^frozen_hpc_launch_request_missing$'):
            owner.child_assignment_schema(empty, role)
    else:
        assert value == {'controlled_original_schema': role} and calls == ['own_schema:' + role]
