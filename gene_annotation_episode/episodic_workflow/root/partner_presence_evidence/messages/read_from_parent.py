"""What the commissioner gives, carried from the old ``from_parent.py`` (``ScientificFromParent.assignment_schema``,
``_assignment``) and the constants of the old ``scientific_assignment_contracts.py`` (``_ASSIGNMENT``,
``_SELECTION``, ``_EVIDENCE_TASK``, ``_REVISION_ORIGIN``).

Old assignment properties, under the same names: ``selection`` (the pinned evidence axis A107, one thought pattern
and the selected tools as ``{name, resources}``), ``proposed_annotation_ref`` (optional), ``evidence_refs``,
``constraints``, ``context`` (optionally ``evidence_task``) and ``revision_origin`` (optional). The old
``proposed_annotation_ref`` is one reference: a form has no single-reference type, so it is a ``record_refs`` field
holding at most one reference (``read_from_parent`` raises otherwise); ``evidence_refs`` is a ``record_refs`` field.

New fields the final form needs (each a "new field" in the carry-over record): ``scope`` (the subject scope the old
runner held; credit and the reasoning commit use it), ``received_record_refs`` (the records the old binding
context received, among them the subjects of the scope: a pass carries only the records named, so the credit that
reads the scope needs them held), ``finding_unit`` (the old credit unit, from the old yield binding or
``context.evidence_task.credit_unit``), and the units of the children this head commissions (``handoff_unit`` and
``acquired_record_unit`` of the launch and results children, ``information_unit`` of the monitor: old
configuration values of those children).

This is the only place the assignment is read. The old checks of the assignment itself are kept: the closed
assignment schema (``_ASSIGNMENT``, with the selection's pinned axis A107). Not carried: the checks of the commission
against the parent (``proposed_annotation_not_received_by_parent``, ``child_proposed_annotation_differs_from_original_task``,
the reference-in-scope tests, the revision origin's authentication against the parent's recorded preparation, the
tool resolution against the library): a wrong commission fails and nothing checks it ahead (rule 1); what they
stood for in custody is the ``record_refs`` fields. The old ``prepare_invocation`` (objective, purpose, closed
``report_schema`` and ``initial_report``, the filled process record and its digests) built the parent-written
report form and its frozen identity: the child declares its return now, so it is not carried."""
import math

from jsonschema import Draft202012Validator
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import obj

AXIS = 'A107'
SELECTION_VERSION = 'partner_presence_evidence_selection'
OPTION_REF_VERSION = 'partner_presence_evidence_option_ref'
REVISION_ORIGIN_VERSION = 'partner_presence_evidence_revision_origin'
REFERENCE = {'type': 'string', 'pattern': '^[a-z][a-z_]*_[a-f0-9]{24,64}$'}
SHA256 = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}


def ref_schema(slot, prefix):
    return obj({'version': {'const': OPTION_REF_VERSION}, 'library_id': SHA256, 'slot': {'const': slot},
                'option_id': {'type': 'string', 'pattern': '^' + prefix + '[0-9]+$'}, 'entry_sha256': SHA256})


EVIDENCE_AXIS = ref_schema('evidence_axis', 'A')
EVIDENCE_AXIS['properties']['option_id'] = {'const': AXIS}
THOUGHT_REF = ref_schema('thought_pattern', 'P')
TOOL_SELECTOR = obj({'name': {'type': 'string', 'minLength': 1}, 'resources': {'enum': ['api', 'local', 'hpc']}})
SELECTION = obj({'version': {'const': SELECTION_VERSION}, 'evidence_axis': EVIDENCE_AXIS,
                 'thought_pattern': THOUGHT_REF,
                 'child_tool_info': {'type': 'array', 'items': TOOL_SELECTOR, 'uniqueItems': True}})
REVISION_ORIGIN = obj({'version': {'const': REVISION_ORIGIN_VERSION},
                       'parent_invocation_ref': {'type': 'string', 'pattern': '^scientific_invocation_[a-f0-9]{24}$'},
                       'preparation_operation_ref': {'type': 'string', 'pattern': '^operation_[a-f0-9]{24}$'}})
EVIDENCE_TASK = obj({'version': {'const': 'evidence_axis_task'}, 'kind': {'const': 'whole_axis_findings'},
                     'evidence_axis': {'const': AXIS},
                     'credit_unit': {'type': 'number', 'exclusiveMinimum': 0,
                                     'description': 'Use the finding unit in the explicitly configured credit '
                                                    'definition for this exact task; do not select or change its '
                                                    'cutoff.'}})
ASSIGNMENT_SCHEMA = obj({'selection': SELECTION,
                         'proposed_annotation_ref': {**REFERENCE, 'description': 'The proposed annotation this task '
                                                                                  'evaluates.'},
                         'evidence_refs': {'type': 'array', 'items': REFERENCE, 'uniqueItems': True},
                         'constraints': {'type': 'object'},
                         'context': {'type': 'object', 'properties': {'evidence_task': EVIDENCE_TASK}},
                         'revision_origin': REVISION_ORIGIN},
                        required=['selection', 'evidence_refs', 'constraints', 'context'])

ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The pinned selection: version, the evidence axis option (A107), one thought '
                                 'pattern option and the selected tools as {name, resources}'),
    'proposed_annotation_ref': Field('record_refs', 'The proposed annotation this task evaluates: at most one '
                                                    'reference, passed in custody', required=False),
    'evidence_refs': Field('record_refs', 'The evidence operands selected by the parent, passed in custody'),
    'constraints': Field('record', "The parent's constraints"),
    'context': Field('record', 'The parent-supplied context; optionally evidence_task (evidence_axis_task, '
                               'whole_axis_findings, A107, credit_unit)'),
    'revision_origin': Field('record', 'The preparation this selection is an alternative approach of (a '
                                       'process.revise result), when it is one', required=False),
    # New fields the final form needs (the old code read them from the runner, the configuration and the yield
    # binding).
    'scope': Field('record', 'The subject scope of the original task (the old runner scope; new field)'),
    'received_record_refs': Field('record_refs', 'The records the commissioner passes beside the evidence '
                                                 'operands, among them the subjects of the scope (the old binding '
                                                 'context received records; new field)'),
    'finding_unit': Field('number', 'The credit of one distinct retained finding (the old yield binding credit '
                                    'definition; new field)'),
    'handoff_unit': Field('number', 'The operational credit unit of a usable handoff, for a launch child it '
                                    'commissions (old configuration of that child; new field)', required=False),
    'acquired_record_unit': Field('number', 'The operational credit unit of an acquired record, for a launch or '
                                            'results child it commissions (old configuration of those children; '
                                            'new field)', required=False),
    'information_unit': Field('number', 'The credit of one newly informative progress observation, for a monitor '
                                        'child it commissions (old configuration of that child; new field)',
                              required=False),
})


def read_from_parent(assignment, message):
    """The validated assignment as the parent input."""
    proposed = assignment.get('proposed_annotation_ref')
    if proposed is not None and len(proposed) != 1:
        raise ValueError('scientific_proposed_annotation_requires_exactly_one_reference')
    old = {key: assignment[key] for key in ('selection', 'evidence_refs', 'constraints', 'context')}
    for key in ('revision_origin',):
        if key in assignment:
            old[key] = assignment[key]
    if proposed is not None:
        old['proposed_annotation_ref'] = proposed[0]
    Draft202012Validator(ASSIGNMENT_SCHEMA).validate(old)
    for name in ('finding_unit', 'handoff_unit', 'acquired_record_unit', 'information_unit'):
        value = assignment.get(name)
        if value is not None and (value <= 0 or not math.isfinite(value)):
            raise ValueError('explicit_positive_credit_unit_required:' + name)
    return {'selection': old['selection'],
            'proposed_annotation_ref': None if proposed is None else proposed[0],
            'evidence_refs': list(old['evidence_refs']), 'constraints': old['constraints'],
            'context': old['context'], 'revision_origin': old.get('revision_origin'),
            'scope': assignment['scope'], 'received_record_refs': list(assignment['received_record_refs']),
            'finding_unit': assignment['finding_unit'], 'handoff_unit': assignment.get('handoff_unit'),
            'acquired_record_unit': assignment.get('acquired_record_unit'),
            'information_unit': assignment.get('information_unit'), 'message': dict(message)}
