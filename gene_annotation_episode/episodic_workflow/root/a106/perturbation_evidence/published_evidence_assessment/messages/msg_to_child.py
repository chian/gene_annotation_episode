"""The commissions of this episode's three children (carried from the old ``to_child_evidence_search_strategy_
improvement.py`` (role ``literature_strategy``), ``to_child_execution_job_submission.py`` (role ``launch``) and
``to_child_execution_result_acquisition.py`` (role ``results``)).

The old ``prepare_*`` validated the child scope, expanded the report contract form from the fact sources the child
binding required, checked the initial report against the interpretation schema, checked the role against the allowed
children (``analysis_children``: ``launch`` and ``results`` only when an execution binding was configured; that is
``task.offered_slots``), checked the binding path, materialized the launch instructions and let the child binding's
``prepare_assignment`` build the child's assignment from the model's assignment. Here each child declares what it
returns and this commission selects the fact sources it wants (the old fact-source names); the assignment is the
child's own: nothing is checked here, a commission the child does not admit fails, and a record this episode does
not hold fails the run. The child's scope is this episode's own (the old model-selected sub-scope is not carried).

``literature_strategy``: the child's ``strategy_assignment_v1`` (the records that give the question its context and
the earlier searches' sources the model chose, the literature task the model chose for it with this commission's own
credit unit, where the old private yield binding filled it, the proposed annotation, the scope and every record this
episode names for the child: the chosen sources with their artifacts (``summary['source_custody']``), the question
context and the proposed annotation).

``launch``: ``execution_launch_assignment_v1`` from the model's arguments, the scope of this episode and
``handoff_unit``, which ``task.action`` took from the settings. The model's ``input_refs`` are named for the child.
The handoff references the child returns (``execution_handoff_refs``, the old ``required_return_sources`` of a
launch) and whether it verified completion are selected.

``results``: ``execution_results_assignment_v1`` (the handoff, named in custody, the selector and the API service of
the original job, which the old ``prepare_assignment`` read through the original target). The retained result
records are always returned; the verified completion and the application observations are selected."""
from episode_runtime import ChildMessage

SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
HANDOFF = 'execution_handoff_refs'
COMPLETED = 'execution_completed'
APPLICATION_OUTCOMES = 'bvbrc_application_outcomes'


def strategy(arguments, summary):
    task = {**arguments['literature_task'], 'credit_unit': summary['task']['credit_unit']}
    # The answers the parent counts: dispositions of the leads of a leads commission (its credit counts them) and
    # the screening answer of a screening commission; an assessment answer is a Store record, not a fact source.
    selection = ((LEADS,) if task['kind'] == 'verified_source_leads'
                 else (SCREENING,) if task['answer_kind'] == 'screening' else ())
    received = [*arguments['question_context_refs'], summary['proposed_annotation_ref']]
    for source_ref in arguments['prior_search_refs']:
        received.extend(summary['source_custody'][source_ref])
    assignment = {'version': 'strategy_assignment_v1', 'question_context_refs': arguments['question_context_refs'],
                  'prior_search_refs': arguments['prior_search_refs'], 'literature_task': task,
                  'proposed_annotation_ref': summary['proposed_annotation_ref'], 'scope': summary['scope'],
                  'received_record_refs': list(dict.fromkeys(received))}
    return assignment, selection


def launch(arguments, summary):
    assignment = {'version': 'execution_launch_assignment_v1', 'requests': arguments['requests'],
                  'immutable_input_versions': arguments['immutable_input_versions'],
                  'constraints': arguments['constraints'], 'scope': summary['scope'],
                  'handoff_unit': arguments['handoff_unit']}
    if arguments.get('launch_instructions') is not None:
        assignment['launch_instructions'] = arguments['launch_instructions']
    if 'input_refs' in arguments:
        assignment['input_refs'] = arguments['input_refs']
    if 'already_handed_off_resource_ids' in arguments:
        assignment['already_handed_off_resource_ids'] = arguments['already_handed_off_resource_ids']
    return assignment, (HANDOFF, COMPLETED)


def results(arguments, summary):
    assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': [arguments['handoff_ref']],
                  'selector': arguments['selector'], 'service': arguments['service']}
    return assignment, (COMPLETED, APPLICATION_OUTCOMES)


COMMISSIONS = {'literature_strategy': strategy, 'launch': launch, 'results': results}
# No text passes: the objective is fixed by the slot and the message is empty (controlled messaging).
OBJECTIVES = {'literature_strategy': 'improve_search_strategy', 'launch': 'launch_execution_requests',
              'results': 'acquire_execution_results'}


def msg_to_child(slot, arguments, summary):
    assignment, selection = COMMISSIONS[slot](arguments, summary)
    return ChildMessage(objective=OBJECTIVES[slot], message={},
                        assignment=assignment, selection=selection)
