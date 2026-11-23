"""What the A102 head reads from its commissioner: the assignment form an axis head gets from the root
(``root/messages/msg_to_child.py``, ``structural_homology_evidence``): ``selection``, ``proposed_annotation_ref`` (one record
reference in custody), ``evidence_refs``, ``constraints``, ``context``, ``scope`` (the Store scope) and ``scope_refs`` (the records
the scope names, in custody), and ``child_credit_units``: the credit units of the child this episode commissions, by name in
``_UNITS`` (``handoff_unit``, ``acquired_record_unit``, ``information_unit``, ``completion_target`` and ``model_unit``, the credit
of a model of the target obtained by the child).

This is the only place the assignment is read. It checks what needs nothing but the value: the selection names the evidence axis
A102, the proposed annotation is one reference, every reference has the reference form, the evidence task is the closed
``evidence_axis_task`` of A102 and the credit units are positive. ``yield_task`` is the key of the head's declaration in
``yield_bindings`` (``yield_estimator.py``). Custody holds every record named in a ``record_refs`` field."""
import re

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.construction_records import (
    validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    obj, validate_schema)

AXIS = 'A102'
YIELD_TASK = AXIS + ':a102_structural_correspondence'
_REFERENCE = re.compile(r'^[a-z][a-z_]*_[a-f0-9]{24,64}$')
_EVIDENCE_TASK = obj({'version': {'const': 'evidence_axis_task'}, 'kind': {'const': 'whole_axis_findings'},
                      'evidence_axis': {'const': AXIS},
                      'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}},
                     required=['version', 'kind', 'evidence_axis', 'credit_unit'])
_UNITS = ('handoff_unit', 'acquired_record_unit', 'information_unit', 'completion_target', 'model_unit')

ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The selected evidence axis (A102), thought pattern and the child tool info'),
    'proposed_annotation_ref': Field('record_refs', 'The proposed annotation this task evaluates (exactly one reference), '
                                                    'passed in custody'),
    'evidence_refs': Field('record_refs', 'The evidence records the commission names, passed in custody'),
    'constraints': Field('record', "The commissioner's constraints"),
    'context': Field('record', 'May carry evidence_task (evidence_axis_task, whole_axis_findings, A102 and a positive '
                               'credit_unit)'),
    'scope': Field('record', 'The Store scope this episode investigates'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody'),
    'child_credit_units': Field('record', 'The credit units of the child this episode commissions, by unit name'),
})


def read_from_parent(assignment, message):
    """The validated assignment as the parent input."""
    selection = validate_selection(assignment['selection'])
    if selection['evidence_axis']['option_id'] != AXIS:
        raise ValueError('scientific_selection_axis_must_be_' + AXIS)
    (proposed,) = assignment['proposed_annotation_ref']
    for reference in (proposed, *assignment['evidence_refs']):
        if not _REFERENCE.fullmatch(reference):
            raise ValueError('scientific_evidence_reference_unavailable:' + reference)
    context = assignment['context']
    if 'evidence_task' in context:
        validate_schema(context['evidence_task'], _EVIDENCE_TASK)
    units = assignment['child_credit_units']
    if set(units) != set(_UNITS) or any(type(units[name]) not in (int, float) or units[name] <= 0 for name in _UNITS):
        raise ValueError('explicit_positive_operational_credit_units_required')
    return {'selection': selection, 'proposed_annotation_ref': proposed, 'evidence_refs': list(assignment['evidence_refs']),
            'constraints': assignment['constraints'], 'context': context, 'scope': assignment['scope'],
            'scope_refs': list(assignment['scope_refs']), 'child_credit_units': dict(units), 'yield_task': YIELD_TASK,
            'message': dict(message)}
