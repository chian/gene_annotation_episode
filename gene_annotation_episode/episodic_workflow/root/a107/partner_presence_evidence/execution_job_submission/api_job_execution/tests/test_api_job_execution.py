"""The A107 ``api_job_execution`` binding: importing ``episode.py`` is the class-definition check; the folder holds
the ten-file set; no module imports another episode folder; its real forms and controller work."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.'
           'execution_job_submission.api_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}
ROOT_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'scope': {'subject_refs': []}, 'version': 'api_service_assignment', 'service': 'ncbi_blast',
              'algorithm': 'blastp', 'database': 'swissprot', 'resource_id': 'ncbi_blast',
              'request': {'program': 'blastp'}, 'input_refs': [], 'immutable_input_versions': {},
              'completion_target': 2.0}


@pytest.fixture(scope='module')
def episode_module():
    return importlib.import_module(PACKAGE + '.episode')


def test_the_class_inherits_only_the_episode_base(episode_module):
    cls = episode_module.ApiJobExecution
    assert cls.__bases__ == (EpisodeBinding,)
    assert cls.binding_path == 'partner_presence_evidence/execution_job_submission/api_job_execution'
    assert dict(cls.child_slots) == {}
    assert tuple(cls.services) == ('job_access',)


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
    form.admit(ASSIGNMENT, 'assignment')
    with pytest.raises(FormError):
        form.admit({name: value for name, value in ASSIGNMENT.items() if name != 'completion_target'}, 'assignment')
    with pytest.raises(FormError):
        form.admit({**ASSIGNMENT, 'version': 'practical_assignment'}, 'assignment')


def test_the_return_form_declares_credit_finding_and_selectable_facts(episode_module):
    form = episode_module.ApiJobExecution.return_form
    selected = form.select(('execution_handoff_refs', 'execution_completed', 'execution_nhmmer_locus_rows'))
    assert {'credit', 'finding', 'execution_handoff_refs', 'execution_completed',
            'execution_nhmmer_locus_rows'} <= set(selected.as_record())
    with pytest.raises(FormError):
        form.select(('credit',))
    with pytest.raises(FormError):
        form.select(('execution_not_a_fact',))


def test_final_to_parent_returns_the_recorded_facts_and_the_systems_credit(episode_module):
    cls = episode_module.ApiJobExecution
    summary = {'resource_id': 'ncbi_blast', 'service': 'ncbi_blast', 'handoff_refs': ['row_a'], 'result_refs': [],
               'completed': True, 'facts': {'execution_nhmmer_locus_rows': [{'locus': 'l'}]}, 'last_status': 'completed',
               'report_update': 'handoff recorded'}
    selection = ('execution_handoff_refs', 'execution_hmmer_domain_rows', 'execution_nhmmer_locus_rows')
    result = cls.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.5}, selection)
    cls.return_form.select(selection).admit(result, 'result')
    assert result['credit'] == 1.5 and result['execution_handoff_refs'] == ['row_a']
    assert result['execution_hmmer_domain_rows'] == []
    assert result['finding']['handoff_established'] is True
    every = tuple(sorted(name for name, field in cls.return_form.fields.items() if not field.required))
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.5}
    full = cls.final_to_parent(summary, completion, every)
    cls.return_form.select(every).admit(full, 'result')
    assert full['execution_result_origin'] == {} and full['execution_blast_hsps'] == []


def test_the_controller_is_completion_toward_the_commissioned_target(episode_module):
    cls = episode_module.ApiJobExecution
    parent_input = cls.read_from_parent(ASSIGNMENT, {'initial_report': 'nothing yet'})
    settings = {'task_yield_profiles': {'launch_api:api_ncbi_blast_blastp_swissprot_handoff':
                                        {'cutoff': 0.1, 'parameters': {}}}}
    controller = cls.yield_controller(0.0, settings, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 2.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required'):
        cls.yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


def test_credit_reads_the_summary_and_never_bounds_it(episode_module):
    credit = episode_module.ApiJobExecution.credit
    assert credit({'credit': 7.5}, None) == 7.5
    with pytest.raises(ValueError):
        credit({'credit': float('nan')}, None)
