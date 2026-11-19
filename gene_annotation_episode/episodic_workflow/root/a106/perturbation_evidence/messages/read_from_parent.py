"""What the commissioner gives: the A106 assignment (the old ``_ASSIGNMENT`` of ``scientific_contracts.py`` and
``ScientificAssignment.assignment_schema`` at 97308b94c): ``selection``, ``proposed_annotation_ref``,
``evidence_refs``, ``constraints``, ``context`` and ``revision_origin``, one field per property of the old
assignment schema, under the same names. This is the only place the assignment is read.

New fields the final form needs (listed in the carry-over record as ``new field``): ``scope`` (the old runner passed
the Store scope of the request, ``context.scope``, to ``prepare_assignment`` and to credit) and
``received_record_refs`` (the records the old binding context ``received_record_refs`` held: the proposed annotation
and what the children and the credit read through it; ``proposed_annotation_ref`` is one text, and a text is no
custody). The old invocation (``_invocation``: objective, purpose, report_schema, initial_report) is the
commission's ``objective`` and ``message`` now; the parent writes no report schema (the return form is this
episode's own), so the ``report_schema`` and ``initial_report`` of the old invocation have no place.

What the old assignment checks stood for: the checks of the assignment *itself* are made here and raise (the axis
task of ``context.evidence_task``, the shape of the selection and of the revision origin, the reference pattern of
``evidence_refs``, the proposed annotation that the old yield binding required). The checks of a *commission* are not
carried, because a wrong commission fails and nothing checks it ahead (owner's rule 1): the selection against the
process library and the tool library (``_selection``, ``_tool_resolution_for``), the references against the scope
(``reference_in_scope``), the revision origin against the recorded preparation of the parent (``_validate_origin``),
the filled-process identity digests (``validate_context``, ``validate_execution_context``) and the closed-commission
replay of ``prepare_invocation``."""
import math
import re

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.construction_records import (
    validate_revision_origin, validate_selection)

AXIS = 'A106'
TASK_VERSION = 'evidence_axis_task_v1'
TASK_KIND = 'whole_axis_findings'
REFERENCE = re.compile(r'^[a-z][a-z_]*_[a-f0-9]{24,64}$')      # the old ``_REFERENCE`` pattern

ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The selected process: version perturbation_evidence_selection_v3, the evidence_axis '
                                 'option reference (A106), the thought_pattern option reference and child_tool_info, '
                                 'the selected tools with their resolved description and instructions'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation this task evaluates; a child inherits it and '
                                             'cannot change it', required=False),
    'evidence_refs': Field('record_refs', 'The records of evidence already known for the question, passed in custody'),
    'constraints': Field('record', "The commissioner's constraints"),
    'context': Field('record', 'The commissioner context: evidence_task, the declared whole-axis finding task '
                               '(version evidence_axis_task_v1, kind whole_axis_findings, evidence_axis A106 and the '
                               'positive credit_unit of one retained finding)'),
    'revision_origin': Field('record', 'Set when this episode is an alternative approach prepared by process.revise '
                                       'of its parent: the parent invocation and the preparation operation',
                             required=False),
    # New fields the final form needs (the old code took them from the request and the binding context).
    'scope': Field('record', 'The Store scope of the commission (old: the scope of the request)'),
    'received_record_refs': Field('record_refs', 'The proposed annotation and every record this episode and its '
                                                 'children read through it, passed in custody (old: the binding '
                                                 "context's received_record_refs)", required=False),
})


def evidence_task(context):
    """The old ``original_task_projector`` check of ``context.evidence_task``: the declared whole-axis task."""
    task = context.get('evidence_task')
    if (not isinstance(task, dict) or set(task) != {'version', 'kind', 'evidence_axis', 'credit_unit'}
            or task['version'] != TASK_VERSION or task['kind'] != TASK_KIND or task['evidence_axis'] != AXIS):
        raise ValueError('original_axis_finding_task_required')
    unit = task['credit_unit']
    if type(unit) not in (int, float) or not math.isfinite(unit) or not unit > 0:
        raise ValueError('explicit_positive_finding_unit_required')
    return task


def read_from_parent(assignment, message):
    """The parent input: the validated assignment under its old names, the task, the task key and the message."""
    if assignment.get('proposed_annotation_ref') is None:        # the old yield binding required it
        raise ValueError('scientific_task_proposed_annotation_required')
    selection = validate_selection(assignment['selection'])
    parent_input = {'selection': selection, 'proposed_annotation_ref': assignment['proposed_annotation_ref'],
                    'evidence_refs': list(assignment['evidence_refs']), 'constraints': assignment['constraints'],
                    'context': assignment['context'], 'scope': assignment['scope'],
                    'received_record_refs': list(assignment.get('received_record_refs', [])),
                    'task': evidence_task(assignment['context']), 'message': dict(message)}
    for reference in parent_input['evidence_refs']:
        if not REFERENCE.fullmatch(reference):
            raise ValueError('scientific_evidence_reference_unavailable:' + reference)
    if 'revision_origin' in assignment:
        parent_input['revision_origin'] = validate_revision_origin(assignment['revision_origin'])
    parent_input['task_key'] = AXIS + ':' + TASK_KIND
    return parent_input
