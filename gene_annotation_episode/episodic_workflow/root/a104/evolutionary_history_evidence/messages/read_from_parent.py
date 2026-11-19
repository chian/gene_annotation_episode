"""What the commissioner gives: the A104 assignment (the old ``_ASSIGNMENT`` of ``scientific_assignment_contracts.py``:
``selection``, ``proposed_annotation_ref``, ``evidence_refs``, ``constraints``, ``context`` and ``revision_origin``,
one field per property, under the same names) and the invocation values of the old ``_invocation`` that are not the
return form (``purpose`` and ``initial_report``, read from the message; the parent writes no return form, it selects
fields, and the objective is the commission's objective).

This is the only place the assignment is read. The checks of the old ``_assignment`` / ``_selection`` that need no
library or Store (the recorded assignment schema, the pinned selection, the revision origin, the original task) are
made here and raise. The checks that were a check of a commission are not carried (a wrong commission fails, rule 1):
``prepare_assignment`` (the inherited annotation differs, the parent did not receive it), ``_validate_origin`` (the
preparation of a revision against the parent's journal), ``reference_in_scope`` of the proposed annotation and of every
evidence reference (custody does it: they are ``record_refs`` fields and the pass requires the commissioner to hold
them). The resolution of the selection against the frozen libraries (``library.resolve``, ``tool_library``) happens in
``task.py`` and ``yield_estimator.py``, which read the settings.

New fields the final form needs (listed in the carry-over record as ``new field``): ``scope`` (the old code took the
Store scope from the request of the commission: the subject scope the credit projector reads) and ``record_refs`` (the
records the commission names beyond the evidence references: the proposed annotation, the subjects of the scope and
the records the model names for the child). ``evidence_refs`` is a ``record_refs`` field (custody) where the old
schema had a list of reference text."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.construction_records import (
    validate_revision_origin, validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    obj, validate_schema)

AXIS = 'A104'
# The old ``_EVIDENCE_TASK``: the whole-axis task the root commissions; ``credit_unit`` is the finding unit of the
# explicitly configured credit definition for this exact task.
_EVIDENCE_TASK = obj({'version': {'const': 'evidence_axis_task_v1'}, 'kind': {'const': 'whole_axis_findings'},
                      'evidence_axis': {'const': AXIS},
                      'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}})
# The old ``_ASSIGNMENT`` context: the evidence task and, optionally, the original A104 task (name).
_CONTEXT = {'type': 'object', 'properties': {'evidence_task': _EVIDENCE_TASK}}

ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The pinned selection of this episode: version, evidence_axis (the A104 option '
                                 'reference of the process library), thought_pattern (a P option reference) and '
                                 'child_tool_info (the canonical rows: name, description, resources, instructions)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation this task evaluates', required=False),
    'evidence_refs': Field('record_refs', 'The evidence records of the commission, passed in custody'),
    'constraints': Field('record', "The commissioner's constraints"),
    'context': Field('record', 'The commission context: evidence_task (whole_axis_findings, A104, credit_unit) and '
                               'optionally the original a104_task (name, and allowed_tasks)'),
    'revision_origin': Field('record', 'The explicit relationship of this episode to the process.revise preparation '
                                       'of its parent, when it is an alternative approach', required=False),
    'scope': Field('record', 'The Store scope of the commission: its subject_refs (new field: the old request scope)'),
    'record_refs': Field('record_refs', 'The records the commission names besides the evidence records: the '
                                        'proposed annotation, the subjects of the scope (new field)',
                         required=False),
})


def read_from_parent(assignment, message):
    selection = validate_selection(assignment['selection'])
    context = assignment['context']
    validate_schema(context, _CONTEXT)
    if 'a104_task' in context and not isinstance(context['a104_task'], dict):
        raise ValueError('a104_original_task_definition_required')
    revision_origin = assignment.get('revision_origin')
    if revision_origin is not None:
        revision_origin = validate_revision_origin(revision_origin)
    purpose, initial_report = message['purpose'], message['initial_report']
    if not isinstance(purpose, str) or not purpose or not isinstance(initial_report, dict):
        raise ValueError('scientific_invocation_invalid')
    return {'selection': selection,
            'proposed_annotation_ref': assignment.get('proposed_annotation_ref'),
            'evidence_refs': list(assignment['evidence_refs']),
            'constraints': assignment['constraints'],
            'context': context,
            'evidence_task': context.get('evidence_task'),
            'a104_task': context.get('a104_task'),
            'revision_origin': revision_origin,
            'scope': assignment['scope'],
            'record_refs': list(assignment.get('record_refs', [])),
            'purpose': purpose,
            'initial_report': initial_report}
