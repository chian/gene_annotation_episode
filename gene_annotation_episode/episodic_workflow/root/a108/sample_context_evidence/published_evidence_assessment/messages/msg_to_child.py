"""The commission of the evidence search strategy improvement child. The parent states what the child takes in its own
assignment: the strategy assignment ``strategy_assignment_v1`` (the sources earlier searches returned, whose use is
revised, and the records that give the question its context), the commissioned literature task, the proposed
annotation, the A108 components the parent wants returned, the scope and the records the child reads.

Carried from the old ``to_child_evidence_search_strategy_improvement.py`` (child role ``literature_strategy``). The old
request carried the child scope (within the parent scope) and ``episode_assignment`` was the child binding's
``prepare_assignment`` applied to the assignment the model wrote (with the parent's yield binding filled in); the old
expanded return contract is the ``selection`` of fields now, and the old initial report values ride in ``message`` (the
scope).

Records (decision T5, name every record the child reads): every earlier search result, every artifact it holds and the
sources it derives from with theirs (read from the summary's ``held_source_custody``), the sources of the task, the
question-context records, the proposed annotation and the hypothesis and scope subjects the summary names, and the
records the parent received for the task.

The task is passed as this episode holds it (the child's own ``commissioned_task`` checks it). Selection: this episode
returns the commissioned task's answers, so it asks the child for the answer that task needs (source-lead dispositions,
screening answers) and, when its own assignment requests A108 components, for the cells of the requested families.

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
    task = summary['task']
    custody = summary['held_source_custody']
    sources = [*arguments['prior_search_refs'], *task.get('source_refs', [])]
    child = {'version': 'strategy_assignment_v1',
             'question_context_refs': arguments['question_context_refs'],
             'prior_search_refs': arguments['prior_search_refs'],
             'literature_task': task, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
             **{name: assignment[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION)
                if assignment.get(name)},
             'scope': summary['scope'],
             'received_record_refs': list(dict.fromkeys([
                 *(ref for source in sources for ref in source_records(custody, source)),
                 *arguments['question_context_refs'],
                 summary['proposed_annotation_ref'], *summary['proposed_annotation_subject_refs'],
                 *summary['scope']['subject_refs'], *summary['received_record_refs']]))}
    return ChildMessage(objective=arguments['objective'], message={'scope': summary['scope']},
                        assignment=child, selection=selected_fields(task, assignment))
