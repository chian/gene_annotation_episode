"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks, the
folder holds exactly the ten-file set, and no module of the folder imports another episode folder."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.'
           'execution_job_submission.hpc_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def test_the_class_passes_its_definition_checks_and_inherits_only_the_episode_type():
    episode = importlib.import_module(PACKAGE + '.episode')
    binding = episode.HpcJobExecution
    assert binding.__bases__ == (EpisodeBinding,)
    assert binding.binding_path == ('gene_context_evidence/hpc_work_planning/execution_job_submission/'
                                    'hpc_job_execution')
    assert dict(binding.child_slots) == {}
    assert tuple(binding.services) == ('job_access',)
    assert set(binding.return_form.fields) >= {'credit', 'finding'}


def test_the_folder_holds_exactly_the_ten_file_set():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert found == TEN_FILES


def test_no_module_of_the_folder_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        depth = len(path.relative_to(FOLDER).parts) - 1
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or '']
                assert node.level <= depth + 1, (path, node.lineno)
            else:
                continue
            for name in names:
                assert not name.startswith('gene_annotation_episode.episodic_workflow.root'), (path, name)


def test_final_to_parent_returns_credit_finding_and_every_selectable_fact_and_the_form_admits_it():
    from ..messages.final_to_parent import RETURN_FORM, final_to_parent
    handoff = {'execution_id': 'job_1', 'monitor_operation': 'm', 'results_operation': 'r'}
    receipts = [{'outcome': {'facts': {'command': {'returncode': 0}, 'requested_job': {'handoff': handoff}}}},
                {'outcome': {'facts': {'command': {'returncode': 1}}}}]
    summary = {'assignment': {'endpoint': 'usable_handoff', 'completion_keys': ['handoff']}, 'receipts': receipts,
               'receipt_refs': ['receipt_1', 'receipt_2'], 'execution_completion': {'proof': 1},
               'execution_progress': {'satisfied_keys': ['handoff']}}
    selection = [name for name, spec in RETURN_FORM.fields.items() if not spec.required]
    result = final_to_parent(summary, {'credit': 1.5}, selection)
    assert result['execution_handoff_refs'] == ['receipt_1'] and result['execution_completed'] is True
    assert result['finding']['failed_command_count'] == 1 and result['finding']['completion'] == {'proof': 1}
    assert RETURN_FORM.admit(result, 'return') == result
