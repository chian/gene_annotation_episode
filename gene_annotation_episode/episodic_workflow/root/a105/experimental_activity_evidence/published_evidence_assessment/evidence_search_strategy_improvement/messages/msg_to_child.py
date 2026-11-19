"""The commission: what this episode sends its one child, carried from the old ``to_child_source_relevance_assessment.py``
(``to_child``: the child's assignment is the one the model wrote, unchanged) and from the envelope the old model
wrote (``version``, ``question_context_refs``, ``search_result_refs``, ``literature_task``,
``proposed_annotation_ref`` and the requested components), under the old names.

The parent states what the child takes in its own text and schema (``task.py``) and builds the child's assignment
here: the search results the model chose (``search_result_refs``) with this episode's question context, the
commissioned task, the proposed annotation, the requested arrays of the cell families, the scope and the records.
Nothing is checked against the child: a selection the child does not declare, an assignment its form does not admit
or a record this episode does not hold fails the run where the child is built (rule 1). The old ``to_child`` copied
the assignment unchanged and so does this.

Selection (rule 5): what the commissioned task needs back. ``literature_source_lead_dispositions`` for a
verified-source-leads task and ``literature_screening_answers`` for a screening answer.

Records (decision T5): the commission names every record the child's code reads. The old child inherited the
records its parent had received, through the receipt ledger; the new commission names every record this episode
holds (its passed records and what it produced or was returned)."""
from episode_runtime import ChildMessage

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'


def msg_to_child(slot, arguments, summary):
    if slot != 'source_relevance_assessment':
        raise LookupError('no_such_child_slot:' + slot)
    task = summary['task']
    selection = []
    if task['kind'] == 'verified_source_leads':
        selection.append(LEADS)
    if task.get('answer_kind') == 'screening':
        selection.append(SCREENING)
    assignment = {'version': 'search_assignment_v1',
                  'question_context_refs': summary['strategy']['question_context_refs'],
                  'search_result_refs': arguments['search']['search_result_refs'],
                  'literature_task': task, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  **summary['requested'], 'scope': summary['scope'],
                  'received_record_refs': list(summary['held_record_refs'])}
    return ChildMessage(objective=arguments['objective'],
                        message={'objective': arguments['objective'], 'task_key': summary['task_key']},
                        assignment=assignment, selection=tuple(selection))
