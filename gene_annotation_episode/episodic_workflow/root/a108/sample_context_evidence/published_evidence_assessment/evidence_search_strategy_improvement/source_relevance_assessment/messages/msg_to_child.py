"""The commission of the source evidence examination child. The parent states what the child takes in its own
assignment: the page assignment ``page_assignment_v1`` (the one source and representation the model chose, with the
records that give the question context and those delivered by earlier examinations of that source), the commissioned
literature task narrowed to that source, the proposed annotation, the A108 components the parent wants returned, the
scope and the records the child reads.

Carried from the old ``to_child_source_evidence_examination.py`` (child role ``literature_page``). The old request
carried the child scope (within the parent scope), the commissioned task and the proposed annotation, and
``episode_assignment`` was the child binding's ``prepare_assignment`` applied to the assignment the model wrote; the old
expanded return contract is the ``selection`` of fields now.

Records (decision T5, name every record the child reads): the page's source, every artifact the source holds, the
sources it derives from with theirs (read from the summary's ``held_source_custody``), the question-context and
prior-delivery records, the proposed annotation and the hypothesis and scope subjects the summary names, and the records
the parent received for the task.

The task is narrowed to the page: an assessment task keeps only the page's source among its ``source_refs``, a
screening task only its spans of that source (the child's own ``commissioned_task`` refuses a task outside its
source). Selection: this episode returns the commissioned task's answers, so it asks the child for the answer that
task needs (source-lead dispositions, screening answers) and, when its own assignment requests A108 components, for the
cells of the requested families.

A commission that is wrong (a selection the child does not declare, a record this episode does not hold, a source not in
``held_source_custody``, a task the child's form does not admit) raises in the child's form, in custody or here and fails
the run: nothing here checks it."""
from episode_runtime import ChildMessage

LEADS = 'literature_source_lead_dispositions'
SCREENING = 'literature_screening_answers'
GRADING_CELLS = 'literature_a108_grading_cells'
AGGREGATION_CELLS = 'literature_a108_aggregation_cells'
REQUESTED_GRADING = 'requested_a108_grading_components'
REQUESTED_AGGREGATION = 'requested_a108_aggregation_components'
ARTIFACT_KEYS = ('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref')


def selected_fields(task, assignment):
    """The selectable fields of the child's return this commission wants."""
    selection = []
    if task['kind'] == 'verified_source_leads':
        selection.append(LEADS)
    elif task['answer_kind'] == 'screening':
        selection.append(SCREENING)
    if assignment.get(REQUESTED_GRADING):
        selection.append(GRADING_CELLS)
    if assignment.get(REQUESTED_AGGREGATION):
        selection.append(AGGREGATION_CELLS)
    return tuple(selection)


def narrowed_task(task, source_ref):
    """The commissioned task for one source: the page's source among an assessment's ``source_refs``, the page's
    spans of a screening's ``examined``."""
    if task['kind'] == 'verified_source_leads':
        return task
    if task['answer_kind'] == 'assessment':
        return {**task, 'source_refs': [ref for ref in task['source_refs'] if ref == source_ref]}
    return {**task, 'examined': [span for span in task['examined'] if span['source_ref'] == source_ref]}


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
    assignment = summary['literature_assignment']
    page = arguments['page']
    task = narrowed_task(summary['task'], page['source_ref'])
    child = {'version': 'page_assignment_v1', **page,
             'literature_task': task, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
             **{name: assignment[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION)
                if assignment.get(name)},
             'scope': summary['scope'],
             'received_record_refs': list(dict.fromkeys([
                 *source_records(summary['held_source_custody'], page['source_ref']),
                 *page['question_context_refs'], *page['prior_delivery_refs'],
                 summary['proposed_annotation_ref'], *summary['proposed_annotation_subject_refs'],
                 *summary['scope']['subject_refs'], *summary['received_record_refs']]))}
    return ChildMessage(objective=arguments['objective'], message={'scope': summary['scope']},
                        assignment=child, selection=selected_fields(task, assignment))
