"""Where the extraction stands, from the loop's view: the commission (the page, the task, the proposed annotation, the
scope), the input list (nano-graphrag: a leaf's input units are consumed, not re-read) and the chunk of the next unit.

``input_list`` holds the commissioned chunks not yet extracted, as ``[offset, end]`` pairs in the order commissioned: after k
extractions it is ``spans[k:]``, and each extraction takes the first and removes it, whatever its outcome (an ``invalid``
outcome of the route is a returned outcome and consumes its chunk as the yield controller counts it). The chunk of this unit
is the first of that list (``chunk``: its text, read through custody from the artifact of the page; ``offset``; ``limit``);
with the list empty there is no chunk. ``sheet_refs`` are the perturbation sheets the completed extractions saved and
``lead_source_refs`` the verified sources: the page source once a sheet was saved. ``a106_findings`` are the controlled
features of the A106 grading sheets this episode saved (code reads them from the sheets)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_leaf_extraction import (
    saved_sheet_refs, window_text)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_a106_findings import (
    own_findings)


def internal_summary(view):
    parent = view.parent_input
    page, task = parent['page'], parent['task']
    extracted = [outcome for outcome in view.outcomes if outcome['kind'] == 'tool' and outcome['tool'] == 'extract']
    remaining = parent['spans'][len(extracted):]
    current = {'offset': None, 'limit': None, 'chunk': None}
    if remaining:
        first = remaining[0]
        current = {'offset': first['offset'], 'limit': first['limit'],
                   'chunk': window_text(view.records, page, first['offset'], first['limit'])}
    sheets = saved_sheet_refs(view.outcomes)
    return {
        **current,
        'input_list': [[span['offset'], span['offset'] + span['limit']] for span in remaining],
        'page': page, 'task': task, 'proposed_annotation_ref': parent['proposed_annotation_ref'],
        'scope': parent['scope'], 'received_record_refs': parent['received_record_refs'],
        'literature_assignment': {'version': 'reading_assignment', 'page': page,
                                  'selection': {'spans': parent['spans']}, 'literature_task': task,
                                  'proposed_annotation_ref': parent['proposed_annotation_ref']},
        'sheet_refs': sheets, 'lead_source_refs': [page['source_ref']] if sheets else [],
        'a106_findings': own_findings(view.records, view.outcomes),
        'units_consumed': view.units_consumed,
    }
