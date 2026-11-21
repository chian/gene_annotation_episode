"""The commissions: what this episode sends each of its three children. All three are leaf extractors of this episode's
own paper in the representation it was commissioned, with the sheet class of the claim (the leaf names the method it
finds; the page names no experiment type), and each is handed input units of the page's candidate list
(``messages/internal_summary.py``):

- ``chunk``: the one prose chunk candidate the model selected (its byte offset and length);
- ``table``: the one table region candidate the model selected (its byte offset and length);
- ``report``: every remaining prose chunk, as the windows of ``report_windows`` in document order (``windows``).

The model selects only unconsumed candidates (the selection schema of ``task.py`` names no other), and a candidate handed
to a child is consumed (``internal_summary.consumed_candidates``). Nothing is checked against the child: a selection the
child does not declare, an assignment its form does not admit or a record this episode does not hold fails the run where
the child is built (rule 1).

Selection (rule 5): each leaf declares ``record_refs`` (its immutable leaf records) and no other optional field, so
``record_refs`` is the whole selection; credit and finding are always returned.

Records (decision T5): the commission names every record the child's code reads: every record this episode holds (its
passed records and what it produced or was returned)."""
from episode_runtime import ChildMessage

LEAF_RECORDS = 'record_refs'   # the selectable field of the leaves' return form
OBJECTIVE = 'find_applicable_evidence'   # whether the candidate holds an experiment or result is what the leaf finds out


def msg_to_child(slot, arguments, summary):
    page = summary['page']
    assignment = {'source_ref': page['source_ref'], 'passed_refs': list(summary['held_record_refs']),
                  'representation': page['representation'], 'sheet_class': summary['sheet_class'],
                  'proposed_annotation_ref': summary['proposed_annotation_ref']}
    if slot == 'report':
        assignment['windows'] = [list(window) for window in summary['report_windows']]
    else:
        candidate = {item['candidate_id']: item for item in summary['content_candidates']}[arguments['candidate_id']]
        assignment.update({'offset': candidate['start'], 'limit': candidate['end'] - candidate['start']})
    return ChildMessage(objective=OBJECTIVE,
                        message={'objective': OBJECTIVE, 'task_key': summary['task_key']},
                        assignment=assignment, selection=(LEAF_RECORDS,))
