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
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py', 'tests/a106_world.py',
         'tests/test_input_list.py', 'tests/test_a106_grading.py', 'tests/test_model_run.py'}
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


def test_the_episode_has_the_one_action_extract_and_no_reasoning_commit_or_read_tool():
    assert set(EPISODE.tools) == {'extract'}


def test_the_commission_form_admits_ordered_windows_and_refuses_what_is_not_a_leaf_commission():
    form = EPISODE.assignment_form
    page = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1',
            'question_context_refs': [], 'prior_delivery_refs': []}
    first = {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10}
    second = {**first, 'offset': 10}
    task = {'kind': 'verified_source_leads', 'evidence_axis': 'A106', 'credit_unit': 1.0}
    assignment = {'version': 'reading_assignment_v1', 'page': page, 'selection': {'spans': [first, second]},
                  'literature_task': task, 'proposed_annotation_ref': 'hyp_1',
                  'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1']}
    admitted = form.admit(assignment, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['spans'] == [first, second] and parent_input['page'] == page
    assert EPISODE.yield_controller(0.0, {}, parent_input).items == 2
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment, 'extra': 1}, 'test')
    with pytest.raises(ValueError, match='literature_reading_windows_not_in_document_order'):
        EPISODE.read_from_parent({**admitted, 'selection': {'spans': [second, first]}}, {})
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent({**admitted, 'selection': {'spans': [{**first, 'source_ref': 'src_2'}]}}, {})
    answer_task = {**task, 'kind': 'source_answer', 'answer_kind': 'screening', 'examined': []}
    with pytest.raises(ValueError, match='literature_original_task_invalid'):
        EPISODE.read_from_parent({**admitted, 'literature_task': answer_task}, {})


def test_the_return_declares_credit_and_finding_as_required_and_returns_the_systems_credit():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    assert set(form.fields) == {'credit', 'finding', 'literature_source_lead_dispositions', 'record_refs'}
    summary = {'a106_findings': {'intervention_assessments': [], 'a106_subscores': []},
               'lead_source_refs': ['src_1'], 'sheet_refs': ['src_9']}
    both = ('literature_source_lead_dispositions', 'record_refs')
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 2.5}, both)
    assert result['credit'] == 2.5 and result['finding'] == summary['a106_findings']
    assert result['literature_source_lead_dispositions'] == {'relevant_lead_count': 1, 'lead_source_refs': ['src_1']}
    form.select(both).admit(result, 'return')
    assert EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.0}, ()) == {
        'credit': 0.0, 'finding': summary['a106_findings']}


def test_the_credit_is_real_code_and_counts_the_one_verified_source():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit and EPISODE.ceiling is credit_module.ceiling
    assert 'NotImplementedError' not in (FOLDER / 'credit.py').read_text()
    summary = {'task': {'kind': 'verified_source_leads', 'credit_unit': 2.0}, 'lead_source_refs': []}
    assert credit_module.credit(summary, None) == 0
    assert credit_module.ceiling(summary, None, 'extract', None, None) == 2.0
    assert credit_module.ceiling(summary, None, 'reason', None, None) == 0.0
    summary['lead_source_refs'] = ['src_1']
    assert credit_module.credit(summary, None) == 2.0
    assert credit_module.ceiling(summary, None, 'extract', None, None) == 0.0
