"""What the parent gives: the A108 assignment of the old ``from_parent.py`` (``_ASSIGNMENT``): the selection (the
evidence axis A108, a thought pattern and the selected tools), the proposed annotation the task evaluates, the evidence
references, the constraints, the context holding the evidence task (``evidence_axis_task_v1``, the credit unit of the
whole-axis findings) and, for a child that is an alternative approach, the revision origin; with the Store scope of the
commission and the records passed in custody. This is the only place the assignment is read.

``selection``, ``proposed_annotation_ref``, ``evidence_refs``, ``constraints``, ``context`` and ``revision_origin`` are the
properties of the old assignment schema, under their names. ``proposed_annotation_ref`` is required here: the old
``credit_projector`` refused every yield-bound task without it (``scientific_task_proposed_annotation_required``) and the
yield settings are always set now. ``scope`` and ``received_record_refs`` are new fields: the old episode took the scope
from its request and the records it received from its binding context; the new commission names both
(contract_misfits: "new field: sample_context_evidence scope", "new field: sample_context_evidence
received_record_refs").

Carried here from the old ``from_parent.py`` and ``scientific_contracts.py``: the form of the selection (the version, the
two pinned option references, the tool selectors) and of the evidence task. The old checks of the assignment against the
head library (the axis entry kind, the library id), the tool library (``resolve_tool_info``), the Store (scope,
proposed annotation received by the parent, evidence references in scope) and the parent's ``process.revise``
preparation (``_validate_origin``) check a commission: they are not carried, a wrong commission fails where its records
are read. The selection travels as the selectors the old assignment carried; ``process_selection`` (``task.py``)
materializes their descriptions and instructions from the tool library, as the old ``materialize`` did."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.construction_records import (
    SELECTION_VERSION, validate_option_ref)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sample_context_evidence.tool_information import (
    selectors)

AXIS = 'A108'
EVIDENCE_TASK_FIELDS = {'version', 'kind', 'evidence_axis', 'credit_unit'}

ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The selection: version, the pinned evidence_axis (A108) and thought_pattern option '
                       'references and child_tool_info, the selected tools as name and resources'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation this task evaluates'),
    'evidence_refs': Field('record_refs', 'The evidence records passed in custody'),
    'constraints': Field('record', 'The parent\'s constraints'),
    'context': Field('record', 'The task context; context.evidence_task is version evidence_axis_task_v1, kind '
                     'whole_axis_findings, evidence_axis A108 and the credit_unit of the finding progress'),
    'revision_origin': Field('record', 'For a child that is an alternative approach: the parent invocation and the '
                             'process_revise operation that prepared the selection', required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The records the episode reads that evidence_refs does not name: the '
                                  'proposed annotation, the hypothesis and subjects it names, the scope subjects and '
                                  'the sources and their artifacts the parent passes (new field: old binding-context '
                                  'received records)'),
})


def selection_of(value):
    """The old ``_SELECTION`` form: the version, the two pinned references of their slots and the tool selectors."""
    if not isinstance(value, dict) or set(value) != {'version', 'evidence_axis', 'thought_pattern', 'child_tool_info'}:
        raise ValueError('sample_context_evidence_selection_invalid')
    if value['version'] != SELECTION_VERSION:
        raise ValueError('sample_context_evidence_selection_invalid')
    axis, thought = validate_option_ref(value['evidence_axis']), validate_option_ref(value['thought_pattern'])
    if axis['slot'] != 'evidence_axis' or axis['option_id'] != AXIS or thought['slot'] != 'thought_pattern':
        raise ValueError('sample_context_evidence_selection_invalid')
    if axis['library_id'] != thought['library_id']:
        raise ValueError('sample_context_evidence_selection_invalid')
    return {'version': value['version'], 'evidence_axis': axis, 'thought_pattern': thought,
            'child_tool_info': selectors(value['child_tool_info'])}


def evidence_task_of(context):
    """The old ``original_task_projector`` form: the commissioned whole-axis finding task of this axis."""
    task = context.get('evidence_task') if isinstance(context, dict) else None
    if (not isinstance(task, dict) or set(task) != EVIDENCE_TASK_FIELDS
            or task['version'] != 'evidence_axis_task_v1' or task['kind'] != 'whole_axis_findings'
            or task['evidence_axis'] != AXIS):
        raise ValueError('original_axis_finding_task_required')
    return task


def read_from_parent(assignment, message):
    """The parent input: the selection, the proposed annotation, the evidence, the constraints, the context and its
    evidence task, the revision origin when there is one, the scope, the passed records and the message."""
    return {'selection': selection_of(assignment['selection']),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'evidence_refs': assignment['evidence_refs'], 'constraints': assignment['constraints'],
            'context': assignment['context'], 'evidence_task': evidence_task_of(assignment['context']),
            'revision_origin': assignment.get('revision_origin'),
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
