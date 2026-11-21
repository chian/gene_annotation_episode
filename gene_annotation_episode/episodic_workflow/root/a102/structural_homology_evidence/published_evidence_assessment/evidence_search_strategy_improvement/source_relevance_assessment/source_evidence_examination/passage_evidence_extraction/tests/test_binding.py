"""The real checks of this episode's binding: importing ``episode.py`` runs the class-definition checks; the folder
holds exactly the ten-file set of an episode without children; no module imports another episode folder; the
episode's own forms, credit and controller behave on real data. Nothing here is faked."""
import ast
import importlib
from pathlib import Path

import pytest

from episode_runtime import EpisodeBinding
from method_loop import FormError
from yield_control import AccumulationYieldController, CompletionYieldController

PACKAGE = __name__.rsplit('.', 2)[0]
FOLDER = Path(__file__).resolve().parents[1]
EPISODE = importlib.import_module(PACKAGE + '.episode').PassageEvidenceExtraction
FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
         'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
         'messages/final_to_parent.py', 'tests/__init__.py', 'tests/test_binding.py'}
ROOT = 'gene_annotation_episode.episodic_workflow.root'
PAGE = {'version': 'page_assignment_v1', 'source_ref': 'src_1', 'representation': 'text', 'artifact_ref': 'art_1',
        'question_context_refs': [], 'prior_delivery_refs': []}
WINDOW = {'source_ref': 'src_1', 'representation': 'text', 'offset': 0, 'limit': 10}
SCREENING_TASK = {'version': 'literature_local_task_v1', 'evidence_axis': 'A105', 'kind': 'source_answer',
                  'answer_kind': 'screening', 'credit_unit': 2.0,
                  'examined': [{'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 0, 'end': 100}]}
LEADS_TASK = {'version': 'literature_local_task_v1', 'evidence_axis': 'A105', 'kind': 'verified_source_leads',
              'credit_unit': 1.0}
ASSIGNMENT = {'version': 'reading_assignment_v1', 'page': PAGE, 'selection': {'spans': [WINDOW]},
              'literature_task': SCREENING_TASK, 'proposed_annotation_ref': 'hyp_1',
              'scope': {'subject_refs': ['sub_1']}, 'received_record_refs': ['src_1', 'art_1', 'hyp_1']}


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


def test_the_commission_form_admits_a_reading_assignment_and_refuses_an_unknown_field():
    form = EPISODE.assignment_form
    admitted = form.admit(ASSIGNMENT, 'test')
    parent_input = EPISODE.read_from_parent(admitted, {'objective': 'read'})
    assert parent_input['spans'] == [WINDOW] and parent_input['page'] == PAGE
    assert parent_input['task_key'] == 'A105:source_answer:screening'
    assert set(form.record_refs(admitted)) >= {'src_1', 'art_1', 'hyp_1'}
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**ASSIGNMENT, 'extra': 1}, 'test')
    other = {**admitted, 'selection': {'spans': [{**WINDOW, 'source_ref': 'src_2'}]}}
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        EPISODE.read_from_parent(other, {})
    with pytest.raises(ValueError, match='literature_original_task_invalid'):
        EPISODE.read_from_parent({**admitted, 'literature_task': {**SCREENING_TASK, 'kind': 'other'}}, {})


def test_the_return_declares_credit_and_finding_as_required_and_the_fact_sources_as_selectable():
    form = EPISODE.return_form
    assert form.fields['credit'].required and form.fields['finding'].required
    for name in ('literature_screening_answers', 'literature_source_lead_dispositions'):
        assert not form.fields[name].required


def test_the_return_carries_credit_the_finding_and_each_selectable_field_as_counts_and_references():
    span = {'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 0, 'end': 100, 'representation': 'text'}
    summary = {'structure_sheets': [], 'no_applicable_evidence': [span],
               'screening_answers': [{'proposed_annotation_ref': 'hyp_1', 'disposition': 'no_applicable_evidence',
                                      'examined': [span], 'annotation_support': 'not_assessed'}],
               'source_lead_dispositions': [{'source_ref': 'src_1', 'disposition': 'relevant',
                                             'relevance_rationale': 'model text that never leaves the episode'},
                                            {'source_ref': 'src_2', 'disposition': 'not_relevant'}]}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 2.5}
    names = ('literature_screening_answers', 'literature_source_lead_dispositions')
    result = EPISODE.final_to_parent(summary, completion, names)
    assert result == {'credit': 2.5, 'finding': {'structure_sheets': []},
                      'literature_screening_answers': {'examined_span_count': 1, 'commissioned_spans_covered': True},
                      'literature_source_lead_dispositions': {'relevant_lead_count': 1, 'lead_source_refs': ['src_1']}}
    form = EPISODE.return_form.select(names)
    form.admit(result, 'return')
    assert form.record_refs(form.admit(result, 'return')) == ('src_1',)
    with pytest.raises(FormError, match='unknown_field'):
        form.admit({**result, 'literature_source_lead_dispositions': {
            **result['literature_source_lead_dispositions'], 'relevance_rationale': 'text'}}, 'return')
    with pytest.raises(FormError, match='must_be_integer'):
        form.admit({**result, 'literature_screening_answers': {'examined_span_count': '1',
                                                               'commissioned_spans_covered': True}}, 'return')
    uncovered = EPISODE.final_to_parent({**summary, 'screening_answers': []}, completion, names)
    assert uncovered['literature_screening_answers']['commissioned_spans_covered'] is False
    plain = EPISODE.final_to_parent(summary, completion, ())
    assert set(plain) == {'credit', 'finding'}
    EPISODE.return_form.select(()).admit(plain, 'return')


def test_the_screening_credit_is_the_unit_when_the_own_declarations_cover_every_requested_span():
    summary = {'task': SCREENING_TASK, 'task_key': 'A105:source_answer:screening', 'proposed_annotation_ref': 'hyp_1',
               'no_applicable_evidence': [{'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 0, 'end': 60,
                                           'representation': 'text'}]}
    assert EPISODE.credit(summary, None) == 0
    summary['no_applicable_evidence'].append({'source_ref': 'src_1', 'artifact_ref': 'art_1', 'start': 50,
                                              'end': 100, 'representation': 'text'})
    assert EPISODE.credit(summary, None) == 2.0
    credit_source = (FOLDER / 'credit.py').read_text()
    assert 'NotImplementedError' not in credit_source and 'min(' not in credit_source


def test_the_controller_follows_the_commissioned_task_kind():
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.1}}
    leads = EPISODE.yield_controller(0, settings, {'task': LEADS_TASK})
    screening = EPISODE.yield_controller(0, settings, {'task': SCREENING_TASK})
    assert isinstance(leads, AccumulationYieldController)
    assert isinstance(screening, CompletionYieldController)


def test_the_model_is_offered_the_access_tools_structure_grading_and_reasoning_and_every_tool_is_declared():
    task = importlib.import_module(PACKAGE + '.task')
    names = task.offered({'tool_registry': {}})
    assert 'execution_estimate' not in names and names[-2:] == ['structure_populate', 'reason'] and len(names) == 16
    assert set(names) <= set(EPISODE.tools)


def test_the_selection_schema_and_its_strict_transport_build_for_every_offered_tool():
    task = importlib.import_module(PACKAGE + '.task')
    summary = {'task': LEADS_TASK, 'input_list': [[0, 10]], 'literature_assignment': {'page': PAGE},
               'reasoning_schema': {'type': 'object', 'properties': {'terms': {'type': 'array'}},
                                                         'required': ['terms'], 'additionalProperties': False}}
    names = task.offered({'tool_registry': {}})
    schema = task.selection_schema(names, summary)
    assert len(schema['properties']['selection']['anyOf']) == len(names)
    assert task.generation_schema(schema)
    reason = [entry for entry in task.catalog(names, summary) if entry['name'] == 'reason'][0]
    assert 'source_lead' in reason['input_schema']['required']


def test_the_input_list_shrinks_as_passages_are_examined_or_yield_a_lead():
    summary_file = importlib.import_module(PACKAGE + '.messages.internal_summary')
    spans = [WINDOW, {**WINDOW, 'offset': 20, 'limit': 10}]
    examined = {'source_ref': 'src_1', 'representation': 'text', 'start': 0, 'end': 4}
    assert summary_file.remaining_windows(spans, [], []) == [[0, 10], [20, 30]]
    assert summary_file.remaining_windows(spans, [examined], []) == [[4, 10], [20, 30]]
    assert summary_file.remaining_windows(spans, [{**examined, 'end': 10}], []) == [[20, 30]]
    lead = {'witness': {'source_ref': 'src_1', 'representation': 'text', 'start': 21, 'end': 25}}
    assert summary_file.remaining_windows(spans, [{**examined, 'end': 10}], [lead]) == []
    task = importlib.import_module(PACKAGE + '.task')
    summary = {'input_list': [[4, 10]], 'literature_assignment': {'page': PAGE}}
    windows = task.processing_schema(summary)['properties']['examined']['items']['anyOf']
    assert len(windows) == 1 and windows[0]['properties']['start']['minimum'] == 4
