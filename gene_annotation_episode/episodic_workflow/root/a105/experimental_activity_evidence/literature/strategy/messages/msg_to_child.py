"""The commission: what this episode sends its one child, the search level: ONE query by reference
(``search_query_ref``: the record of this episode that holds the query the model wrote with ``write_search``; the
query text never travels, the child reads the record through custody), with this episode's question context, the one
task, the proposed annotation, the persisted sheet states, the articles already examined, the scope and the records.

The parent states what the child takes in its own text and schema (``task.py``) and builds the child's assignment
here. Nothing is checked against the child: a selection the child does not declare, an assignment its form does not
admit or a record this episode does not hold fails the run where the child is built (rule 1).

Selection (rule 5): what the one task needs back: the persisted sheet states (the next run starts from them), the
articles its pages examined (the next run does not fetch them again) and ``literature_source_lead_dispositions``.

Records (decision T5): the commission names every record this episode holds (its passed records and what it produced
or was returned)."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
SHEET_STATE_REFS = 'sheet_state_refs'
EXAMINED = 'examined_article_refs'


def msg_to_child(slot, arguments, summary):
    if slot != 'web_search':
        raise LookupError('no_such_child_slot:' + slot)
    assignment = {'version': 'search_assignment_v1',
                  'question_context_refs': summary['strategy']['question_context_refs'],
                  'search_query_ref': arguments['search_query_ref'],
                  'literature_task': summary['task'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  SHEET_STATE_REFS: list(summary['sheet_state_refs']),
                  EXAMINED: list(summary['all_examined_article_refs']), 'scope': summary['scope'],
                  'received_record_refs': list(summary['held_record_refs'])}
    return ChildMessage(objective=arguments['objective'],
                        message={'objective': arguments['objective'], 'task_key': summary['task_key']},
                        assignment=assignment, selection=(SHEET_STATE_REFS, EXAMINED, LEADS))
