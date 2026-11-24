"""The commission of the search child with one written query (carried from the old
``to_child_source_relevance_assessment.py``, role ``literature_search``).

The old ``prepare_request`` validated the child scope, expanded the report contract form from the fact sources the
child binding required, checked the initial report against the interpretation schema, checked the role against the
allowed children, materialized the launch instructions and let the child binding's ``prepare_assignment`` build the
child's assignment from the model's search assignment. Here the child declares what it returns and this commission
selects the fact sources it wants (the old fact-source names); the assignment is the child's ``search_assignment``:
the records that give the question its context, the ONE query as ``search_query_ref`` (the reference of the record of
this episode that holds the query its model wrote: no query text travels between episodes), the one task with its
credit unit, the proposed annotation, the scope and every record this episode names for the child: the question
context, the query record and the proposed annotation. Nothing is checked here: a commission the child does not admit
fails, and a record this episode does not hold fails the run. The child's scope is this episode's own (the old
model-selected sub-scope is not carried). The answer the parent counts is the dispositions of the leads."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
# No text passes: the objective is fixed by the slot and the message is empty (controlled messaging).
OBJECTIVE = 'assess_returned_sources'


def msg_to_child(slot, arguments, summary):
    query_ref = arguments['search_query_ref']
    context = summary['strategy']['question_context_refs']
    received = [*context, query_ref, summary['proposed_annotation_ref']]
    assignment = {'version': 'search_assignment', 'question_context_refs': context,
                  'search_query_ref': query_ref, 'literature_task': summary['task'],
                  'proposed_annotation_ref': summary['proposed_annotation_ref'], 'scope': summary['scope'],
                  'received_record_refs': list(dict.fromkeys(received))}
    return ChildMessage(objective=OBJECTIVE, message={}, assignment=assignment, selection=(LEADS,))
