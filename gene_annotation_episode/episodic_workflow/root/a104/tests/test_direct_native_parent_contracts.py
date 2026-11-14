"""Real direct/scientific parent contracts; no provider or native execution."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a104.tests.test_a104_native_execution_private import native_frame, own_module
from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior

HOMES = tuple(parent + '/' + child
    for parent in ('execution_job_submission', 'scientific_process/execution_job_submission')
    for child in ('local_job_execution', 'hpc_job_execution'))

@pytest.fixture(params=HOMES, ids=HOMES)
def native_home(request):
    return request.param

def plain(value):
    return own_module('communication').plain(value)

def test_parent_contract_keeps_actual_parent_schema(native_frame):
    frame = native_frame
    value = plain(frame.parent.assignment)
    expected_schema = frame.parent_binding.assignment_schema('launch', internal=True)
    expected = own_module('execution_contracts').checked(value, expected_schema, 'invalid_execution_launch_assignment')
    actual = frame.binding._launch(value, scope=frame.parent.scope)
    assert actual == expected == value and actual is not value
    schema = own_module(frame.home + '/parent_launch_contract').parent_launch_schema(frame.binding)
    assert schema == expected_schema
    assert frame.parent_binding.binding_path == frame.binding.commissioning_parent
    assert frame.binding.resources == frame.parent_binding.resources

def test_literal_registry_parent_and_sibling_identity(native_frame):
    frame = native_frame
    sibling_parent = ('execution_job_submission' if frame.home.startswith('scientific_process/')
        else 'scientific_process/execution_job_submission')
    sibling = own_module(sibling_parent + '/' + frame.home.rsplit('/', 1)[1] + '/episode').ExecutionEpisode(
        frame.parent_binding.services, **frame.options)
    other_parent = own_module(sibling_parent + '/episode').ExecutionEpisode(frame.parent_binding.services, **frame.options)
    registry_type = own_module('episode_bindings').EpisodeBindingRegistry
    registry = registry_type((frame.binding, sibling))
    assert registry._child_binding(frame.parent_binding, frame.context.role) is frame.binding
    assert registry._child_binding(other_parent, frame.context.role) is sibling
    with pytest.raises(LookupError, match='episode_child_not_bound:'):
        registry_type((frame.binding,))._child_binding(other_parent, frame.context.role)

def test_original_admission_selected_object_once(native_frame, monkeypatch):
    frame = native_frame
    selected = plain(frame.context.assignment)
    original = frame.binding.prepare_assignment
    calls = []
    def observed(parent, role, value, scope, operation_key):
        calls.append((parent, role, value, scope, operation_key))
        return original(parent, role, value, scope, operation_key)
    monkeypatch.setattr(frame.binding, 'prepare_assignment', observed)
    admitted = frame.binding.prepare_assignment(frame.parent, frame.context.role, selected,
        frame.context.scope, f'{frame.context.run_id}:{frame.parent.episode_id}:original-admission')
    assert len(calls) == 1 and calls[0][0] is frame.parent and calls[0][2] is selected
    assert admitted == selected and admitted is not selected
    assert plain(frame.parent.assignment)['requests'][selected['resource_id']] == selected

def test_actual_build_initializes_from_saved_parent(native_frame, tmp_path, monkeypatch):
    adapter = SimpleNamespace(setup=lambda _: native_frame, module=own_module, role=native_frame.context.role)
    PlanningAllocationTaskBehavior.test_original_runtime_build_selects_this_binding_task(adapter, tmp_path, monkeypatch)

def test_parent_and_sibling_roles_remain_not_child_roles(native_frame):
    frame = native_frame
    sibling = 'launch_hpc' if frame.context.role == 'launch_local' else 'launch_local'
    assert frame.binding.roles == (frame.context.role,)
    for role in ('launch', sibling):
        with pytest.raises(ValueError, match='^unknown_execution_episode_role$'):
            frame.binding.assignment_schema(role, internal=True)

def test_original_wrong_parent_role_denial(native_frame):
    frame = native_frame
    path = frame.parent.path[:-1] + (('results', 'wrong-parent'),)
    wrong = replace(frame.parent, role='results', path=path,
        episode_id=own_module('method_loop.identities').EpisodeRef(frame.parent.run_id, path).episode_id)
    with pytest.raises(ValueError, match='^resource_child_role_owned_by_launch$'):
        frame.binding.prepare_assignment(wrong, frame.context.role, plain(frame.context.assignment),
            frame.context.scope, f'{frame.context.run_id}:{wrong.episode_id}:denied')

@pytest.mark.parametrize('defect', ('version', 'requests', 'constraints'))
def test_original_malformed_parent_is_not_accepted(native_frame, defect):
    frame = native_frame
    value = plain(frame.parent.assignment)
    if defect == 'version': value['version'] = 'not-the-original-launch-contract'
    elif defect == 'requests': value['requests'] = {}
    else: value['constraints'] = {'allowed_resource_ids': 'not-an-array'}
    code = 'invalid_execution_resource_constraints' if defect == 'constraints' else 'invalid_execution_launch_assignment'
    with pytest.raises(ValueError, match='^' + code + '$'):
        frame.binding._launch(value, scope=frame.parent.scope)

@pytest.mark.parametrize('defect', ('absent', 'sibling', 'foreign_run'))
def test_original_exact_saved_parent_lookup_is_retained(native_frame, defect):
    frame = native_frame
    before = frame.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
        (frame.parent.run_id, frame.parent.episode_id)).fetchone()
    assert before is not None
    # Negative controls modify only this isolated fixture's genuine parent row.
    # No row is used as a positive identity witness after mutation.
    if defect == 'absent':
        frame.store.db.execute('DELETE FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (frame.parent.run_id, frame.parent.episode_id))
    elif defect == 'sibling':
        sibling = frame.parent.path[:-1] + (('launch', 'different-original-parent'),)
        frame.store.db.execute('UPDATE runtime_episodes SET path=? WHERE run_id=? AND episode_id=?',
            (frame.runtime._json(sibling), frame.parent.run_id, frame.parent.episode_id))
    else:
        frame.store.db.execute('UPDATE runtime_episodes SET run_id=? WHERE run_id=? AND episode_id=?',
            ('different-original-run', frame.parent.run_id, frame.parent.episode_id))
    with pytest.raises(ValueError, match='^execution_original_launch_assignment_unavailable$'):
        frame.binding._check_parent_inputs(frame.context)
