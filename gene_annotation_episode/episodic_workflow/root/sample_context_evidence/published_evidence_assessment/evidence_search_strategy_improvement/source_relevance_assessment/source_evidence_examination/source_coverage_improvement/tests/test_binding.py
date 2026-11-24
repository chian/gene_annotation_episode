"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set; no module imports another episode folder; the episode's own forms and functions
behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py', 'tests/a108_world.py',
         'tests/test_context_grading.py', 'tests/test_model_run.py'}
SOURCE = 'source_' + 'a' * 24
ARTIFACT = 'artifact_' + 'a' * 24
ROOT = 'gene_annotation_episode.episodic_workflow.root'
TASK = {'kind': 'verified_source_leads', 'evidence_axis': 'A108', 'credit_unit': 1.0,
        'version': 'literature_local_task'}
FIRST = {'source_ref': SOURCE, 'representation': 'text', 'offset': 0, 'limit': 10}
SECOND = {'source_ref': SOURCE, 'representation': 'text', 'offset': 10, 'limit': 10}


def files():
    return {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def assignment(task=TASK, spans=(FIRST, SECOND)):
    page = {'version': 'page_assignment', 'source_ref': SOURCE, 'representation': 'text', 'artifact_ref': ARTIFACT,
            'question_context_refs': [], 'prior_delivery_refs': []}
    return {'version': 'reading_assignment', 'page': page, 'selection': {'spans': list(spans)},
            'literature_task': task, 'proposed_annotation_ref': 'hyp_1', 'scope': {'subject_refs': ['sub_1']},
            'received_record_refs': [SOURCE, ARTIFACT]}


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


def test_the_commission_admits_the_windows_in_order_and_refuses_what_is_not_the_commission():
    form = EPISODE.assignment_form
    admitted = form.admit(assignment(), 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['spans'] == [FIRST, SECOND] and parent_input['task_key'] == 'A108:verified_source_leads'
    assert set(form.record_refs(admitted)) == {SOURCE, ARTIFACT}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**assignment(), 'extra': 1}, 'test')
    other = {**admitted, 'selection': {'spans': [{**FIRST, 'source_ref': 'source_' + 'c' * 24}]}}
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent(other, {})
    backwards = {**admitted, 'selection': {'spans': [SECOND, FIRST]}}
    with pytest.raises(ValueError, match='literature_reading_windows_invalid'):
        EPISODE.read_from_parent(backwards, {})
    for kind in ({'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': [SOURCE]},
                 {'kind': 'source_answer', 'answer_kind': 'screening', 'examined': []}):
        wrong = {**admitted, 'literature_task': {**TASK, **kind}}
        with pytest.raises(ValueError, match='literature_original_task_invalid'):
            EPISODE.read_from_parent(wrong, {})


def test_the_return_declares_credit_and_finding_as_required_and_the_leads_and_cells_as_selectable():
    fields = EPISODE.return_form.fields
    assert fields['credit'].required and fields['finding'].required
    assert {name for name, spec in fields.items() if not spec.required} == {
        'literature_source_lead_dispositions', 'literature_a108_grading_cells'}
    assert fields['literature_a108_grading_cells'].type == 'record_refs'


def test_the_credit_counts_nothing_without_a_graded_sheet_and_the_ceiling_of_the_extraction_is_unbounded():
    credit_module = importlib.import_module(PACKAGE + '.credit')
    assert EPISODE.credit is credit_module.credit and EPISODE.ceiling is credit_module.ceiling
    summary = {'task': {**TASK, 'credit_unit': 2.0}, 'task_key': 'A108:verified_source_leads', 'source_leads': [],
               'proposed_annotation_ref': 'hyp_1', 'finding': {'grading_sheets': []}}
    assert credit_module.credit(summary, None) == 0
    assert credit_module.ceiling(summary, None, 'extract', None, None) == credit_module.UNBOUNDED
    assert credit_module.ceiling(summary, None, 'source_read', None, None) == 0.0


def test_the_controller_counts_the_windows_to_do():
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    controller = EPISODE.yield_controller(0, settings, {'task': TASK, 'spans': [FIRST, SECOND]})
    assert isinstance(controller, AccumulationYieldController) and controller.items == 2


def test_the_one_action_is_the_extraction_with_its_grading_and_source_lead():
    task = importlib.import_module(PACKAGE + '.task')
    commit_schema = {'type': 'object', 'additionalProperties': False, 'required': ['terms'],
                     'properties': {'terms': {'type': 'array'}}}
    assert list(EPISODE.tools) == ['extract'] == EPISODE.offered_actions({}, None)
    assert tuple(EPISODE.services) == ()
    library = importlib.import_module(
        'gene_annotation_episode.episodic_workflow.episode_support.literature.forms.sample_context_evidence.'
        'literature_leaf_extraction')
    schema = library.selection_schema(commit_schema)
    options = schema['properties']['selection']['anyOf']
    assert len(options) == 1 and options[0]['properties']['tool']['const'] == 'extract'
    arguments = options[0]['properties']['arguments']['properties']
    assert 'evidence_processing' in arguments and 'source_lead' in arguments
    assert library.empty_commit({'terms': []}, commit_schema) and not library.empty_commit({'terms': [{}]}, commit_schema)
    assert task.TEXT == 'window'


def test_the_segments_carry_the_exact_byte_offsets_of_the_text_shown():
    library = importlib.import_module(
        'gene_annotation_episode.episodic_workflow.episode_support.literature.forms.sample_context_evidence.'
        'literature_leaf_extraction')
    content = 'Methods. Strain QX-7 grew in 5 µM succinate. It did not grow without it.\nDiscussion. Done'.encode()
    segments = library.window_segments(content, 9, len(content))
    assert segments and segments[0]['text'].startswith('Strain QX-7')
    for segment in segments:
        assert content[segment['start']:segment['end']].decode() == segment['text']
