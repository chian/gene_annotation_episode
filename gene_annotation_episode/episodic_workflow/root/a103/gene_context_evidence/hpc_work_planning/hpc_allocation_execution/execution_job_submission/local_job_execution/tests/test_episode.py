"""The A103 local job execution episode is a private binding in the ten-file form, and reads a real assignment."""
import ast
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

from .. import episode as episode_module
from ..episode import LocalJobExecution
from ..goal import BINDING_PATH
from ..messages.final_to_parent import RETURN_FORM
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def test_the_class_inherits_only_the_system_episode_type():
    assert LocalJobExecution.__bases__ == (EpisodeBinding,)
    assert LocalJobExecution.binding_path == BINDING_PATH
    assert dict(LocalJobExecution.child_slots) == {}
    assert tuple(LocalJobExecution.services) == ('job_access',)
    assert set(LocalJobExecution.tools) == {'exec_command'}


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
                 'execution_result_origin', 'execution_file_source_refs', 'execution_file_capture_outcomes',
                 'execution_blast_hsps'):
        assert name in RETURN_FORM.fields and not RETURN_FORM.fields[name].required


def _assignment(**changes):
    value = {'version': 'practical_assignment_v1', 'assignment_id': 'a1', 'resource_id': 'local',
             'resource_kind': 'local', 'workspace': '/work/space', 'endpoint': 'usable_handoff',
             'requested_job': {'argv': ['/bin/true'], 'environment': {}},
             'progress_requirements': [
                 {'key': 'cwd', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': '/work/space/run'}},
                 {'key': 'handoff', 'credit': 4.0, 'predicate': {'kind': 'requested_job_handoff'}}],
             'completion_keys': ['handoff'],
             'initial_context': {'revision': 0, 'cwd': '/work/space', 'environment': {}},
             'inventory_snapshot': {}, 'constraints': {}}
    value.update(changes)
    return value


def test_the_assignment_is_read_once_and_gives_the_completion_target():
    assignment = ASSIGNMENT_FORM.admit(_assignment(), 'assignment')
    parent_input = read_from_parent(assignment, {})
    assert parent_input['completion_target'] == 4.0
    assert parent_input['assignment']['completion_keys'] == ['handoff']
    controller = yield_controller(0.0, {'cost': 0.5, 'parameters': {}}, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 4.0


def test_a_wrong_commission_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit(_assignment(resource_kind='hpc'), 'assignment')
    with pytest.raises(ValueError):
        read_from_parent(ASSIGNMENT_FORM.admit(_assignment(completion_keys=['unknown']), 'assignment'), {})


def test_final_to_parent_returns_credit_finding_and_every_selectable_fact_and_the_form_admits_it():
    from ..messages.final_to_parent import RETURN_FORM, final_to_parent
    summary = {'execution_completion': {'completed': True}, 'receipts': [{'command': 'run'}],
               'receipt_refs': ['receipt_1'], 'handoff_refs': ['handoff_1'],
               'execution_progress': {'satisfied_keys': ['handoff'],
                                      'requirements': [{'key': 'handoff', 'satisfied': True},
                                                       {'key': 'outputs', 'satisfied': False}]},
               'commands': [{'failure': None}, {'failure': {'code': 'exit_1'}}], 'assignment': {'endpoint': 'usable_handoff'}}
    selection = [name for name, spec in RETURN_FORM.fields.items() if not spec.required]
    result = final_to_parent(summary, {'credit': 1.5}, selection)
    assert result['credit'] == 1.5 and result['finding']['unsatisfied_keys'] == ['outputs']
    assert result['finding']['failures'] == [{'code': 'exit_1'}] and result['execution_completed'] is True
    assert result['execution_result_origin'] == {'retained': False}
    assert RETURN_FORM.admit(result, 'return') == result
