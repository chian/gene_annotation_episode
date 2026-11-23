"""The commission of the source evidence examination child (the page): ONE paper. The parent states what the child
takes in its own assignment: the page assignment ``page_assignment`` (the source of the paper the picked hit names,
its representation and artifact, filled by code from the source record, with the records that give the question
context and no earlier delivery), the commissioned literature task, the proposed annotation, the A108 components the
parent wants returned, the scope and the records the child reads.

Carried from the old ``to_child_source_evidence_examination.py`` (child role ``literature_page``). The page's objective
is one fixed value, ``evidence_location_unknown``: the search has not read the paper, so it does not know whether the
paper holds a contextual observation, let alone where (that is what the page and the leaves below it find out). No
model-written text reaches the page; the model's part of the commission was to pick the hit.

Records (decision T5, name every record the child reads): the page's source, every artifact the source holds, the
sources it derives from with theirs (read from the summary's ``held_source_custody``), the question-context records,
the proposed annotation and the hypothesis and scope subjects the summary names, and the records the parent received
for the task.

Selection: this episode returns the commissioned task's answer, so it asks the child for the source-lead dispositions
and, when its own assignment requests A108 components, for the cells of the requested families.

A commission that is wrong (a selection the child does not declare, a record this episode does not hold, a source not in
``held_source_custody``, a task the child's form does not admit) raises in the child's form, in custody or here and fails
the run: nothing here checks it."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
GRADING_CELLS = 'literature_a108_grading_cells'
AGGREGATION_CELLS = 'literature_a108_aggregation_cells'
REQUESTED_GRADING = 'requested_a108_grading_components'
REQUESTED_AGGREGATION = 'requested_a108_aggregation_components'
ARTIFACT_KEYS = ('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref')
OBJECTIVE = 'evidence_location_unknown'


def selected_fields(task, assignment):
    """The selectable fields of the child's return this commission wants."""
    selection = [LEADS]
    if assignment.get(REQUESTED_GRADING):
        selection.append(GRADING_CELLS)
    if assignment.get(REQUESTED_AGGREGATION):
        selection.append(AGGREGATION_CELLS)
    return tuple(selection)


def source_records(custody, source_ref):
    """The source, its artifacts, the sources it derives from and theirs, by the custody the summary lists."""
    named, pending = [], [source_ref]
    while pending:
        current = pending.pop()
        if current in named:
            continue
        named.append(current)
        entry = custody[current]
        named.extend(entry[key] for key in ARTIFACT_KEYS if entry.get(key) is not None)
        pending.extend(entry.get('parent_source_refs') or ())
    return named


def msg_to_child(slot, arguments, summary):
    if slot != 'source_evidence_examination':
        raise LookupError('no_such_child_slot:' + slot)
    assignment = summary['literature_assignment']
    page = arguments['page']
    child = {'version': 'page_assignment', **page, 'question_context_refs': summary['question_context_refs'],
             'literature_task': summary['task'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
             **{name: assignment[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION)
                if assignment.get(name)},
             'scope': summary['scope'],
             'received_record_refs': list(dict.fromkeys([
                 *source_records(summary['held_source_custody'], page['source_ref']),
                 *summary['question_context_refs'], *page['prior_delivery_refs'],
                 summary['proposed_annotation_ref'], *summary['proposed_annotation_subject_refs'],
                 *summary['scope']['subject_refs'], *summary['received_record_refs']]))}
    return ChildMessage(objective=OBJECTIVE, message={'scope': summary['scope']},
                        assignment=child, selection=selected_fields(summary['task'], assignment))
