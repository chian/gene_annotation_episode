"""What the A102 head reads from its commissioner (carried from ``from_parent.py`` and ``scientific_contracts.py``
at ``97308b94c``).

``ASSIGNMENT_FORM`` has one field per property of the old ``_ASSIGNMENT`` under its old name: ``selection``,
``proposed_annotation_ref``, ``evidence_refs``, ``constraints``, ``context`` and ``revision_origin``. Two fields are
new (the old head took them from its request and its binding context): ``scope`` (the Store scope of the
commission) and ``scope_refs`` (the records the scope names, passed in custody: a read of the scope or an
inventory under it needs every subject held). ``proposed_annotation_ref`` and ``evidence_refs`` are
``record_refs``: the records travel in custody (the old one was a single text reference; the form carries it as a
list of one).

``read_from_parent`` is the only place the assignment is read. It makes the old assignment checks that need no Store
(the selection's identity, the evidence-axis task, the proposed annotation count, the revision origin) and derives
what the head's credit and its controller need: the commissioned task, the projector's own record, the estimator
kind it requires and the maximum it declares. The old checks that read the old journal or the old library (the
selection resolving against this library and tool library, the proposed annotation and evidence references being
inside the scope, a ``revision_origin`` matching the parent's recorded ``process.revise`` preparation, a
descendant not changing the proposed annotation) are not made here: custody holds the records, and the receipt
journal and the preparation lookup are old-runner machinery.
"""
from __future__ import annotations

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.structural_evidence import (
    task_context)
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.construction_records import (
    SELECTION_VERSION, validate_option_ref, validate_revision_origin)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_information import tool_info_selection

from .. import credit as credit_file

AXIS = 'A102'
EVIDENCE_TASK_VERSION = 'evidence_axis_task_v1'

ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The selected evidence axis (option A102), thought pattern and tool information: '
                       'version, evidence_axis, thought_pattern and child_tool_info (name and resources of each '
                       'selected tool)'),
    'proposed_annotation_ref': Field('record_refs', 'The proposed annotation this task evaluates (exactly one '
                                     'reference), passed in custody', required=False),
    'evidence_refs': Field('record_refs', 'The evidence records the commission names, passed in custody'),
    'constraints': Field('record', "The commissioner's constraints"),
    'context': Field('record', 'The commission context: evidence_task (version evidence_axis_task_v1, kind '
                     'whole_axis_findings, evidence_axis A102 and a positive credit_unit) and, when the commission '
                     'is a named A102 task, a102_task'),
    'revision_origin': Field('record', 'Present when the commission came from the commissioner\'s process revision '
                             '(version, parent_invocation_ref, preparation_operation_ref)', required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: the old head took it from its '
                   'request)'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody (new field)'),
})


def check_selection(selection):
    """The old ``_selection`` as far as no library is needed: the version, the evidence-axis option A102, the
    thought pattern option, one library for both and the tool information of the selected tools."""
    if not isinstance(selection, dict) or selection.get('version') != SELECTION_VERSION:
        raise ValueError('structural_homology_evidence_selection_invalid')
    if set(selection) != {'version', 'evidence_axis', 'thought_pattern', 'child_tool_info'}:
        raise ValueError('structural_homology_evidence_selection_invalid')
    axis = validate_option_ref(selection['evidence_axis'])
    thought = validate_option_ref(selection['thought_pattern'])
    if axis['slot'] != 'evidence_axis' or axis['option_id'] != AXIS or thought['slot'] != 'thought_pattern':
        raise ValueError('scientific_support_metadata_required')
    if axis['library_id'] != thought['library_id']:
        raise ValueError('scientific_selection_library_mismatch')
    return {'version': selection['version'], 'evidence_axis': axis, 'thought_pattern': thought,
            'child_tool_info': tool_info_selection(selection['child_tool_info'])}


def check_context(context):
    """The old ``context.evidence_task`` form and the named A102 task (the task is its library definition)."""
    task = context.get('evidence_task')
    if task is not None:
        if (not isinstance(task, dict) or set(task) != {'version', 'kind', 'evidence_axis', 'credit_unit'}
                or task['version'] != EVIDENCE_TASK_VERSION or task['kind'] != 'whole_axis_findings'
                or task['evidence_axis'] != AXIS or isinstance(task['credit_unit'], bool)
                or not isinstance(task['credit_unit'], (int, float)) or not task['credit_unit'] > 0):
            raise ValueError('scientific_evidence_task_invalid')
    named = context.get('a102_task')
    if named is not None:
        if not isinstance(named, dict) or named != task_context(named.get('name')):
            raise ValueError('a102_original_task_definition_required')
        return named['name'], (None if task is None else task['credit_unit'])
    return None, (None if task is None else task['credit_unit'])


def read_from_parent(assignment, message):
    """The parent input: the admitted assignment and what the head's credit and controller derive from it."""
    selection = check_selection(assignment['selection'])
    proposed = list(assignment.get('proposed_annotation_ref', []))
    if len(proposed) > 1:
        raise ValueError('scientific_one_proposed_annotation_required')
    context = dict(assignment['context'])
    task_name, credit_unit = check_context(context)
    revision_origin = assignment.get('revision_origin')
    if revision_origin is not None:
        revision_origin = validate_revision_origin(revision_origin)
    projector = credit_file.projector(task_name)
    record = projector.as_record()
    return {'selection': selection, 'proposed_annotation_ref': proposed, 'evidence_refs': list(assignment['evidence_refs']),
            'constraints': dict(assignment['constraints']), 'context': context, 'revision_origin': revision_origin,
            'scope': dict(assignment['scope']), 'scope_refs': list(assignment['scope_refs']),
            'a102_task': task_name, 'credit_unit': credit_unit,
            'task_key': AXIS + ':' + (task_name if task_name is not None else record['kind']),
            'credit_definition': record, 'yield_method': projector.yield_method,
            'native_score_maximum': getattr(projector, 'native_score_maximum', None),
            'message': dict(message)}
