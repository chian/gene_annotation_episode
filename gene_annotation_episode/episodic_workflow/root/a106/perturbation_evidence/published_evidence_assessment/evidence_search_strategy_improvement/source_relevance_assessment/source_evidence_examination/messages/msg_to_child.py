"""The commissions of the three leaf investigations of the examined paper (``literature_table``, ``literature_ordered``,
``literature_targeted``). Each is handed input units of the page's candidate list (``messages/internal_summary.py``):

- ``literature_table``: the one table region candidate the model selected (its byte window);
- ``literature_targeted``: the one prose chunk candidate the model selected (its byte window);
- ``literature_ordered``: the first window of the remaining prose, in document order (``report_windows``).

The model selects only unconsumed candidates (the selection schema of ``task.py`` names no other), and a candidate handed
to a leaf is consumed (``internal_summary.consumed_candidates``). The leaf's assignment is its own
``reading_assignment_v1``: the page of this paper, the window, the commissioned task, the proposed annotation, the scope
and every record this episode names for the child. Nothing is checked here: a commission the child does not admit fails.

No text passes: the objective of each leaf is fixed by its slot and the message is empty (controlled messaging)."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
OBJECTIVES = {'literature_table': 'investigate_selected_table', 'literature_ordered': 'read_source_in_order',
              'literature_targeted': 'investigate_selected_passages'}


def window(summary, start, end):
    """A byte window of the assigned paper in its assigned representation (the child's WINDOW shape)."""
    page = summary['page']
    return {'source_ref': page['source_ref'], 'representation': page['representation'], 'offset': start,
            'limit': end - start}


def selection_of(slot, arguments, summary):
    """The reading the leaf is handed, built from the input list (``summary['content_candidates']``)."""
    candidates = {item['candidate_id']: item for item in summary['content_candidates']}
    if slot == 'literature_table':
        item = candidates[arguments['candidate_id']]
        return window(summary, item['start'], item['end'])
    if slot == 'literature_targeted':
        item = candidates[arguments['candidate_id']]
        return {'spans': [window(summary, item['start'], item['end'])]}
    start, end = summary['report_windows'][0]
    return {'spans': [window(summary, start, end)]}


def msg_to_child(slot, arguments, summary):
    assignment = {'version': 'reading_assignment_v1', 'page': summary['page'],
                  'selection': selection_of(slot, arguments, summary), 'literature_task': summary['task'],
                  'proposed_annotation_ref': summary['proposed_annotation_ref'], 'scope': summary['scope'],
                  'received_record_refs': list(summary['received_record_refs'])}
    return ChildMessage(objective=OBJECTIVES[slot], message={}, assignment=assignment, selection=(LEADS,))
