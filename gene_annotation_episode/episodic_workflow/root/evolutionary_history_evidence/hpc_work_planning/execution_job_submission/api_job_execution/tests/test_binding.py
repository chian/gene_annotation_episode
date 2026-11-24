"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own forms and functions behave on real data. Nothing here is faked and nothing contacts a service."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').ApiJobExecution
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'version': 'api_service_assignment', 'resource_id': 'blast', 'service': 'ncbi_blast',
              'request': {'program': 'blastp'}, 'endpoint': 'usable_handoff', 'constraints': {},
              'input_refs': ['sub_1'], 'handoff_unit': 1.0, 'acquired_record_unit': 0.5}
MESSAGE = {'scientific_question': 'Which family?', 'selected_tool_info': {'name': 'blast'}}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {}
    assert tuple(EPISODE.services) == ('job_access',)


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_without_children():
    assert files() == FILES
    assert not (FOLDER / 'messages' / 'msg_to_child.py').exists()
    assert not (FOLDER / 'messages' / 'read_from_child.py').exists()


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_the_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, MESSAGE)
    assert parent_input['assignment']['resource_id'] == 'blast'
    assert 'input_refs' not in parent_input['assignment']
    assert parent_input['handoff_unit'] == 1.0 and parent_input['input_refs'] == ['sub_1']
    assert set(form.record_refs(admitted)) == {'sub_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(FormError, match='missing_field'):
        form.admit({key: value for key, value in ASSIGNMENT.items() if key != 'handoff_unit'}, 'test')


def test_the_return_form_declares_credit_finding_and_the_selectable_fact_sources():
    fields = EPISODE.return_form.fields
    assert fields['credit'].required and fields['finding'].required
    assert fields['execution_handoff_refs'].required and fields['execution_completed'].required
    assert not fields['execution_result_refs'].required and not fields['execution_blast_hsps'].required
    assert all(name.isidentifier() for name in fields)


def test_the_controller_is_a_completion_controller_whose_target_is_the_handoff_unit():
    parent_input = EPISODE.read_from_parent(EPISODE.assignment_form.admit(ASSIGNMENT, 'test'), MESSAGE)
    settings = {'task_yield_profiles': {'launch_api:api_ncbi_blast_handoff': {'cutoff': 0.1, 'parameters': {}}}}
    controller = EPISODE.yield_controller(0.0, settings, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 1.0 and controller.cost == 0.1
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        EPISODE.yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_credit_is_the_old_operational_formula_unbounded_over_the_summary():
    parent_input = EPISODE.read_from_parent(EPISODE.assignment_form.admit(ASSIGNMENT, 'test'), MESSAGE)
    summary = {'handoff_unit': 1.0, 'acquired_record_unit': 0.5, 'initial_handoff_identities': [],
               'initial_result_identities': [], 'handoff_identities': [], 'result_identities': []}
    assert EPISODE.credit(summary, None) == 0
    summary.update(handoff_identities=[['blast', 'e1']], result_identities=[['r', '1'], ['r', '2']])
    assert EPISODE.credit(summary, None) == 2.0
    summary.update(initial_handoff_identities=[['blast', 'e1']])
    assert EPISODE.credit(summary, None) == 1.0
    assert parent_input['acquired_record_unit'] == 0.5


def test_the_result_returns_the_systems_credit_and_the_selected_empty_sources():
    summary = {'handoff_refs': ['row_1'], 'handoff_identities': [['blast', 'e1']], 'result_refs': [],
               'result_identities': [], 'completed': True, 'submission_uncertain': False,
               'operations': [{'operation': 'submit', 'status': 'completed', 'submission_outcome': None}]}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.0}
    result = EPISODE.final_to_parent(summary, completion, ('execution_blast_hsps', 'execution_result_refs'))
    admitted = EPISODE.return_form.select(('execution_blast_hsps', 'execution_result_refs')).admit(result, 'test')
    assert admitted['credit'] == 1.0 and admitted['finding']['handoff_established'] is True
    assert admitted['execution_handoff_refs'] == ['row_1'] and admitted['execution_blast_hsps'] == []
    EPISODE.return_form.admit(result, 'return')
    with pytest.raises(FormError):
        EPISODE.return_form.select(('execution.masking_status',))
