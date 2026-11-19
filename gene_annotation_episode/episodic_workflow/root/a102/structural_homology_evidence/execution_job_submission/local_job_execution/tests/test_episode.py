"""The A102 local job execution episode is a private binding in the ten-file form, and reads a real assignment."""
import ast
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    assess_validations)

from .. import episode as episode_module
from .. import task as task_file
from ..credit import credit
from ..episode import LocalJobExecution
from ..goal import BINDING_PATH
from ..messages.final_to_parent import RETURN_FORM, final_to_parent
from ..messages.internal_summary import BASELINE_CHECKED_AT
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def test_the_class_inherits_only_the_system_episode_type():
    assert LocalJobExecution.__bases__ == (EpisodeBinding,)
    assert LocalJobExecution.binding_path == BINDING_PATH == (
        'structural_homology_evidence/execution_job_submission/local_job_execution')
    assert dict(LocalJobExecution.child_slots) == {}
    assert tuple(LocalJobExecution.services) == ('job_access',)
    assert set(LocalJobExecution.tools) == {'exec_command'}
    assert not hasattr(LocalJobExecution, 'msg_to_child') and not hasattr(LocalJobExecution, 'read_from_child')


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
    for name in ('practical_completed', 'practical_receipt_digests', 'practical_receipt_refs',
                 'execution_handoff_refs', 'execution_result_refs', 'execution_completed',
                 'execution_result_origin'):
        assert name in RETURN_FORM.fields and not RETURN_FORM.fields[name].required


def _assignment(**changes):
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


def test_the_assignment_is_read_once_and_gives_the_completion_target_and_the_yield_profile():
    assignment = ASSIGNMENT_FORM.admit(_assignment(), 'assignment')
    parent_input = read_from_parent(assignment, {})
    assert parent_input['completion_target'] == 5.0
    assert parent_input['assignment']['completion_keys'] == ['cwd', 'handoff']
    settings = {'task_yield_profiles': {'launch_local:practical_local_handoff': {'cutoff': 0.5, 'parameters': {}}}}
    controller = yield_controller(0.0, settings, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 5.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_a_wrong_commission_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit(_assignment(resource_kind='hpc'), 'assignment')
    with pytest.raises(ValueError):
        read_from_parent(ASSIGNMENT_FORM.admit(_assignment(completion_keys=['unknown']), 'assignment'), {})
    with pytest.raises(ValueError, match='local_job_credited_requirement_outside_completion_keys'):
        read_from_parent(ASSIGNMENT_FORM.admit(_assignment(completion_keys=['handoff'], progress_requirements=[
            {'key': 'cwd', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': '/work/space/run'}},
            {'key': 'handoff', 'credit': 0.0, 'predicate': {'kind': 'requested_job_handoff'}}]), 'assignment'), {})


def test_the_local_transport_refuses_a_workspace_outside_the_configured_one(tmp_path):
    settings = {'resources': {'local': {'kind': 'local', 'workspace': str(tmp_path),
                                        'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}}},
                'coordinator_workspace': str(tmp_path / 'coordinator')}
    inside = read_from_parent(ASSIGNMENT_FORM.admit(_assignment(workspace=str(tmp_path / 'w'), initial_context={
        'revision': 0, 'cwd': str(tmp_path / 'w'), 'environment': {}},
        progress_requirements=[{'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
        completion_keys=['handoff']), 'assignment'), {})['assignment']
    task_file._operations(settings, inside).validate_action(
        inside, 'exec_command', {'cmd': 'true', 'workdir': str(tmp_path / 'w'), 'env': {}})
    outside = {**inside, 'workspace': '/elsewhere', 'initial_context': {**inside['initial_context'],
                                                                      'cwd': '/elsewhere'}}
    with pytest.raises(ValueError, match='execution_workspace_configuration_conflict'):
        task_file._operations(settings, outside)
    with pytest.raises(ValueError, match='execution_workdir_outside_workspace'):
        task_file._operations(settings, inside).validate_action(
            inside, 'exec_command', {'cmd': 'true', 'workdir': '/elsewhere', 'env': {}})


def _summary_before_any_command():
    """The summary shape ``internal_summary`` gives for a view with no outcomes, from the real library pieces."""
    assignment = ASSIGNMENT_FORM.admit(_assignment(), 'assignment')
    parent_input = read_from_parent(assignment, {})
    assignment = parent_input['assignment']
    initial = assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                 checked_at=BASELINE_CHECKED_AT)
    return {'assignment': assignment, 'completion_target': parent_input['completion_target'],
            'initial_validations': initial, 'receipts': [], 'receipt_refs': [], 'handoff_refs': [],
            'commands': [], 'execution_completion': None,
            'execution_progress': project_practical_credit(assignment, initial, [])}


def test_credit_is_the_projected_practical_credit_of_the_receipts_so_far():
    summary = _summary_before_any_command()
    assert credit(summary, None) == project_practical_credit(
        summary['assignment'], summary['initial_validations'], [])['credit']
    assert credit(summary, None) >= 0.0


def test_the_return_carries_the_systems_credit_and_the_finding_and_the_selected_facts():
    summary = _summary_before_any_command()
    result = final_to_parent(summary, {'credit': 0.0}, ['practical_completed', 'execution_result_refs'])
    assert result['credit'] == 0.0
    assert result['finding']['completed'] is False and result['finding']['commands_run'] == 0
    assert result['practical_completed'] is False and result['execution_result_refs'] == []
    RETURN_FORM.admit(result, 'return')
    origin = final_to_parent(summary, {'credit': 0.0}, ['execution_result_origin'])
    assert origin['execution_result_origin'] == {}
    RETURN_FORM.admit(origin, 'return')
