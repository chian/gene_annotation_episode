"""The commission: what this episode sends its one child, the page: ONE paper, the source reference of the paper the
picked hit names (``source_ref``; code obtained it, or it was already held), its ``representation`` and ``artifact_ref``
(filled by code from the source record, ``internal_summary.page_of``), with this episode's question context, the one
task, the proposed annotation, the persisted sheet states, the scope and the records.

The page's objective is one fixed value of the page's own vocabulary, ``evidence_location_unknown``: the search has not
read the paper, so it does not know whether the paper holds an experiment, let alone where (that is what the page and
the leaves below it find out). No model-written text reaches the page.

The parent states what the child takes in its own text and schema (``task.py``) and builds the child's assignment
here. Nothing is checked against the child: a selection the child does not declare, an assignment its form does not
admit or a record this episode does not hold fails the run where the child is built (rule 1).

Selection (rule 5): what the one task needs back: the persisted sheet states (the next page starts from them) and
``literature_source_lead_dispositions``.

Records (decision T5): the commission names every record this episode holds (its passed records and what it produced
or was returned)."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
SHEET_STATE_REFS = 'sheet_state_refs'
OBJECTIVE = 'evidence_location_unknown'


def child_page(arguments, summary):
    """The child's page: the paper, its representation and artifact, with this episode's question context."""
    page = arguments['page']
    return {'source_ref': page['source_ref'], 'representation': page['representation'],
            'artifact_ref': page['artifact_ref'], 'question_context_refs': summary['search']['question_context_refs'],
            'prior_delivery_refs': page['prior_delivery_refs']}


def msg_to_child(slot, arguments, summary):
    if slot != 'page':
        raise LookupError('no_such_child_slot:' + slot)
    assignment = {'version': 'page_assignment', **child_page(arguments, summary),
                  'literature_task': summary['task'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                  SHEET_STATE_REFS: list(summary['sheet_state_refs']),
                  'scope': summary['scope'], 'received_record_refs': list(summary['held_record_refs'])}
    return ChildMessage(objective=OBJECTIVE,
                        message={'objective': OBJECTIVE, 'task_key': summary['task_key']},
                        assignment=assignment, selection=(SHEET_STATE_REFS, LEADS))
