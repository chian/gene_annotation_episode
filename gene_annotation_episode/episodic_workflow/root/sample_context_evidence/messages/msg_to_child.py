"""The commissions of the two children: a narrower A108 sample-context investigation by this binding itself (slot
``sample_context_evidence``, the old child role of that name) and the assessment of published evidence (slot
``published_evidence_assessment``, the old child role ``literature``).

Carried from the old ``to_child_sample_context_evidence.py`` and ``to_child_published_evidence_assessment.py`` (and the
child assignment of ``from_parent.py``). The old preparers took the objective (``selection.goal``), the purpose, the
expanded report schema, the initial report and ``selection.assignment``; the objective and the purpose are the
commission's ``objective`` and the ``purpose`` of its ``message`` now, and the report schema is the ``selection`` of
the child's selectable return fields (README 3b C4). The recursion's assignment is the old ``_ASSIGNMENT``: the
selection the model copied from ``process_revise`` (with its ``revision_origin`` when it is an alternative approach),
the evidence references the model names, and the proposed annotation, the constraints and the context (with the
evidence task) which the old ``prepare_assignment`` inherited from the parent (``child_proposed_annotation_differs_from_original_task``);
the literature assignment is the old ``literature_assignment`` (the question context, the sources, the commissioned
task, the proposed annotation and the requested grading and aggregation components). The child scope is the model's
(within the parent scope: the Store admits it); ``received_record_refs`` names every record the child reads and
``evidence_refs`` and the lists do not name (decision T5): the proposed annotation, the hypothesis and subjects it
names, the scope subjects, the sources of the task with their artifacts and the records the parent received.

A commission that is wrong (a selection the child does not declare, a record this episode does not hold, a task the
child's form does not admit) raises in the child's form, in custody or here and fails the run: nothing here checks it.
The old checks of the commission (scope within the parent scope, each required return source once, the initial report
valid against the schema, the role allowed) are not carried."""
from episode_runtime import ChildMessage

COMMITTED = 'committed_record_refs'
REQUESTED_GRADING = 'requested_a108_grading_components'
REQUESTED_AGGREGATION = 'requested_a108_aggregation_components'
ARTIFACT_KEYS = ('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref')


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


def passed_records(summary, scope, sources):
    """Every record a child reads that the commission's lists do not name."""
    custody = summary['held_source_custody']
    return list(dict.fromkeys([
        *(ref for source in sources for ref in source_records(custody, source)),
        *summary['received_record_refs'], summary['proposed_annotation_ref'],
        *summary['proposed_annotation_subject_refs'], *scope['subject_refs']]))


def msg_to_child(slot, arguments, summary):
    scope = arguments['scope']
    if slot == 'sample_context_evidence':
        assignment = {'selection': arguments['selection'],
                      'proposed_annotation_ref': summary['proposed_annotation_ref'],
                      'evidence_refs': arguments['evidence_refs'], 'constraints': summary['constraints'],
                      'context': summary['context'],
                      **({'revision_origin': arguments['revision_origin']}
                         if arguments.get('revision_origin') is not None else {}),
                      'scope': scope, 'received_record_refs': passed_records(summary, scope, [])}
        selection = tuple(dict.fromkeys([COMMITTED, *arguments['return_fields']]))
    elif slot == 'published_evidence_assessment':
        given = arguments['assignment']
        assignment = {'version': 'literature_assignment',
                      'question_context_refs': given['question_context_refs'],
                      'literature_task': given['literature_task'],
                      'proposed_annotation_ref': summary['proposed_annotation_ref'],
                      **{name: given[name] for name in (REQUESTED_GRADING, REQUESTED_AGGREGATION) if given[name]},
                      'scope': scope,
                      'received_record_refs': passed_records(summary, scope, [])}
        assignment['received_record_refs'] = list(dict.fromkeys(
            [*assignment['received_record_refs'], *given['question_context_refs']]))
        selection = tuple(arguments['return_fields'])
    return ChildMessage(objective=arguments['objective'], message={'purpose': arguments['purpose'], 'scope': scope},
                        assignment=assignment, selection=selection)
