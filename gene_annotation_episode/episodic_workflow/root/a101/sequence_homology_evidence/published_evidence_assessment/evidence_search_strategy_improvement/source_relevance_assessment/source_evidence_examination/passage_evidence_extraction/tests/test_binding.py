"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set; no module imports another episode folder; the episode's own forms and functions
behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def test_the_class_inherits_only_the_episode_type_and_is_its_own_binding():
    assert EPISODE.__bases__ == (EpisodeBinding,)
    assert EPISODE.binding_path == importlib.import_module(PACKAGE + '.goal').BINDING_PATH
    assert PACKAGE.endswith(EPISODE.binding_path.replace('/', '.'))
    assert dict(EPISODE.child_slots) == {}


def test_the_folder_holds_exactly_the_ten_files_of_an_episode_without_children():
    assert files() == FILES
    assert not (FOLDER / 'messages' / 'msg_to_child.py').exists()
    assert not (FOLDER / 'messages' / 'read_from_child.py').exists()


def test_no_module_of_the_folder_imports_another_episode_folder():
    own = PACKAGE
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == own or module.startswith(own + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_a_reading_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    page = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1',
            'question_context_refs': [], 'prior_delivery_refs': []}
    window = {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10}
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': [window]},
                  'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1']}
    admitted = form.admit(assignment, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['spans'] == [window] and parent_input['page'] == page
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment, 'extra': 1}, 'test')
    other = {**admitted, 'selection': {'spans': [{**window, 'source_ref': 'src_2'}]}}
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent(other, {})


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    summary = {'report': None, 'report_source_held': {},
               'literature_assignment': {'page': {'source_ref': 's', 'representation': 'text'},
                                         'selection': {'spans': [{'source_ref': 's', 'representation': 'text'}]}}}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and result['finding']['written'] is False
    form.admit(result, 'test')


def test_the_credit_is_the_native_correspondence_projector_and_never_a_stub():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit
    assert credit_module.A101SequenceCredit().as_record()['kind'] == 'a101_native_sequence_correspondence'
    source = (FOLDER / 'credit.py').read_text()
    assert 'NotImplementedError' not in source


def test_the_model_is_offered_the_access_tools_and_the_report_and_every_tool_is_declared():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({})
    assert 'execution_estimate' not in names and names[-1] == 'report' and len(names) == 15
    assert set(names) <= set(EPISODE.tools)
    schema = task.selection_schema(names)
    assert len(schema['properties']['selection']['anyOf']) == len(names)
    assert 'execution_estimate' in task.offered({'tool_registry': {'native_statistics': object()}})
