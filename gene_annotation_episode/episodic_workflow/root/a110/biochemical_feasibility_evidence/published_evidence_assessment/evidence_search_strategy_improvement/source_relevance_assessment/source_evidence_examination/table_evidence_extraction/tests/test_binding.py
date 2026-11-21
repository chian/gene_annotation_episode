"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set; no module imports another episode folder; the episode's own forms and functions
behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding, Rejected, ToolCall
from method_loop import FormError

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').TableEvidenceExtraction
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
FEATURES_MODULE = importlib.import_module('gene_annotation_episode.episodic_workflow.episode_support.findings.'
                                          'biochemical_feasibility_evidence.investigation_finding_features')
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py',
         'tests/test_reaction_grading.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
PAGE = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'original', 'artifact_ref': 'art_1',
        'question_context_refs': [], 'prior_delivery_refs': []}
TABLE = {'kind': 'table', 'source_ref': 'src_1', 'sheet_key': 'Sheet1', 'offset': 0, 'limit': 20, 'header_row': 1,
         'where': {'column': 'B', 'match': 'contains', 'value': 'ATP', 'case_sensitive': False}}
WINDOW = {'kind': 'window', 'source_ref': 'src_1', 'representation': 'original', 'offset': 0, 'limit': 10}
ASSIGNMENT = {'version': 'reading_assignment_v1', 'page': PAGE, 'selection': TABLE,
              'scope': {'subject_refs': ['sub_1']}, 'finding_unit': 2.0, 'received_record_refs': ['src_1', 'art_1']}


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
    for path in FOLDER.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) and not node.level else [])
            for module in modules:
                assert not module.startswith(ROOT) or module == PACKAGE or module.startswith(PACKAGE + '.'), \
                    str(path.relative_to(FOLDER)) + ' imports ' + module


def test_the_commission_form_admits_a_table_and_a_window_selection_and_refuses_the_rest():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['selection'] == TABLE and parent_input['finding_unit'] == 2.0
    assert set(form.record_refs(admitted)) == {'src_1', 'art_1'}
    window = form.admit({**ASSIGNMENT, 'selection': WINDOW}, 'test')
    assert EPISODE.read_from_parent(window, {})['selection'] == WINDOW
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent({**admitted, 'selection': {**TABLE, 'source_ref': 'src_2'}}, {})
    with pytest.raises(ValueError, match='literature_reading_representation_mismatch'):
        EPISODE.read_from_parent({**window, 'selection': {**WINDOW, 'representation': 'text'}}, {})
    with pytest.raises(ValueError, match='explicit_positive_finding_unit_required'):
        EPISODE.read_from_parent({**admitted, 'finding_unit': 0}, {})


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    features = FEATURES_MODULE.validate_features({
        'retained_finding_count': 0, 'count_by_evidence_type': dict.fromkeys(FEATURES_MODULE.EVIDENCE_TYPE_VALUES, 0),
        'strengthening_count': 0, 'weakening_count': 0, 'mixed_or_nondiscriminating_count': 0, 'direct_count': 0,
        'qualified_count': 0, 'independent_source_count': 0, 'uncertainty_reported_count': 0, 'controlled_count': 0,
        'arm_agreement': 'none', 'inactive_count_by_reason': dict.fromkeys(FEATURES_MODULE.INACTIVE_REASONS, 0),
        'finding_refs': [], 'finding_record_refs': []})
    summary = {'investigation_finding': features, 'reaction_sheets': []}
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}, ())
    assert result['credit'] == 2.5 and result['finding']['reaction_sheets'] == []
    assert form.admit(result, 'test') == result
    text_fields = [name for name, spec in FINAL.FINDING_FORM.fields.items() if spec.type == 'text']
    assert all(hasattr(FINAL.FINDING_FORM.fields[name], 'options') for name in text_fields)



def test_the_model_is_offered_the_access_tools_the_reaction_graders_and_the_reasoning_and_every_tool_is_declared():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({})
    assert 'report' not in EPISODE.tools and {'source_xlsx_sheets', 'source_xlsx_rows'} <= set(names)
    assert names[-3:] == ['literature_reaction_populate', 'literature_reaction_source_populate', 'reason']
    assert len(names) == 17 and set(names) <= set(EPISODE.tools)


def test_the_input_list_is_the_unread_selection_and_a_consumed_read_is_rejected():
    inputs = importlib.import_module('gene_annotation_episode.episodic_workflow.episode_support.literature.readers.'
                                     'gene_context_evidence.literature_selection_input_list')
    read = {'kind': 'tool', 'tool': 'source_read', 'outcome': {'status': 'completed'},
            'arguments': {'arguments': {'source_ref': 'src_1', 'representation': 'original', 'offset': 2, 'limit': 3}}}
    assert inputs.selection_input_list(WINDOW, []) == [[0, 10]]
    assert inputs.selection_input_list(WINDOW, [read]) == [[0, 2], [5, 10]]
    consumed = inputs.consumed_extents(WINDOW, [read])
    assert inputs.already_read(WINDOW, consumed, 'source_read',
                               {'source_ref': 'src_1', 'representation': 'original', 'offset': 3, 'limit': 1})
    assert not inputs.already_read(WINDOW, consumed, 'source_read',
                                   {'source_ref': 'src_1', 'representation': 'original', 'offset': 4, 'limit': 3})
