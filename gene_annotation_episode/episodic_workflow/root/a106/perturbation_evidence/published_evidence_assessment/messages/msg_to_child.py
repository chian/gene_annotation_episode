"""The commission of this episode's one child, the search strategy investigation (carried from the old
``to_child_evidence_search_strategy_improvement.py``, role ``literature_strategy``).

The old ``prepare_*`` validated the child scope, expanded the report contract form from the fact sources the child
binding required, checked the initial report against the interpretation schema, checked the role against the allowed
children, checked the binding path and let the child binding's ``prepare_assignment`` build the child's assignment
from the model's assignment. Here the child declares what it returns and this commission selects the fact sources it
wants (the old fact-source names); the assignment is the child's own: nothing is checked here, a commission the child
does not admit fails, and a record this episode does not hold fails the run. The child's scope is this episode's own
(the old model-selected sub-scope is not carried).

``literature_strategy``: the child's ``strategy_assignment_v1``: the records that give the question its context, the
one task with this commission's own credit unit (where the old private yield binding filled it), the proposed
annotation, the scope and every record this episode names for the child: the question context and the proposed
annotation. No prior search and no source is passed: a strategy writes its searches itself, and a paper reaches the
chain only through a search. The answer the parent counts is the dispositions of the leads."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
# No text passes: the objective is fixed by the slot and the message is empty (controlled messaging).
OBJECTIVE = 'improve_search_strategy'


def strategy(arguments, summary):
    task = {**arguments['literature_task'], 'credit_unit': summary['task']['credit_unit']}
    received = [*arguments['question_context_refs'], summary['proposed_annotation_ref']]
    assignment = {'version': 'strategy_assignment_v1', 'question_context_refs': arguments['question_context_refs'],
                  'literature_task': task, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  'scope': summary['scope'], 'received_record_refs': list(dict.fromkeys(received))}
    return assignment, (LEADS,)


COMMISSIONS = {'literature_strategy': strategy}


def msg_to_child(slot, arguments, summary):
    assignment, selection = COMMISSIONS[slot](arguments, summary)
    return ChildMessage(objective=OBJECTIVE, message={}, assignment=assignment, selection=selection)
