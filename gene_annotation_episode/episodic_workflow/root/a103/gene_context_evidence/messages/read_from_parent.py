"""What the commissioner gives: the A103 scientific assignment (the old ``_ASSIGNMENT`` of ``contracts.py``: ``selection``,
``proposed_annotation_ref``, ``evidence_refs``, ``constraints``, ``context`` and ``revision_origin``, one field per
property of the old assignment schema, under the same names). This is the only place the assignment is read.

``selection`` is the closed record of the old schema (the evidence axis option, the thought pattern option and the
canonical information of the selected tools); the old ``_selection`` check of its shape is made here with the library's
``validate_selection`` and raises. What the old ``_selection`` also did against the frozen option library and the tool
library (resolve each option, resolve each tool) needs those libraries; it is made by the lookup tool ``process_library``
of ``task.py`` (the libraries are opened from settings there, not here: this function is handed no settings).

``proposed_annotation_ref``, ``evidence_refs`` and ``scope_refs`` are ``record_refs`` fields: the old assignment named
its references as text checked in scope (``reference_in_scope``); a record the commissioner names here passes in custody
and a record it does not hold fails the commission (rule 1), so the old in-scope checks of the episode's own commission
are not carried. The old ``proposed_annotation_ref`` was one text; here it is a ``record_refs`` field of exactly one
reference, and ``read_from_parent`` gives the reference as text. It is required: the old ``credit_projector`` raised
``scientific_task_proposed_annotation_required`` when the commission had a private yield declaration and no proposed
annotation, and this episode's controller is always that declaration.

``context`` may carry ``evidence_task`` (the old ``_EVIDENCE_TASK``) and ``a103_task.name`` (the old continuation task
name, which ``yield_estimator.py`` reads from the parent input as ``a103_task_name``).

New fields the final form needs, listed in the carry-over record as ``new field``: ``scope`` (the subject scope the old
runner passed to ``prepare_assignment``; the A103 credit reads the original scope) and ``scope_refs`` (every record the
scope names, passed in custody: a scope's subjects must be held to be read). The old ``revision_origin`` check against
the parent's recorded preparation (``_validate_origin``: the recorded ``process.revise`` operation, the parent
invocation) read the old runner's tables; only its value shape is checked here."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.construction_records import (
    validate_revision_origin, validate_selection)

AXIS = 'A103'
EVIDENCE_TASK_VERSION = 'evidence_axis_task_v1'

ASSIGNMENT_FORM = RecordForm({
    'selection': Field('record', 'The selected evidence axis option (A103), the thought pattern option and the '
                                 'canonical information of the selected tools (gene_context_evidence_selection_v3)'),
    'proposed_annotation_ref': Field('record_refs', 'The proposed annotation (a hypothesis) this task evaluates: '
                                     'exactly one reference, passed in custody', required=False),
    'evidence_refs': Field('record_refs', 'Records the commissioner hands on as evidence, with every record the '
                           'child reads that they name, passed in custody'),
    'constraints': Field('record', "The commissioner's constraints"),
    'context': Field('record', "The commissioner's context: optionally evidence_task and a103_task"),
    'revision_origin': Field('record', 'Present when the selection was prepared by process.revise of the '
                             'commissioner: its parent invocation and preparation operation', required=False),
    # New fields the final form needs (the old code took them from the runner).
    'scope': Field('record', 'The subject scope fixed by the commissioner (old runner scope)'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody'),
})


def _evidence_task(value):
    """The old ``_EVIDENCE_TASK`` schema: a closed record of the A103 whole-axis findings task."""
    if (not isinstance(value, dict) or set(value) != {'version', 'kind', 'evidence_axis', 'credit_unit'}
            or value['version'] != EVIDENCE_TASK_VERSION or value['kind'] != 'whole_axis_findings'
            or value['evidence_axis'] != AXIS or isinstance(value['credit_unit'], bool)
            or not isinstance(value['credit_unit'], (int, float)) or not value['credit_unit'] > 0):
        raise ValueError('scientific_evidence_task_invalid')


def read_from_parent(assignment, message):
    selection = validate_selection(assignment['selection'])
    if selection['evidence_axis']['option_id'] != AXIS:
        raise ValueError('scientific_selection_evidence_axis_must_be_' + AXIS)
    proposed = assignment.get('proposed_annotation_ref')
    if proposed is None or len(proposed) != 1:
        raise ValueError('scientific_task_proposed_annotation_required')
    context = assignment['context']
    if 'evidence_task' in context:
        _evidence_task(context['evidence_task'])
    task = context.get('a103_task')
    if task is not None and (not isinstance(task, dict) or not isinstance(task.get('name'), str)
                             or not task['name']):
        raise ValueError('scientific_continuation_original_task_required')
    parent_input = {'selection': selection, 'proposed_annotation_ref': proposed[0],
                    'evidence_refs': list(assignment['evidence_refs']), 'constraints': assignment['constraints'],
                    'context': context, 'scope': assignment['scope'], 'scope_refs': list(assignment['scope_refs']),
                    'a103_task_name': None if task is None else task['name'], 'message': message}
    if 'revision_origin' in assignment:
        parent_input['revision_origin'] = validate_revision_origin(assignment['revision_origin'])
    return parent_input
