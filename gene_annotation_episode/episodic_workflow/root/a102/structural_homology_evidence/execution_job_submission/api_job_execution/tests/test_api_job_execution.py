"""The A102 ``api_job_execution`` binding: importing ``episode.py`` is the class-definition check; the folder holds
the ten-file set; no module imports another episode folder; its real forms and controller work."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.'
           'execution_job_submission.api_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}
ROOT_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'


@pytest.fixture(scope='module')
def episode_module():
    return importlib.import_module(PACKAGE + '.episode')


def test_the_class_inherits_only_the_episode_base(episode_module):
    assert episode_module.ApiJobExecution.__bases__ == (EpisodeBinding,)
    assert episode_module.ApiJobExecution.binding_path == (
        'structural_homology_evidence/execution_job_submission/'
        'api_job_execution')
    assert dict(episode_module.ApiJobExecution.child_slots) == {}


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert found == TEN_FILES
    assert not any(path.is_dir() and path.name not in ('messages', 'tests', '__pycache__')
                   for path in FOLDER.iterdir())


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = [node.module or ''] if isinstance(node, ast.ImportFrom) else \
                [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
            for name in names:
                assert not name.startswith(ROOT_PACKAGE), (str(path), name)
                assert not (isinstance(node, ast.ImportFrom) and node.level > 1), (str(path), name)


def test_the_assignment_form_admits_one_assignment_and_refuses_a_missing_field(episode_module):
    form = episode_module.ApiJobExecution.assignment_form
    assignment = {'scope': {'subject_refs': []}, 'version': 'api_service_assignment_v1', 'service': 'ncbi_blast',
                  'resource_id': 'ncbi_blast', 'request': {'program': 'blastp'}, 'input_refs': [],
                  'immutable_input_versions': {}, 'completion_target': 1.0}
    form.admit(assignment, 'assignment')
    with pytest.raises(FormError):
        form.admit({name: value for name, value in assignment.items() if name != 'completion_target'}, 'assignment')


def test_the_return_form_declares_credit_finding_and_selectable_facts(episode_module):
    form = episode_module.ApiJobExecution.return_form
    selected = form.select(('execution_handoff_refs', 'execution_completed'))
    assert {'credit', 'finding', 'execution_handoff_refs', 'execution_completed'} <= set(selected.as_record())
    with pytest.raises(FormError):
        form.select(('credit',))


def test_the_controller_is_completion_toward_the_commissioned_target(episode_module):
    parent_input = episode_module.ApiJobExecution.read_from_parent(
        {'scope': {}, 'version': 'api_service_assignment_v1', 'service': 'ncbi_blast', 'resource_id': 'r',
         'request': {}, 'input_refs': [], 'immutable_input_versions': {}, 'completion_target': 2.0},
        {'initial_report': 'nothing yet'})
    controller = episode_module.ApiJobExecution.yield_controller(0.0, {'cost': 0.1, 'parameters': {}}, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 2.0


def _summary(**changes):
    summary = {'resource_id': 'r', 'service': 'ncbi_blast', 'handoff_refs': ['h1'], 'result_refs': [],
               'completed': True, 'last_status': 'completed', 'report_update': 'handoff recorded', 'credit': 1.5}
    return {**summary, **changes}


def test_credit_is_the_unbounded_credit_of_the_summary():
    credit = importlib.import_module(PACKAGE + '.credit').credit
    assert credit(_summary(credit=7.25), None) == 7.25
    with pytest.raises(ValueError):
        credit(_summary(credit=float('inf')), None)


def test_final_to_parent_returns_the_completion_credit_and_the_selected_facts(episode_module):
    result = episode_module.ApiJobExecution.final_to_parent(
        _summary(), {'credit': 2.0}, ('execution_handoff_refs', 'execution_completed'))
    assert result['credit'] == 2.0 and result['execution_handoff_refs'] == ['h1']
    assert result['execution_completed'] is True and result['finding']['handoff_established'] is True
    assert 'execution_result_refs' not in result
    episode_module.ApiJobExecution.return_form.select(('execution_handoff_refs', 'execution_completed')).admit(
        result, 'result')


def test_final_to_parent_returns_every_selectable_fact_and_the_form_admits_it(episode_module):
    names = ('execution_handoff_refs', 'execution_result_refs', 'execution_completed', 'execution_result_origin')
    result = episode_module.ApiJobExecution.final_to_parent(_summary(), {'credit': 2.0}, names)
    assert result['execution_result_origin'] == {}
    assert set(names) <= set(result)
    episode_module.ApiJobExecution.return_form.select(names).admit(result, 'result')
