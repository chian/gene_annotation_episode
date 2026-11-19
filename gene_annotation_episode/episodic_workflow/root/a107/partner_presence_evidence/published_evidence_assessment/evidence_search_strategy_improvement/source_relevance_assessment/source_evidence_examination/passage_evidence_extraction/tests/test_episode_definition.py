"""The class definition of the passage evidence extraction episode, over the real source (no fake, no runner).

Importing `episode.py` runs the system's class-definition checks, so the import is the check."""
import ast
import importlib
from pathlib import Path

from episode_runtime import EpisodeBinding

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction'
FOLDER = Path(__file__).resolve().parents[1]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def test_class_definition_passes_and_inherits_only_the_episode_type():
    episode = importlib.import_module(PACKAGE + '.episode')
    classes = [value for value in vars(episode).values()
               if isinstance(value, type) and value.__module__ == episode.__name__]
    assert len(classes) == 1
    assert classes[0].__bases__ == (EpisodeBinding,)
    goal = importlib.import_module(PACKAGE + '.goal')
    assert PACKAGE.endswith(goal.BINDING_PATH.replace('/', '.'))
    assert classes[0].binding_path == goal.BINDING_PATH
    assert classes[0].child_slots == {}
    assert not hasattr(classes[0], 'msg_to_child') and not hasattr(classes[0], 'read_from_child')


def test_folder_holds_exactly_the_ten_file_set():
    files = {path.relative_to(FOLDER).as_posix() for path in FOLDER.rglob('*')
             if path.is_file() and '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert files == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if 'tests' in path.relative_to(FOLDER).parts or '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert node.level <= 1 if path.parent == FOLDER else node.level <= 2, (path, node.module)
                assert 'episodic_workflow.root' not in (node.module or ''), (path, node.module)
            elif isinstance(node, ast.Import):
                assert not any('episodic_workflow.root' in alias.name for alias in node.names), path
