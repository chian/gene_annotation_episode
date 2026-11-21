"""The commissions: what this episode sends each of its three children. All three are leaf extractors of this episode's
own source in the representation it was commissioned, for one kind of experiment, and each is handed input units of the
page's candidate list (``messages/internal_summary.py``; nano-graphrag's page hands a table child its region and a report
child the remaining prose):

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


def msg_to_child(slot, arguments, summary):
    """The commission of a leaf (``source_ref``, ``passed_refs``, ``representation``, the input unit(s),
    ``experiment_type``, ``proposed_annotation_ref``); this episode groups the returned records into graders and scores
    them."""
    page = summary['page']
    assignment = {'source_ref': page['source_ref'], 'passed_refs': list(summary['held_record_refs']),
                  'representation': page['representation'], 'experiment_type': arguments['experiment_type'],
                  'proposed_annotation_ref': summary['proposed_annotation_ref']}
    if slot == 'report':
        assignment['windows'] = [list(window) for window in summary['report_windows']]
    else:
        candidate = {item['candidate_id']: item for item in summary['content_candidates']}[arguments['candidate_id']]
        assignment.update({'offset': candidate['start'], 'limit': candidate['end'] - candidate['start']})
    return ChildMessage(objective=arguments['objective'],
                        message={'objective': arguments['objective'], 'task_key': summary['task_key']},
                        assignment=assignment, selection=(LEAF_RECORDS,))
