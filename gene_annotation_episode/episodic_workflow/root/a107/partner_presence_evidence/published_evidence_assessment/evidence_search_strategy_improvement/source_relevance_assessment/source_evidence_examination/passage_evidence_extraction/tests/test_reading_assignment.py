"""The reading assignment the episode admits and what it reads from it (real form, no runner)."""
import copy

import pytest

from method_loop import FormError

from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.messages.read_from_parent import ASSIGNMENT_FORM, read_from_parent
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.messages.final_to_parent import RETURN_FORM

SOURCE = 'source_' + 'a' * 24
ARTIFACT = 'artifact_' + 'b' * 24
ASSIGNMENT = {
    'version': 'reading_assignment_v1',
    'page': {'version': 'page_assignment_v1', 'source_ref': SOURCE, 'representation': 'text',
             'artifact_ref': ARTIFACT, 'question_context_refs': [], 'prior_delivery_refs': []},
    'selection': {'spans': [{'source_ref': SOURCE, 'representation': 'text', 'offset': 10, 'limit': 200},
                            {'source_ref': SOURCE, 'representation': 'text', 'offset': 900, 'limit': 50}]},
    'held_refs': [SOURCE, ARTIFACT], 'scope': {'subject_refs': []}, 'finding_unit': 1.0}


def test_the_assignment_is_admitted_and_read_with_its_spans_kept_separate():
    admitted = ASSIGNMENT_FORM.admit(ASSIGNMENT, 'assignment')
    parent_input = read_from_parent(admitted, {})
    assert [span['offset'] for span in parent_input['spans']] == [10, 900]
    assert list(ASSIGNMENT_FORM.record_refs(admitted)) == [SOURCE, ARTIFACT]


def test_a_span_of_another_source_fails():
    assignment = copy.deepcopy(ASSIGNMENT)
    assignment['selection']['spans'][1]['source_ref'] = 'source_' + 'c' * 24
    with pytest.raises(ValueError, match='literature_reading_source_mismatch'):
        read_from_parent(ASSIGNMENT_FORM.admit(assignment, 'assignment'), {})


def test_an_unknown_assignment_field_fails():
    with pytest.raises(FormError):
        ASSIGNMENT_FORM.admit({**ASSIGNMENT, 'spans': []}, 'assignment')


def test_credit_and_finding_cannot_be_selected():
    assert set(RETURN_FORM.select(()).fields) == {'credit', 'finding'}
    with pytest.raises(FormError):
        RETURN_FORM.select(('credit',))


def test_the_return_carries_credit_and_the_controlled_sheet_features_and_the_form_admits_it():
    from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.messages.final_to_parent import final_to_parent
    counts = {'matched_sheet_count': 0, 'matched_loss_sheet_count': 0, 'distinct_experiment_count': 0}
    result = final_to_parent({'partner_sheets': [], 'partner_agreement': counts},
                             {'ended_by': 'yield_stop', 'units_consumed': 1, 'credit': 0.5}, ())
    assert result == {'credit': 0.5, 'finding': {'partner_sheets': [], **counts}}
    RETURN_FORM.admit(result, 'return')


def test_the_input_list_shrinks_as_spans_are_read_and_a_consumed_read_is_refused():
    import importlib
    base = ('gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.published_evidence_assessment'
            '.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination'
            '.passage_evidence_extraction')
    summary = importlib.import_module(base + '.messages.internal_summary')
    task = importlib.import_module(base + '.task')
    spans = ASSIGNMENT['selection']['spans']
    read = {'tool': 'source_read', 'outcome': {'status': 'completed', 'result': {
        'source_ref': SOURCE, 'representation': 'text', 'start': 0, 'end': 300}}}
    assert summary.input_list(spans, []) == ([], spans)
    assert summary.input_list(spans, [read]) == (spans[:1], spans[1:])
    state = {'literature_assignment': {'page': ASSIGNMENT['page']}, 'processed_spans': spans[:1]}
    assert task.consumed_read({'source_ref': SOURCE, 'offset': 20, 'limit': 50}, state)
    assert not task.consumed_read({'source_ref': SOURCE, 'offset': 900, 'limit': 50}, state)
