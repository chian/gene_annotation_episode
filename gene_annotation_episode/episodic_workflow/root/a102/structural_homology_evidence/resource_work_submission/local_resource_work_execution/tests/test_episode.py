"""The A102 local resource work execution episode is a private binding in the ten-file form, reads its assignment
once, and declares a controlled return."""
import ast
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

from .. import episode as episode_module
from ..episode import LocalResourceWorkExecution
from ..goal import BINDING_PATH
from ..messages.final_to_parent import FINDING_FORM, RETURN_FORM
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from ..yield_estimator import yield_controller

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}
ASSIGNMENT = {'version': 'resource_launch_assignment_v1', 'resource_id': 'local', 'work_refs': ['art_work'],
              'input_refs': ['art_input'], 'handoff_unit': 4.0, 'check_unit': 3.0}


def test_the_class_inherits_only_the_system_episode_type_and_declares_the_defined_actions():
    assert LocalResourceWorkExecution.__bases__ == (EpisodeBinding,)
    assert LocalResourceWorkExecution.binding_path == BINDING_PATH == (
        'structural_homology_evidence/resource_work_submission/local_resource_work_execution')
    assert dict(LocalResourceWorkExecution.child_slots) == {}
    assert tuple(LocalResourceWorkExecution.services) == ('job_access',)
    assert set(LocalResourceWorkExecution.tools) == {'inspect_resource', 'launch_work', 'check_handoff', 'wait'}
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


def test_no_file_of_the_episode_offers_the_model_a_command_of_its_own():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts:
            text = path.read_text()
            assert 'exec_' + 'command' not in text and 'sub' + 'process' not in text, path


def test_the_return_is_controlled_data_credit_finding_and_the_job_rows():
    assert {name for name, spec in RETURN_FORM.fields.items() if spec.required} == {
        'credit', 'finding', 'handoff_refs', 'check_refs'}
    assert {name: spec.type for name, spec in RETURN_FORM.fields.items()} == {
        'credit': 'number', 'finding': 'record', 'handoff_refs': 'record_refs', 'check_refs': 'record_refs'}
    assert {name: spec.type for name, spec in FINDING_FORM.fields.items()} == {
        'job_state': 'text', 'result_available': 'boolean'}
    assert 'not_launched' in FINDING_FORM.fields['job_state'].options
    with pytest.raises(FormError):
        FINDING_FORM.admit({'job_state': 'the job looked fine to me', 'result_available': True}, 'finding')


def test_the_assignment_is_read_once_and_gives_the_completion_target_of_the_controller():
    parent_input = read_from_parent(ASSIGNMENT_FORM.admit(ASSIGNMENT, 'assignment'), {})
    assert parent_input == {'resource_id': 'local', 'work_ref': 'art_work', 'input_refs': ['art_input'],
                            'credit_units': {'handoff': 4.0, 'usable_check': 3.0}, 'completion_target': 7.0}
    controller = yield_controller(0.0, {'cost': 0.5, 'parameters': {'uncertainty_alpha': 0.05}}, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 7.0


def test_a_wrong_commission_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({key: value for key, value in ASSIGNMENT.items() if key != 'work_refs'}, 'assignment')
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({**ASSIGNMENT, 'version': 'other'}, 'assignment')
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({**ASSIGNMENT, 'command': ['true']}, 'assignment')
