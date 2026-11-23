"""The commissions: what this episode sends each of its three leaf children. Each is handed ONE input unit of the page's
candidate list (``messages/internal_summary.py``) of this episode's own paper, in the representation it was commissioned:

- ``table_evidence_extraction``: the one table region the model selected (its byte window);
- ``passage_evidence_extraction``: the one prose chunk the model selected (its byte window);
- ``source_coverage_improvement``: the remaining prose in document order, as one window from the first remaining prose
  window to the end of the last.

The model selects only unconsumed candidates (the selection schema of ``task.py`` names no other), and a candidate handed
to a leaf is consumed (``internal_summary.consumed_candidates``). The objective is the fixed one below: whether the
candidate holds an organism-context observation is what the leaf finds out, so neither the page nor its model states one.
Nothing is checked against the child: a selection the child does not declare, an assignment its form does not admit or a
record this episode does not hold fails the run where the child is built.

Selection: the relevant source-lead answer, and the cells of the requested A108 component families for the leaves that
declare cells (the passage leaf declares none and is given no requested components). A leaf returns its cells as the
references of their rows; the features of every sheet it saved are in its finding."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
GRADING_CELLS = 'literature_a108_grading_cells'
AGGREGATION_CELLS = 'literature_a108_aggregation_cells'
REQUESTED_GRADING = 'requested_a108_grading_components'
REQUESTED_AGGREGATION = 'requested_a108_aggregation_components'
CELLS_FROM = ('table_evidence_extraction', 'source_coverage_improvement')
OBJECTIVE = 'find_applicable_evidence'


def selected_fields(slot, assignment):
    """The selectable fields of the leaf's return this commission wants."""
    selection = [LEADS]
    if slot in CELLS_FROM:
        if assignment.get(REQUESTED_GRADING):
            selection.append(GRADING_CELLS)
        if assignment.get(REQUESTED_AGGREGATION):
            selection.append(AGGREGATION_CELLS)
    return tuple(selection)


def window_of(summary, start, end):
    page = summary['page']
    return {'source_ref': page['source_ref'], 'representation': page['representation'], 'offset': start,
            'limit': end - start}


def selection_of(slot, arguments, summary):
    """The window (or spans) the leaf's form takes: the candidate's bytes, or the remaining prose windows in document
    order, each one a span the coverage leaf extracts once."""
    if slot == 'source_coverage_improvement':
        return {'spans': [window_of(summary, start, end) for start, end in summary['report_windows']]}
    candidate = {item['candidate_id']: item for item in summary['content_candidates']}[arguments['candidate_id']]
    window = window_of(summary, candidate['start'], candidate['end'])
    return {'spans': [window]} if slot == 'passage_evidence_extraction' else window


def msg_to_child(slot, arguments, summary):
    assignment = summary['literature_assignment']
    page = summary['page']
    child = {'version': 'reading_assignment', 'page': page, 'selection': selection_of(slot, arguments, summary),
             'literature_task': summary['task'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
             **{name: assignment[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION)
                if slot in CELLS_FROM and assignment.get(name)},
             'scope': summary['scope'],
             'received_record_refs': list(dict.fromkeys(
                 [*summary['received_record_refs'], *page['question_context_refs'], *page['prior_delivery_refs']]))}
    return ChildMessage(objective=OBJECTIVE, message={'scope': summary['scope']}, assignment=child,
                        selection=selected_fields(slot, assignment))
