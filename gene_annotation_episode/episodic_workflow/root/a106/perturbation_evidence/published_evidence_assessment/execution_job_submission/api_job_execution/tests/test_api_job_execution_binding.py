"""Real checks of the API job execution binding: importing ``episode.py`` runs the system's class-definition
checks, the folder holds exactly the ten-file set (no children, so no ``msg_to_child.py`` or
``read_from_child.py``), and no module imports another episode folder."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.published_evidence_assessment.'
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


def test_the_assignment_admits_the_old_assignment_and_the_return_declares_credit_and_finding():
    from_parent = importlib.import_module(MODULE + '.messages.read_from_parent')
    final = importlib.import_module(MODULE + '.messages.final_to_parent')
    assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'bvbrc', 'service': 'bvbrc_appservice',
                  'request': {'application': 'RNASeq'}, 'endpoint': 'usable_handoff', 'constraints': {},
                  'completion_target': 1.0, 'input_refs': ['sub_1']}
    admitted = from_parent.ASSIGNMENT_FORM.admit(assignment, 'assignment')
    parent_input = from_parent.read_from_parent(admitted, {'purpose': 'x'})
    assert parent_input['version'] == 'api_service_assignment_v1'
    assert parent_input['completion_target'] == 1.0
    assert final.RETURN_FORM.fields['credit'].required and final.RETURN_FORM.fields['finding'].required
    assert not final.RETURN_FORM.fields['execution_result_refs'].required


def test_the_return_gives_credit_finding_and_every_selectable_fact_and_is_admitted():
    episode = importlib.import_module(MODULE + '.episode')
    cls = [value for value in vars(episode).values()
           if isinstance(value, type) and value.__module__ == episode.__name__][0]
    summary = {'service': 'bvbrc_appservice', 'resource_id': 'bvbrc', 'handoff_established': True,
               'submission_outcome': 'submitted', 'request_identity': None, 'job_identity': 'job_1',
               'facts_by_source': {'execution_handoff_refs': ['row_1'], 'execution_completed': True,
                                   'execution_result_refs': [], 'bvbrc_appservice_support_refs': ['sup_1'],
                                   'bvbrc_application_outcomes': []}}
    selection = ('execution_result_refs', 'bvbrc_appservice_support_refs', 'bvbrc_application_outcomes')
    result = cls.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 2.0}, selection)
    assert result['credit'] == 2.0 and result['finding']['job_identity'] == 'job_1'
    assert 'request_identity' not in result['finding']
    assert result['execution_handoff_refs'] == ['row_1'] and result['execution_completed'] is True
    assert result['execution_result_refs'] == [] and result['bvbrc_appservice_support_refs'] == ['sup_1']
    cls.return_form.admit(result, 'return')
    cls.return_form.select(selection).admit(result, 'return')
