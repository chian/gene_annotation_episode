"""The commission of the evidence search strategy improvement child. The parent states what the child takes in its own
assignment: the strategy assignment ``strategy_assignment`` (the records that give the question its context; no
search and no source is handed down), the commissioned literature task, the proposed annotation, the A108 components
the parent wants returned, the scope and the records the child reads.

Carried from the old ``to_child_evidence_search_strategy_improvement.py`` (child role ``literature_strategy``): the
child's assignment is the one this episode holds, unchanged. The old request carried the child scope (within the
parent scope) and the old expanded return contract is the ``selection`` of fields now; the model's only part of the
commission is its objective.

Records (decision T5, name every record the child reads): the question-context records, the proposed annotation and
the hypothesis and scope subjects the summary names, and the records the parent received for the task.

Selection: this episode returns the commissioned task's answer, so it asks the child for the source-lead dispositions
and, when its own assignment requests A108 components, for the cells of the requested families.

A commission that is wrong (a selection the child does not declare, a record this episode does not hold, a task the
child's form does not admit) raises in the child's form, in custody or here and fails the run: nothing here checks it."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
GRADING_CELLS = 'literature_a108_grading_cells'
AGGREGATION_CELLS = 'literature_a108_aggregation_cells'
REQUESTED_GRADING = 'requested_a108_grading_components'
REQUESTED_AGGREGATION = 'requested_a108_aggregation_components'


def selected_fields(task, assignment):
    """The selectable fields of the child's return this commission wants."""
    selection = [LEADS]
    if assignment.get(REQUESTED_GRADING):
        selection.append(GRADING_CELLS)
    if assignment.get(REQUESTED_AGGREGATION):
        selection.append(AGGREGATION_CELLS)
    return tuple(selection)


def msg_to_child(slot, arguments, summary):
    if slot != 'evidence_search_strategy_improvement':
        raise LookupError('no_such_child_slot:' + slot)
    assignment = summary['literature_assignment']
    child = {'version': 'strategy_assignment',
             'question_context_refs': assignment['question_context_refs'],
             'literature_task': summary['task'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
             **{name: assignment[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION)
                if assignment.get(name)},
             'scope': summary['scope'],
             'received_record_refs': list(dict.fromkeys([
                 *assignment['question_context_refs'],
                 summary['proposed_annotation_ref'], *summary['proposed_annotation_subject_refs'],
                 *summary['scope']['subject_refs'], *summary['received_record_refs']]))}
    return ChildMessage(objective=arguments['objective'], message={'scope': summary['scope']},
                        assignment=child, selection=selected_fields(summary['task'], assignment))
