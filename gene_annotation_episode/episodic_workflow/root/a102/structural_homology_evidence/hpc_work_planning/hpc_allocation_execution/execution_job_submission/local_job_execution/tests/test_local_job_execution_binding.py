"""The episode is a private binding in the final ten-file form: importing ``episode.py`` runs the system's class
definition checks, the folder holds exactly the ten-file set, and no module of it imports another episode."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.hpc_work_planning.'
           'hpc_allocation_execution.execution_job_submission.local_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py'}


def test_the_class_passes_the_definition_checks_and_inherits_only_the_episode_type():
    episode = importlib.import_module(PACKAGE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    assert classes[0].child_slots == {}


def test_the_folder_holds_exactly_the_ten_file_set():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py') if '__pycache__' not in path.parts}
    assert {name for name in found if not name.startswith('tests/')} == FILES - {'tests/__init__.py'}
    assert not (FOLDER / 'messages' / 'msg_to_child.py').exists()
    assert not (FOLDER / 'messages' / 'read_from_child.py').exists()


def test_no_module_of_the_folder_imports_another_episode_folder():
    root = 'gene_annotation_episode.episodic_workflow.root'
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            assert not [name for name in names if name == root or name.startswith(root + '.')], (path, names)


def test_a_commissioned_assignment_gives_its_completion_controller_its_target_and_profile():
    """The real assignment form, ``read_from_parent``, the real credit projection and the real controller."""
    from yield_control import CompletionYieldController
    episode = importlib.import_module(PACKAGE + '.episode')
    credit = importlib.import_module(PACKAGE + '.credit')
    cls = episode.LocalJobExecution
    assignment = {
        'version': 'practical_assignment_v1', 'assignment_id': 'a1', 'resource_id': 'workstation',
        'resource_kind': 'local', 'workspace': '/work/job', 'endpoint': 'usable_handoff',
        'requested_job': {'argv': ['/bin/true'], 'environment': {}},
        'progress_requirements': [
            {'key': 'cwd', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': '/work/job'}},
            {'key': 'handoff', 'credit': 3.0, 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': '/work/job', 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {}, 'scope': {'subject_refs': []}}
    admitted = cls.assignment_form.admit(assignment, 'assignment')
    parent = cls.read_from_parent(admitted, {})
    assert parent['completion_target'] == 4.0
    assert parent['yield_class'] == 'practical_local_handoff'
    initial = credit.credit({'assignment': parent['assignment'], 'initial_validations': parent['initial_validations'],
                             'receipts': []}, None)
    assert initial == 1.0   # the starting working directory already satisfies the cwd requirement
    settings = {'task_yield_profiles': {'launch_local:practical_local_handoff':
                                        {'cutoff': 0.5, 'parameters': {'uncertainty_alpha': 0.05}}}}
    controller = cls.yield_controller(initial, settings, parent)
    assert isinstance(controller, CompletionYieldController) and controller.target == 4.0


def test_the_final_return_carries_the_completion_credit_and_the_real_handoff_finding():
    """The real ``final_to_parent`` on the real projection of a commissioned assignment before any command ran."""
    episode = importlib.import_module(PACKAGE + '.episode')
    summary_module = importlib.import_module(PACKAGE + '.messages.internal_summary')
    final = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    cls = episode.LocalJobExecution
    assignment = {
        'version': 'practical_assignment_v1', 'assignment_id': 'a1', 'resource_id': 'workstation',
        'resource_kind': 'local', 'workspace': '/work/job', 'endpoint': 'usable_handoff',
        'requested_job': {'argv': ['/bin/true'], 'environment': {}},
        'progress_requirements': [
            {'key': 'cwd', 'credit': 1.0, 'predicate': {'kind': 'context_cwd', 'path': '/work/job'}},
            {'key': 'handoff', 'credit': 3.0, 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': '/work/job', 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {}, 'scope': {'subject_refs': []}}
    parent = cls.read_from_parent(cls.assignment_form.admit(assignment, 'assignment'), {})
    progress = summary_module.project_practical_credit(parent['assignment'], parent['initial_validations'], [])
    assert summary_module.completion_proof(parent['assignment'], parent['initial_validations'], []) is None
    assert summary_module.selected_execution_task(parent) is None
    summary = {'assignment': parent['assignment'], 'completion_target': parent['completion_target'],
               'execution_progress': progress, 'execution_completion': None, 'requested_job': None,
               'receipts': [], 'receipt_refs': [], 'receipt_artifact_refs': []}
    result = final.final_to_parent(summary, {'credit': 1.0, 'ended_by': 'controller', 'units_consumed': 0},
                                   ['execution_handoff_refs'])
    assert result['credit'] == 1.0
    assert result['finding']['completed'] is False and result['finding']['satisfied_keys'] == ['cwd']
    assert result['execution_handoff_refs'] == [] and result['practical_receipt_digests'] == []
