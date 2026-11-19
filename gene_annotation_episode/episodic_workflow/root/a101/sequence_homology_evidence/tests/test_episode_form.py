"""The episode's form: importing ``episode.py`` runs the class-definition checks of the system, the class inherits
only ``EpisodeBinding``, the folder holds exactly the ten-file set (plus its child episode folders and tests), and
no module of the folder imports another episode folder."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence'
FOLDER = Path(__file__).resolve().parents[1]
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py'}
MESSAGES = {'__init__.py', 'read_from_parent.py', 'msg_to_child.py', 'read_from_child.py', 'internal_summary.py',
            'final_to_parent.py'}
CHILDREN = ('execution_job_submission', 'execution_progress_assessment', 'execution_result_acquisition',
            'published_evidence_assessment', 'resource_result_acquisition', 'resource_work_submission')


def names(folder):
    return {path.name for path in folder.iterdir() if path.name != '__pycache__'}


def test_episode_class_passes_the_class_definition_checks():
    episode = importlib.import_module(PACKAGE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    assert classes[0].binding_path == 'sequence_homology_evidence'
    assert set(classes[0].child_slots.values()) == {'sequence_homology_evidence/' + name for name in CHILDREN} | {
        'sequence_homology_evidence'}


def test_folder_holds_exactly_the_ten_files():
    assert names(FOLDER) == FILES | {'messages', 'tests', *CHILDREN}
    assert names(FOLDER / 'messages') == MESSAGES


def imports(path, package):
    tree = ast.parse(path.read_text())
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ''
            if node.level:
                parts = package.split('.')
                parts = parts[:len(parts) - node.level + 1]
                base = '.'.join([*parts, *([node.module] if node.module else [])])
            found.append(base)
            found.extend(base + '.' + alias.name for alias in node.names)
    return found


def test_no_module_imports_another_episode_folder():
    root = 'gene_annotation_episode.episodic_workflow.root'
    for path in list(FOLDER.glob('*.py')) + list((FOLDER / 'messages').glob('*.py')):
        package = PACKAGE if path.parent == FOLDER else PACKAGE + '.messages'
        for name in imports(path, package):
            if name.startswith(root):
                assert name == PACKAGE or name.startswith(PACKAGE + '.') and not any(
                    name.startswith(PACKAGE + '.' + child) for child in CHILDREN), (path.name, name)


def test_the_return_carries_the_credit_the_finding_and_every_selectable_field():
    final = importlib.import_module(PACKAGE + '.messages.final_to_parent')
    target = {'evidence_type': 'native_correspondence_aggregate', 'algorithm_count': 1, 'algorithms_agree': False,
              'comparison_count': 0, 'distinct_reference_count': 0, 'region_count': 1, 'uncovered_region_count': 1,
              'uncertainty_kind': 'native_evalue', 'uncertainty_sampling_basis': 'native_search_space',
              'function_specific_assessed': False, 'blast_component': 0.0}
    summary = {'committed_record_refs': ['art_1'], 'handoff_refs': ['hand_1'], 'axis_findings': [target],
               'child_reports': [{'slot': 'execution_job_submission', 'credit': 2.0, 'finding': {},
                                  'record_refs': ['hand_1'], 'handoff_refs': ['hand_1']}]}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 1.5}
    every = tuple(name for name in final.RETURN_FORM.fields if name not in ('credit', 'finding'))
    result = final.final_to_parent(summary, completion, every)
    final.RETURN_FORM.admit(result, 'return')
    assert result['credit'] == 1.5 and result['finding']['targets'] == [target]
    assert result['finding']['outstanding_handoff_count'] == 1
    assert result['committed_record_refs'] == ['art_1'] and result['execution_handoff_refs'] == ['hand_1']
    final.RETURN_FORM.admit(final.final_to_parent(summary, completion, ()), 'return')
