"""What the parent gives: the literature assignment ``literature_assignment`` (the records that give the question its
context), the commissioned A108 literature task (the verified source leads, the one task kind), the proposed
annotation, the A108 grading and aggregation components the parent wants returned, the Store scope of the commission
and the records passed in custody. This is the only place the assignment is read. No source and no search is handed
in: the literature chain finds its own papers.

``version`` and ``question_context_refs`` are the properties of the old assignment schema (old ``from_parent.py``
``assignment_schema('literature')``); ``literature_task``, ``proposed_annotation_ref`` and the two requested-component
properties are its other properties (``goal.task_schema`` and the grading/aggregation ``REQUESTED`` properties), all
under their names. ``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from its
request and the records it received from its binding context; the new commission names both.

Carried here from the old ``goal.py`` (private copies, library candidates): ``_task_key``, ``task_schema`` and
``commissioned_task``. Any other task kind is a wrong commission and fails where the form reads it. Not carried: the
checks of the old ``commissioned_task`` against the request's report contract and the Store checks of the old
assignment validation: they check a commission, and a wrong commission fails where its records are read."""
import math

from method_loop import DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_aggregation import (
    COMPONENTS as AGGREGATION_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    COMPONENTS as GRADING_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError, obj, validate_schema)

REQUESTED_GRADING = 'requested_a108_grading_components'
REQUESTED_AGGREGATION = 'requested_a108_aggregation_components'
VERSION = 'literature_local_task'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The literature assignment version', 'literature_assignment'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'literature_task': Field('record', 'The commissioned A108 literature task: version, evidence_axis A108, '
                             'credit_unit, and its kind verified_source_leads'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    REQUESTED_GRADING: SubsetField('text', 'The A108 contextual grading components the parent wants returned',
                                   GRADING_COMPONENTS, required=False),
    REQUESTED_AGGREGATION: SubsetField('text', 'The A108 aggregation components the parent wants returned',
                                       AGGREGATION_COMPONENTS, required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The records the episode reads that the lists above do not name: '
                                  'the proposed annotation, the hypothesis and subjects it names and the scope '
                                  'subjects, passed in custody (new field: old binding-context received records)'),
})


def task_key(task):
    """The old ``_task_key``: ``<axis>:<kind>``."""
    return task['evidence_axis'] + ':' + task['kind']


def task_schema():
    """The old ``goal.task_schema`` of the commissioned A108 result without the old ``yield_settings`` property: the
    verified source leads, the only task kind."""
    return obj({'version': {'const': VERSION}, 'evidence_axis': {'const': 'A108'},
                'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'kind': {'const': 'verified_source_leads'}})


def commissioned_task(assignment):
    """The old ``commissioned_task`` over the assignment alone: the task against its schema, a finite credit unit and
    the proposed annotation."""
    task = assignment['literature_task']
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    if not isinstance(assignment['proposed_annotation_ref'], str):
        raise ContractError('literature_original_proposed_annotation_required')
    return task


def read_from_parent(assignment, message):
    """The parent input: the question context, the task, the proposed annotation, the requested components, the scope
    and the passed records."""
    task = commissioned_task(assignment)
    return {'question_context_refs': assignment['question_context_refs'], 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            REQUESTED_GRADING: assignment.get(REQUESTED_GRADING, []),
            REQUESTED_AGGREGATION: assignment.get(REQUESTED_AGGREGATION, []),
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
