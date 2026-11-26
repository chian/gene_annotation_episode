"""What the commissioner gives: the selection, the scope and its records in custody, the records already known, the
constraints, the context and the credit units of the children this episode commissions; and, when the commissioner has
them, the candidate organisms of the subject.

There is no proposed annotation: this head is commissioned on a subject and finds its candidate annotations (the owner,
2026-11-25: the pipeline starts "with no proposed annotations period"). This is the only place the assignment is read.
The checks of the assignment that need nothing but its value: the selection and the revision origin are valid, every
evidence reference has the reference form, the evidence task is the closed ``evidence_axis_task`` of A101, and the credit
units are the four positive ones. Custody holds every record named in a record_refs field."""
import re

from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.construction_records import (
    validate_revision_origin, validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    obj, validate_schema)

AXIS = 'A101'
_REFERENCE = re.compile(r'^[a-z][a-z_]*_[a-f0-9]{24,64}$')
_EVIDENCE_TASK = obj({'version': {'const': 'evidence_axis_task'}, 'kind': {'const': 'whole_axis_findings'},
                      'evidence_axis': {'const': AXIS},
                      'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}}, required=['version', 'kind',
                                                                                         'evidence_axis',
                                                                                         'credit_unit'])
_UNITS = ('handoff_unit', 'acquired_record_unit', 'information_unit', 'completion_target')

ORGANISM_ROLES = ('leader', 'on_the_leaders_lineage', 'rival')
ORGANISM_FORM = RecordForm({
    'taxon_id': Field('integer', 'The candidate taxon (NCBI taxonomy id)'),
    'name': Field('text', 'The taxonomy\'s own name of the taxon'),
    'rank_code': Field('text', 'The rank code of the taxon (a rank letter, a digit for a level between two ranks)'),
    'score': Field('number', 'The candidate\'s score: the support on its own lineage'),
    'role': ChoiceField('text', 'The leading candidate, a vaguer candidate on its lineage, or its leading rival',
                        ORGANISM_ROLES),
})
ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The selected evidence axis (A101), thought pattern and the child tool info '
                                 '(name, resources, description, instructions of each selected tool)'),
    'evidence_refs': Field('record_refs', 'In-scope references the parent supplies, in custody'),
    'constraints': Field('record', "The parent's constraints (a free object)"),
    'context': Field('record', 'May carry evidence_task (evidence_axis_task, whole_axis_findings, A101, '
                               'credit_unit) and the original task name a101_task'),
    'revision_origin': Field('record', 'sequence_homology_evidence_revision_origin of the parent invocation and '
                                       'its process.revise preparation, when this is an alternative approach',
                             required=False),
    'scope': Field('record', 'The Store scope this episode investigates (new field: the old request scope)'),
    'scope_refs': Field('record_refs', 'The records the scope names (new field)'),
    'child_credit_units': Field('record', 'The credit units of the children this episode commissions, by unit '
                                          'name (new field)'),
    'organism_candidates': Field('list', 'The candidate organisms of the DNA the subject is from, as the organism '
                                         'identification head found them and the commissioner chose to pass them: the '
                                         'leading candidate, the vaguer candidates on its lineage and its leading rival, '
                                         'each with its score', items=ORGANISM_FORM, required=False),
})


def read_from_parent(assignment, message):
    """The validated assignment as the parent input; ``yield_task`` is the old ``continuation_task`` key."""
    selection = validate_selection(assignment['selection'])
    if selection['evidence_axis']['option_id'] != AXIS:
        raise ValueError('scientific_selection_axis_must_be_' + AXIS)
    for reference in assignment['evidence_refs']:
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
    parent_input = {'selection': selection,
                    'evidence_refs': list(assignment['evidence_refs']), 'constraints': assignment['constraints'],
                    'context': context, 'scope': assignment['scope'], 'scope_refs': list(assignment['scope_refs']),
                    'child_credit_units': dict(units), 'yield_task': yield_task, 'message': dict(message),
                    'organism_candidates': list(assignment.get('organism_candidates', []))}
    if 'revision_origin' in assignment:
        parent_input['revision_origin'] = validate_revision_origin(assignment['revision_origin'])
    return parent_input
