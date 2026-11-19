"""Real checks of the source coverage improvement binding: importing ``episode.py`` runs the system's
class-definition checks, the folder holds exactly the ten-file set, and no module imports another episode."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

MODULE = ('gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.'
          'published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.'
          'source_evidence_examination.source_coverage_improvement')
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


def test_the_return_carries_the_credit_and_the_finding_and_is_admitted_by_the_return_form():
    module = importlib.import_module(MODULE + '.messages.final_to_parent')
    completion = {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.5}
    report = {'entries': [{'source_ref': 'src_1', 'claim_kind': 'reported_family_assignment',
                           'subject_relation': 'family_member', 'measured': False, 'offset': 0, 'limit': 100,
                           'function': 'PF00001'}]}
    written = module.final_to_parent({'report': report}, completion, ())
    assert written['credit'] == 0.5 and written['finding']['written'] is True
    finding = module.RETURN_FORM.admit(written, 'return')['finding']
    assert finding['claim_count_reported_family_assignment'] == 1
    assert finding['entries'][0] == {'source_refs': ['src_1'], 'claim_kind': 'reported_family_assignment',
                                     'subject_relation': 'family_member', 'measured': False, 'offset': 0,
                                     'limit': 100, 'function': 'PF00001'}
    unwritten = module.final_to_parent({'report': None}, completion, ())
    assert unwritten['finding']['written'] is False
    module.RETURN_FORM.admit(unwritten, 'return')
