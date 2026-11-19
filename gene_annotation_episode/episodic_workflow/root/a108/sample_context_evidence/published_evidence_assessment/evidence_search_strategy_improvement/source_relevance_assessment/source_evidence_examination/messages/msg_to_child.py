"""The commissions of the three children. The parent states what each child takes in its own assignment: the reading
assignment ``reading_assignment_v1`` (this page, the selection the model chose, the commissioned literature task, the
proposed annotation, the A108 components the parent wants returned, the scope and the records the child reads).
Carried from the old ``to_child_table_evidence_extraction.py`` (child role ``literature_table``),
``to_child_source_coverage_improvement.py`` (``literature_ordered``) and ``to_child_passage_evidence_extraction.py``
(``literature_targeted``): the three differed only in the role string. The old request carried the child scope (within
the parent scope), the commissioned task and the proposed annotation, and ``episode_assignment`` was the child
binding's ``prepare_assignment``; the old expanded return contract is the ``selection`` of fields now.

Selection: this episode returns the commissioned task's answers, so it asks each child for the answer that task needs
(source-lead dispositions, screening answers) and, when its own assignment requests A108 components, for the cells of
the requested families; the passage child declares no cells and is given no requested components. A child returns cells as the references of their rows; the features of every sheet it saved are in its finding.

A commission that is wrong (a selection the child does not declare, a record this episode does not hold, a selection
the child's form does not admit) raises in the child's form or in custody and fails the run: nothing here checks it."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
SCREENING = 'literature_screening_answers'
GRADING_CELLS = 'literature_a108_grading_cells'
AGGREGATION_CELLS = 'literature_a108_aggregation_cells'
REQUESTED_GRADING = 'requested_a108_grading_components'
REQUESTED_AGGREGATION = 'requested_a108_aggregation_components'
CELLS_FROM = ('table_evidence_extraction', 'source_coverage_improvement')


def selected_fields(slot, task, parent):
    """The selectable fields of the child's return this commission wants."""
    selection = []
    if task['kind'] == 'verified_source_leads':
        selection.append(LEADS)
    elif task['answer_kind'] == 'screening':
        selection.append(SCREENING)
    if slot in CELLS_FROM:
        if parent[REQUESTED_GRADING]:
            selection.append(GRADING_CELLS)
        if parent[REQUESTED_AGGREGATION]:
            selection.append(AGGREGATION_CELLS)
    return tuple(selection)


def msg_to_child(slot, arguments, summary):
    assignment = summary['literature_assignment']
    page = {name: assignment[name] for name in ('version', 'source_ref', 'representation', 'artifact_ref',
                                                'question_context_refs', 'prior_delivery_refs')}
    task = summary['task']
    parent = {REQUESTED_GRADING: assignment.get(REQUESTED_GRADING, []),
              REQUESTED_AGGREGATION: assignment.get(REQUESTED_AGGREGATION, [])}
    child = {'version': 'reading_assignment_v1', 'page': page, 'selection': arguments['selection'],
             'literature_task': task, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
             **{name: value for name, value in parent.items() if value and slot in CELLS_FROM},
             'scope': summary['scope'],
             'received_record_refs': list(dict.fromkeys(
                 [*summary['received_record_refs'], *page['question_context_refs'], *page['prior_delivery_refs']]))}
    return ChildMessage(objective=arguments['objective'], message={'scope': summary['scope']},
                        assignment=child, selection=selected_fields(slot, task, parent))
