"""What the commissioner gives: the old ``_ASSIGNMENT`` of ``scientific_contracts.py`` (``selection``,
``proposed_annotation_ref``, ``evidence_refs``, ``constraints``, ``context``, ``revision_origin``: one field per
property, under the same names) and the values the old episode took from its runner and its configuration.

New fields the final form needs (the old code read them from the runner or the configuration):
``scope`` (the Store scope the old runner passed as the request scope), ``scope_refs`` (the records the scope names,
in custody), ``proposed_annotation_refs`` (the proposed annotation in custody: the old ``initial_references`` named
it with ``evidence_refs``) and ``child_credit_units`` (the credit units of the children this episode commissions,
by name in ``_UNITS``: exactly the four the root sends, ``OPERATIONAL_CREDIT_UNITS`` of the root's ``credit.py``).

This is the only place the assignment is read. The old checks of the assignment that need nothing but its value are
carried: the selection and the revision origin are valid, every evidence reference has the reference form, the
evidence task is the closed ``evidence_axis_task_v1`` of A101, and a proposed annotation is present (the old
``credit_projector`` raised ``scientific_task_proposed_annotation_required`` for a head with private yield
bindings, which this head always has). The old checks against the runner (the proposed annotation was received by
the parent and is in scope, every evidence reference is in scope, the revision origin matches the parent's recorded
preparation, the selection's library and tools resolve) are not carried here: custody holds every record named in
a record_refs field, and the others need the old journal (machinery)."""
import re

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.construction_records import (
    validate_revision_origin, validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    obj, validate_schema)

AXIS = 'A101'
_REFERENCE = re.compile(r'^[a-z][a-z_]*_[a-f0-9]{24,64}$')
_EVIDENCE_TASK = obj({'version': {'const': 'evidence_axis_task_v1'}, 'kind': {'const': 'whole_axis_findings'},
                      'evidence_axis': {'const': AXIS},
                      'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}}, required=['version', 'kind',
                                                                                         'evidence_axis',
                                                                                         'credit_unit'])
_UNITS = ('handoff_unit', 'acquired_record_unit', 'information_unit', 'completion_target')

ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The selected evidence axis (A101), thought pattern and the child tool info '
                                 '(name, resources, description, instructions of each selected tool)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation this task evaluates', required=False),
    'evidence_refs': Field('record_refs', 'In-scope references the parent supplies, in custody'),
    'constraints': Field('record', "The parent's constraints (a free object)"),
    'context': Field('record', 'May carry evidence_task (evidence_axis_task_v1, whole_axis_findings, A101, '
                               'credit_unit) and the original task name a101_task'),
    'revision_origin': Field('record', 'sequence_homology_evidence_revision_origin_v1 of the parent invocation and '
                                       'its process.revise preparation, when this is an alternative approach',
                             required=False),
    'scope': Field('record', 'The Store scope this episode investigates (new field: the old request scope)'),
    'scope_refs': Field('record_refs', 'The records the scope names (new field)'),
    'proposed_annotation_refs': Field('record_refs', 'The proposed annotation in custody (new field)',
                                      required=False),
    'child_credit_units': Field('record', 'The credit units of the children this episode commissions, by unit '
                                          'name (new field)'),
})


def read_from_parent(assignment, message):
    """The validated assignment as the parent input; ``yield_task`` is the old ``continuation_task`` key."""
    selection = validate_selection(assignment['selection'])
    if selection['evidence_axis']['option_id'] != AXIS:
        raise ValueError('scientific_selection_axis_must_be_' + AXIS)
    proposed = assignment.get('proposed_annotation_ref')
    if not proposed:
        raise ValueError('scientific_task_proposed_annotation_required')
    for reference in (proposed, *assignment['evidence_refs']):
        if not _REFERENCE.fullmatch(reference):
            raise ValueError('scientific_evidence_reference_unavailable:' + reference)
    context = assignment['context']
    if 'evidence_task' in context:
        validate_schema(context['evidence_task'], _EVIDENCE_TASK)
    assigned = context.get(AXIS.lower() + '_task')
    if assigned is not None:
        if not isinstance(assigned, dict) or not isinstance(assigned.get('name'), str) or not assigned['name']:
            raise ValueError('scientific_continuation_original_task_required')
        yield_task = AXIS + ':' + assigned['name']
    else:
        yield_task = AXIS + ':a101_native_sequence_correspondence'
    units = assignment['child_credit_units']
    if set(units) != set(_UNITS) or any(type(units[name]) not in (int, float) or units[name] <= 0 for name in _UNITS):
        raise ValueError('explicit_positive_operational_credit_units_required')
    parent_input = {'selection': selection, 'proposed_annotation_ref': proposed,
                    'evidence_refs': list(assignment['evidence_refs']), 'constraints': assignment['constraints'],
                    'context': context, 'scope': assignment['scope'], 'scope_refs': list(assignment['scope_refs']),
                    'child_credit_units': dict(units), 'yield_task': yield_task, 'message': dict(message)}
    if 'revision_origin' in assignment:
        parent_input['revision_origin'] = validate_revision_origin(assignment['revision_origin'])
    return parent_input
