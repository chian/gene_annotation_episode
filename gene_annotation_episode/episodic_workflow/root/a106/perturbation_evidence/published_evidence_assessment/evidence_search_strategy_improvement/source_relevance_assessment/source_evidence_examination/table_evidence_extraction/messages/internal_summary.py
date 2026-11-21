"""Where the extraction stands, from the loop's view: the commission (the page, the task, the proposed annotation, the
scope), the input list (nano-graphrag: a table region is consumed when it is selected) and the table's text.

``input_list`` holds the one table region of the commission, ``[[offset, offset + limit]]``, until it has been extracted once
(whatever the outcome of the population route: an ``invalid`` outcome is a returned outcome and consumes the region), and is
empty after that. ``table`` is its text, read through custody from the artifact of the page. ``sheet_refs`` are the
perturbation sheets the completed extractions saved and ``lead_source_refs`` the verified sources: the page source once a
sheet was saved. ``a106_findings`` are the controlled features of the A106 grading sheets this episode saved (code reads
them from the sheets)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_leaf_extraction import (
    saved_sheet_refs, window_text)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    own_findings)


def internal_summary(view):
    parent = view.parent_input
    page, task, window = parent['page'], parent['task'], parent['window']
    extracted = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == 'extract']
    sheets = saved_sheet_refs(view.outcomes)
    return {
        'offset': window['offset'], 'limit': window['limit'],
        'table': window_text(view.records, page, window['offset'], window['limit']),
        'input_list': [] if extracted else [[window['offset'], window['offset'] + window['limit']]],
        'page': page, 'task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_assignment': {'version': 'reading_assignment_v1', 'page': page, 'selection': window,
                                  'literature_task': task,
                                  'proposed_annotation_ref': parent['proposed_annotation_ref']},
        'sheet_refs': sheets, 'lead_source_refs': [page['source_ref']] if sheets else [],
        'a106_findings': own_findings(view.records, view.outcomes),
        'units_consumed': view.units_consumed,
    }
