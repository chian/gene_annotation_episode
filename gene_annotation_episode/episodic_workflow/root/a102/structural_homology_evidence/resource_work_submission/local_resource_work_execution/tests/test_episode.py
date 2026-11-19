"""The A102 local resource work execution episode is a private binding in the ten-file form, and reads a real
assignment."""
import ast
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

from .. import episode as episode_module
from .. import task as task_file
from ..episode import LocalResourceWorkExecution
from ..goal import BINDING_PATH
from ..messages.final_to_parent import RETURN_FORM
from ..messages.internal_summary import execution_handoffs
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def test_the_class_inherits_only_the_system_episode_type():
    assert LocalResourceWorkExecution.__bases__ == (EpisodeBinding,)
    assert LocalResourceWorkExecution.binding_path == BINDING_PATH == (
        'structural_homology_evidence/resource_work_submission/local_resource_work_execution')
    assert dict(LocalResourceWorkExecution.child_slots) == {}
    assert tuple(LocalResourceWorkExecution.services) == ('job_access',)
    assert set(LocalResourceWorkExecution.tools) == {
        'exec_command', 'resource_capabilities', 'resource_inspect', 'resource_check_handoff', 'reason'}
    assert not hasattr(LocalResourceWorkExecution, 'msg_to_child')
    assert not hasattr(LocalResourceWorkExecution, 'read_from_child')


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
             if path.is_file() and '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert found == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level <= (1 if path.parent == FOLDER else 2) or 'tests' in path.parts, (path, node.module)
                modules = [node.module or '']
            for module in modules:
                assert '.episodic_workflow.root' not in module or module.startswith(PACKAGE), (path, module)


def test_the_return_form_declares_credit_and_finding_and_the_old_fact_sources_as_selectable():
    required = {name for name, spec in RETURN_FORM.fields.items() if spec.required}
    assert required == {'credit', 'finding'}
    for name in ('execution_handoff', 'execution_handoffs', 'execution_handoff_record_refs'):
        assert name in RETURN_FORM.fields and not RETURN_FORM.fields[name].required


SELECTION = {'resource_id': 'local', 'kind': 'local', 'allocation': {'cpu': 1, 'memory_bytes': None,
                                                                      'scratch_bytes': None},
             'capability_binding_ref': 'registry_1'}


def _practical(**changes):
    value = {'version': 'practical_assignment_v1', 'assignment_id': 'a1', 'resource_id': 'local',
             'resource_kind': 'local', 'workspace': '/work/space', 'endpoint': 'usable_handoff',
             'requested_job': {'argv': ['/bin/true'], 'environment': {}},
             'progress_requirements': [
                 {'key': 'cwd', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': '/work/space/run'}},
                 {'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
             'completion_keys': ['cwd', 'handoff'],
             'initial_context': {'revision': 0, 'cwd': '/work/space', 'environment': {}},
             'inventory_snapshot': {}, 'constraints': {}}
    value.update(changes)
    return value


def _assignment(**changes):
    value = {'version': 'resource_launch_assignment_v1', 'job_request': {'argv': ['/bin/true']},
             'immutable_input_versions': [], 'constraints': {}, 'resource_selection': SELECTION,
             'software_knowledge_refs': [], 'resource_knowledge_refs': [], 'adapter_assignment': _practical(),
             'scope': {'subjects': []}}
    value.update(changes)
    return value


def test_the_assignment_is_read_once_and_gives_the_completion_target_and_the_yield_profile():
    parent_input = read_from_parent(ASSIGNMENT_FORM.admit(_assignment(), 'assignment'), {})
    assert parent_input['completion_target'] == 5.0
    assert parent_input['assignment']['completion_keys'] == ['cwd', 'handoff']
    assert parent_input['launch']['resource_selection'] == SELECTION
    settings = {'task_yield_profiles': {'launch_local:practical_local_handoff': {'cutoff': 0.5, 'parameters': {}}}}
    controller = yield_controller(0.0, settings, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 5.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_a_wrong_commission_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({key: value for key, value in _assignment().items() if key != 'scope'}, 'assignment')
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit(_assignment(version='other'), 'assignment')
    with pytest.raises(ValueError, match='explicit_local_resource_selection_required'):
        read_from_parent(ASSIGNMENT_FORM.admit(
            _assignment(resource_selection={**SELECTION, 'kind': 'hpc'}), 'assignment'), {})
    with pytest.raises(ValueError, match='resource_selection_conflict'):
        read_from_parent(ASSIGNMENT_FORM.admit(
            _assignment(resource_selection={**SELECTION, 'resource_id': 'other'}), 'assignment'), {})
    with pytest.raises(ValueError, match='local_resource_credited_requirement_outside_completion_keys'):
        read_from_parent(ASSIGNMENT_FORM.admit(_assignment(adapter_assignment=_practical(
            completion_keys=['handoff'])), 'assignment'), {})


def _capability(resource_id, tools):
    return {'resource_id': resource_id, 'kind': 'local', 'availability': 'unknown', 'observed_at': 'now',
            'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': tools, 'local_resources': {},
            'allocation_limits': {'cpu': None, 'memory_bytes': None, 'scratch_bytes': None}}


def test_the_capabilities_list_unbound_resources_without_tools_and_require_the_selected_one():
    settings = {'resources': {'local': {'kind': 'local'}},
                'resource_capabilities': [_capability('local', ['exec_command']), _capability('spare', ['exec_command'])]}
    listed = {item['resource_id']: item for item in task_file.capabilities(settings, SELECTION)}
    assert listed['local']['tool_names'] == ['exec_command'] and listed['spare']['tool_names'] == []
    with pytest.raises(ValueError, match='resource_not_bound'):
        task_file.capabilities(settings, {**SELECTION, 'resource_id': 'missing'})
    with pytest.raises(ValueError, match='resource_capability_tool_not_bound'):
        task_file.capabilities({**settings, 'resource_capabilities': [_capability('local', ['unknown_tool'])]},
                               SELECTION)


def _handoff(handle, checked_at, state='usable'):
    return {'version': 'execution_handoff_v1', 'execution_handle': handle, 'resource_selection': SELECTION,
            'checked_at': checked_at, 'state': state, 'check_record_refs': []}


def test_the_handoff_facts_keep_the_latest_usable_check_of_each_identity_in_identity_order():
    found = execution_handoffs([_handoff('b', '2'), _handoff('a', '1'), _handoff('a', '3'),
                                _handoff('c', '4', 'unavailable')])
    assert [(item['execution_handle'], item['checked_at']) for item in found] == [('a', '3'), ('b', '2')]


def test_the_local_transport_refuses_a_workspace_outside_the_configured_one(tmp_path):
    settings = {'resources': {'local': {'kind': 'local', 'workspace': str(tmp_path),
                                        'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}}},
                'coordinator_workspace': str(tmp_path / 'coordinator')}
    inside = read_from_parent(ASSIGNMENT_FORM.admit(_assignment(adapter_assignment=_practical(
        workspace=str(tmp_path / 'w'), initial_context={'revision': 0, 'cwd': str(tmp_path / 'w'),
                                                        'environment': {}},
        progress_requirements=[{'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
        completion_keys=['handoff'])), 'assignment'), {})['assignment']
    task_file._operations(settings, inside).validate_action(
        inside, 'exec_command', {'cmd': 'true', 'workdir': str(tmp_path / 'w'), 'env': {}})
    outside = {**inside, 'workspace': '/elsewhere', 'initial_context': {**inside['initial_context'],
                                                                      'cwd': '/elsewhere'}}
    with pytest.raises(ValueError, match='execution_workspace_configuration_conflict'):
        task_file._operations(settings, outside)
    with pytest.raises(ValueError, match='execution_workdir_outside_workspace'):
        task_file._operations(settings, inside).validate_action(
            inside, 'exec_command', {'cmd': 'true', 'workdir': '/elsewhere', 'env': {}})
