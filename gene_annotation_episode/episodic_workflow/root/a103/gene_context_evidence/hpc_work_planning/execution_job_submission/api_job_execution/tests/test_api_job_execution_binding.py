"""Real checks of the API job execution binding: importing ``episode.py`` runs the system's class-definition
checks, the folder holds exactly the ten-file set (no children, so no ``msg_to_child.py`` or
``read_from_child.py``), and no module imports another episode folder."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.'
          'execution_job_submission.api_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py'}
EPISODE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'


def folder_files():
    found = set()
    for path in FOLDER.rglob('*'):
        relative = path.relative_to(FOLDER)
        if '__pycache__' in relative.parts or relative.parts[0] == 'tests' or path.is_dir():
            continue
        found.add(relative.as_posix())
    return found


def test_the_class_passes_the_definition_checks():
    episode = importlib.import_module(MODULE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = importlib.import_module(MODULE + '.goal')
    assert classes[0].binding_path == goal.BINDING_PATH
    assert MODULE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert dict(classes[0].child_slots) == {}


def test_the_folder_holds_exactly_the_ten_file_set():
    assert folder_files() == FILES


def test_no_module_imports_another_episode_folder():
    own = MODULE
    for relative in sorted(folder_files()):
        tree = ast.parse((FOLDER / relative).read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                if name.startswith(EPISODE_PACKAGE):
                    assert name == own or name.startswith(own + '.'), (relative, name)
            if isinstance(node, ast.ImportFrom) and node.level > 1:
                raise AssertionError((relative, 'relative import above the episode folder'))


def test_the_assignment_admits_both_old_assignment_versions_and_the_return_declares_credit_and_finding():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    service_job = {'version': 'api_service_assignment', 'resource_id': 'blast', 'service': 'ncbi_blast',
                   'request': {'program': 'blastp'}, 'endpoint': 'usable_handoff', 'constraints': {},
                   'completion_target': 1.0}
    hmmer = {'version': 'api_execution_assignment', 'resource_id': 'hmmer', 'service': 'ebi_hmmer',
             'subject_ref': 'sub_1', 'algorithm': 'phmmer', 'database': 'pdb', 'parameters': {}, 'page_size': 10,
             'endpoint': 'usable_handoff', 'constraints': {}, 'completion_target': 1.0, 'input_refs': ['sub_1']}
    for assignment in (service_job, hmmer):
        admitted = from_parent.ASSIGNMENT_FORM.admit(assignment, 'assignment')
        assert from_parent.read_from_parent(admitted, {'purpose': 'x'})['version'] == assignment['version']
    assert final.RETURN_FORM.fields['credit'].required and final.RETURN_FORM.fields['finding'].required
    assert not final.RETURN_FORM.fields['execution_blast_hsps'].required


def test_final_to_parent_returns_credit_finding_and_every_selectable_fact_and_the_form_admits_it():
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    summary = {'service': 'ncbi_blast', 'resource_id': 'ncbi_blast', 'handoff_established': True,
               'submission_outcome': 'accepted', 'request_identity': None, 'job_identity': 'RID1',
               'handoff_refs': ['row_a'], 'result_refs': [], 'execution_completed': False, 'facts': {}}
    selection = [name for name, spec in final.RETURN_FORM.fields.items() if not spec.required]
    result = final.final_to_parent(summary, {'credit': 1.5}, selection)
    assert result['credit'] == 1.5 and result['execution_handoff_refs'] == ['row_a']
    assert result['finding'] == {**result['finding'], 'job_identity': 'RID1', 'handoff_established': True}
    assert 'request_identity' not in result['finding'] and result['execution_result_origin'] == {}
    assert final.RETURN_FORM.admit(result, 'return') == result
