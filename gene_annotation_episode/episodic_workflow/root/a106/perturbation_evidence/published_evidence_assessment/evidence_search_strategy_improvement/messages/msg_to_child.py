"""The commission of the source relevance assessment of returned sources (carried from the old
``to_child_source_relevance_assessment.py``, role ``literature_search``).

The old ``prepare_request`` validated the child scope, expanded the report contract form from the fact sources the
child binding required, checked the initial report against the interpretation schema, checked the role against the
allowed children, materialized the launch instructions and let the child binding's ``prepare_assignment`` build the
child's assignment from the model's search assignment. Here the child declares what it returns and this commission
selects the fact sources it wants (the old fact-source names); the assignment is the child's
``search_assignment_v1``: the records that give the question its context and the returned sources the model chose,
the literature task the model chose for the search (its credit unit is this commission's own, where the old private
yield binding filled it), the proposed annotation, the scope and every record this episode names for the child: the
chosen sources with their artifacts (``summary['source_custody']``), the question context and the proposed
annotation. Nothing is checked here: a commission the child does not admit fails, and a source this episode does not
hold fails the run. The child's scope is this episode's own (the old model-selected sub-scope is not carried)."""
from episode_runtime import ChildMessage

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
# No text passes: the objective is fixed by the slot and the message is empty (controlled messaging).
OBJECTIVE = 'assess_returned_sources'


def msg_to_child(slot, arguments, summary):
    task = {**arguments['literature_task'], 'credit_unit': summary['task']['credit_unit']}
    # The answers the parent counts: dispositions of the leads of a leads commission (its credit counts them) and
    # the screening answer of a screening commission; an assessment answer is a Store record, not a fact source.
    selection = ((LEADS,) if task['kind'] == 'verified_source_leads'
                 else (SCREENING,) if task['answer_kind'] == 'screening' else ())
    received = [*arguments['question_context_refs'], summary['proposed_annotation_ref']]
    for source_ref in arguments['search_result_refs']:
        received.extend(summary['source_custody'][source_ref])
    assignment = {'version': 'search_assignment_v1', 'question_context_refs': arguments['question_context_refs'],
                  'search_result_refs': arguments['search_result_refs'], 'literature_task': task,
                  'proposed_annotation_ref': summary['proposed_annotation_ref'], 'scope': summary['scope'],
                  'received_record_refs': list(dict.fromkeys(received))}
    return ChildMessage(objective=OBJECTIVE, message={},
                        assignment=assignment, selection=selection)
