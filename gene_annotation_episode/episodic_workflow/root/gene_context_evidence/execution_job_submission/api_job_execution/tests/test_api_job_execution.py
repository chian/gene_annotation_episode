"""The A103 ``api_job_execution`` binding: importing ``episode.py`` is the class-definition check; the folder holds
the ten-file set; no module imports another episode folder; its real forms and controller work."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import CompletionYieldController

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.gene_context_evidence.'
           'execution_job_submission.api_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}
ROOT_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'version': 'api_service_assignment', 'resource_id': 'ncbi_blast', 'service': 'ncbi_blast',
              'endpoint': 'usable_handoff', 'constraints': {}, 'request': {'program': 'blastp'},
              'immutable_input_versions': {}, 'scope': {'subject_refs': []}, 'input_refs': [],
              'completion_target': 2.0}


@pytest.fixture(scope='module')
def episode_module():
    return importlib.import_module(PACKAGE + '.episode')


def test_the_class_inherits_only_the_episode_base(episode_module):
    cls = episode_module.ApiJobExecution
    assert cls.__bases__ == (EpisodeBinding,)
    assert cls.binding_path == 'gene_context_evidence/execution_job_submission/api_job_execution'
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


def test_read_from_parent_keeps_the_old_properties_and_the_new_fields(episode_module):
    parent_input = episode_module.ApiJobExecution.read_from_parent(ASSIGNMENT, {'objective': 'submit'})
    assert parent_input['request'] == {'program': 'blastp'} and parent_input['completion_target'] == 2.0
    assert 'algorithm' not in parent_input and parent_input['message'] == {'objective': 'submit'}


def test_the_return_form_declares_credit_finding_and_selectable_facts(episode_module):
    form = episode_module.ApiJobExecution.return_form
    selected = form.select(('execution_handoff_refs', 'execution_completed', 'bvbrc_minhash_matches'))
    assert {'credit', 'finding', 'execution_handoff_refs', 'execution_completed',
            'bvbrc_minhash_matches'} <= set(selected.as_record())
    with pytest.raises(FormError):
        form.select(('credit',))
    with pytest.raises(FormError):
        form.select(('execution_not_a_fact',))


def test_final_to_parent_returns_the_recorded_facts_and_the_systems_credit(episode_module):
    cls = episode_module.ApiJobExecution
    summary = {'resource_id': 'ncbi_blast', 'service': 'ncbi_blast', 'handoff_refs': ['row_a'], 'result_refs': [],
               'completed': True, 'facts': {'bvbrc_minhash_matches': [{'genome': 'g'}]}, 'last_status': 'completed',
               'job_identity': 'RID1'}
    selection = ('execution_handoff_refs', 'execution_hmmer_domain_rows', 'bvbrc_minhash_matches')
    result = cls.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.5}, selection)
    cls.return_form.select(selection).admit(result, 'result')
    assert result['credit'] == 1.5 and result['execution_handoff_refs'] == ['row_a']
    assert result['execution_hmmer_domain_rows'] == []
    assert result['finding']['handoff_established'] is True and result['finding']['job_identity'] == 'RID1'
    everything = tuple(name for name, spec in cls.return_form.fields.items() if not spec.required)
    full = cls.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 1.5}, everything)
    assert full['execution_result_origin'] == {'retained': False} and full['bvbrc_minhash_counts'] == []
    assert cls.return_form.admit(full, 'return') == full


def test_the_controller_is_completion_toward_the_commissioned_target(episode_module):
    cls = episode_module.ApiJobExecution
    hmmer = {name: value for name, value in ASSIGNMENT.items() if name != 'request'}
    hmmer.update(version='api_execution_assignment', resource_id='ebi_hmmer', service='ebi_hmmer',
                 subject_ref='subject_a', algorithm='phmmer', database='pdb', parameters={}, page_size=10)
    parent_input = cls.read_from_parent(hmmer, {})
    settings = {'task_yield_profiles': {'launch_api:api_ebi_hmmer_phmmer_pdb_handoff':
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
