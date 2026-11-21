"""The commission: what this episode sends its one child, carried from the old ``to_child_source_evidence_examination.py``
(``to_child``: the child's assignment is the one the model wrote, unchanged) and from the envelope the old model
wrote (``version``, ``page``, ``literature_task``, ``proposed_annotation_ref`` and the requested components), under
the old names.

The parent states what the child takes in its own text and schema (``task.py``) and builds the child's assignment
here: the page the model chose (``source_ref``, ``representation``, ``artifact_ref``, ``prior_delivery_refs``) with
this episode's question context, the commissioned task, the proposed annotation, the requested arrays of the cell
families selected, the scope and the records. Nothing is checked against the child: a selection the child does not
declare, an assignment its form does not admit or a record this episode does not hold fails the run where the child
is built (rule 1). The old ``to_child`` copied the assignment unchanged and so does this: the old task checks the
child made against its page (``literature_task_outside_assigned_source``) are the child's own.

Selection (rule 5): what the commissioned task needs back. ``literature_source_lead_dispositions`` for a
verified-source-leads task and ``literature_screening_answers`` for a screening answer.

Records (decision T5): the commission names every record the child's code reads. The old child inherited the
records its parent had received, through the receipt ledger; the new commission names every record this episode
holds (its passed records and what it produced or was returned)."""
from episode_runtime import ChildMessage

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
SHEET_STATE_REFS = 'sheet_state_refs'


def child_page(arguments, summary):
    """The old ``_PAGE``: the child's page, with this episode's question context and the deliveries of earlier
    examinations of the page the model named."""
    page = arguments['page']
    return {'source_ref': page['source_ref'], 'representation': page['representation'],
            'artifact_ref': page['artifact_ref'], 'question_context_refs': summary['search']['question_context_refs'],
            'prior_delivery_refs': page['prior_delivery_refs']}


def msg_to_child(slot, arguments, summary):
    if slot != 'page':
        raise LookupError('no_such_child_slot:' + slot)
    task = summary['task']
    selection = [SHEET_STATE_REFS]   # the page's persisted sheet states: the next page starts from them
    if task['kind'] == 'verified_source_leads':
        selection.append(LEADS)
    if task.get('answer_kind') == 'screening':
        selection.append(SCREENING)
    page = child_page(arguments, summary)
    assignment = {'version': 'page_assignment_v1', **page, 'literature_task': task,
                  'proposed_annotation_ref': summary['proposed_annotation_ref'], **summary['requested'],
                  SHEET_STATE_REFS: list(summary['sheet_state_refs']),
                  'scope': summary['scope'], 'received_record_refs': list(summary['held_record_refs'])}
    return ChildMessage(objective=arguments['objective'],
                        message={'objective': arguments['objective'], 'task_key': summary['task_key']},
                        assignment=assignment, selection=tuple(selection))
