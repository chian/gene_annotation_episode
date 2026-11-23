"""The commission of the page child on the ONE paper the model picked (carried from the old
``to_child_source_evidence_examination.py``, role ``literature_page``).

The old ``prepare_request`` validated the child scope, expanded the report contract form from the fact sources the
child binding required, checked the initial report against the interpretation schema, checked the role against the
allowed children, materialized the launch instructions and let the child binding's ``prepare_assignment`` build the
child's assignment from the model's page assignment. Here the child declares what it returns and this commission
selects the fact sources it wants (the old fact-source names); the assignment is the child's ``page_assignment``:
the one paper (``source_ref``) with its representation and that representation's artifact, which code filled from the
source record when the page was built (``messages/internal_summary.py``, ``page_of``), the records that give the
question its context, no earlier delivery (the paper was just obtained), the one task with its credit unit, the proposed
annotation, the scope and every record this episode names for the child: the paper and its artifacts, the question
context and the proposed annotation. The model writes none of it. Nothing is checked here: a commission the child does
not admit fails, and a record this episode does not hold fails the run. The child's scope is this episode's own (the
old model-selected sub-scope is not carried). The answer the parent counts is the dispositions of the leads."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
# No text passes: the objective is fixed by the slot and the message is empty (controlled messaging).
OBJECTIVE = 'examine_selected_source'


def msg_to_child(slot, arguments, summary):
    page = arguments['page']
    context = summary['search']['question_context_refs']
    received = [*page['custody'], *context, summary['proposed_annotation_ref']]
    assignment = {'version': 'page_assignment', 'source_ref': page['source_ref'],
                  'representation': page['representation'], 'artifact_ref': page['artifact_ref'],
                  'question_context_refs': context, 'prior_delivery_refs': page['prior_delivery_refs'],
                  'literature_task': summary['task'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  'scope': summary['scope'], 'received_record_refs': list(dict.fromkeys(received))}
    return ChildMessage(objective=OBJECTIVE, message={}, assignment=assignment, selection=(LEADS,))
