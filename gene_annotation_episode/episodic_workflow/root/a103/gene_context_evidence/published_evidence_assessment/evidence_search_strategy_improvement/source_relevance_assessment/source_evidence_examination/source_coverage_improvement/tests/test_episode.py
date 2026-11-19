"""The A103 source coverage improvement episode is a private binding in the ten-file form."""
import ast
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

from .. import episode as episode_module
from ..episode import SourceCoverageImprovement
from ..goal import BINDING_PATH
from ..messages.final_to_parent import RETURN_FORM
from ..messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent

FOLDER = Path(episode_module.__file__).parent
PACKAGE = episode_module.__name__.rsplit('.', 1)[0]
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}


def test_the_class_inherits_only_the_system_episode_type():
    assert SourceCoverageImprovement.__bases__ == (EpisodeBinding,)
    assert SourceCoverageImprovement.binding_path == BINDING_PATH
    assert dict(SourceCoverageImprovement.child_slots) == {}


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
             if path.is_file() and '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert found == TEN_FILES


def test_no_module_imports_another_episode_folder():
    for path in FOLDER.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level <= (1 if path.parent == FOLDER else 2) or 'tests' in path.parts, (path, node.module)
                modules = [node.module or '']
            for module in modules:
                assert '.episodic_workflow.root' not in module or module.startswith(PACKAGE), (path, module)


def _assignment(**changes):
    value = {'version': 'reading_assignment_v1',
             'page': {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text',
                      'artifact_ref': 'art_1', 'question_context_refs': [], 'prior_delivery_refs': []},
             'selection': {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10},
             'scope': {'subject_refs': ['sub_1']}, 'record_refs': ['src_1', 'art_1']}
    return {**value, **changes}


def test_the_assignment_form_admits_the_old_assignment_and_read_from_parent_reads_it():
    assignment = ASSIGNMENT_FORM.admit(_assignment(), 'assignment')
    parent_input = read_from_parent(assignment, 'message')
    assert parent_input['selection']['limit'] == 10


def test_the_assignment_form_refuses_an_unknown_field():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({**_assignment(), 'other': 1}, 'assignment')


def test_a_window_of_another_source_is_refused_where_the_assignment_is_read():
    window = {'source_ref': 'src_2', 'representation': 'text', 'offset': 0, 'limit': 10}
    assignment = ASSIGNMENT_FORM.admit(_assignment(selection=window), 'assignment')
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        read_from_parent(assignment, 'message')


def test_the_return_form_declares_credit_and_finding_as_required():
    required = {name for name, field in RETURN_FORM.fields.items() if field.required}
    assert {'credit', 'finding'} <= required
