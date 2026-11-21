"""What the parent gives: the page assignment ``page_assignment_v1`` (ONE paper in one representation, by its source
reference), the commissioned A108 literature task (``verified_source_leads``, the only task), the proposed annotation, the
A108 grading and aggregation components the parent wants returned, the Store scope of the commission and the records passed
in custody. This is the only place the assignment is read.

``version``, ``source_ref``, ``representation``, ``artifact_ref``, ``question_context_refs`` and ``prior_delivery_refs`` are
the properties of the old page schema; ``literature_task``, ``proposed_annotation_ref`` and the two requested-component
properties are the old assignment's other properties, all under their names. ``scope`` and ``received_record_refs`` are
new fields: the commission names the Store scope and the records passed in custody.

Any task other than ``verified_source_leads`` is a wrong commission: the form's schema refuses it and the run fails."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_aggregation import (
    COMPONENTS as AGGREGATION_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    COMPONENTS as GRADING_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError, obj, validate_schema)

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')
REQUESTED_GRADING = 'requested_a108_grading_components'
REQUESTED_AGGREGATION = 'requested_a108_aggregation_components'
VERSION = 'literature_local_task_v1'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The paper to examine'),
    'representation': ChoiceField('text', 'The representation of the paper that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The paper's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier examinations of this paper'),
    'literature_task': Field('record', 'The commissioned A108 literature task: version, evidence_axis A108, '
                             'credit_unit and kind verified_source_leads'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    REQUESTED_GRADING: SubsetField('text', 'The A108 contextual grading components the parent wants returned',
                                   GRADING_COMPONENTS, required=False),
    REQUESTED_AGGREGATION: SubsetField('text', 'The A108 aggregation components the parent wants returned',
                                       AGGREGATION_COMPONENTS, required=False),
    'scope': Field('record', 'The Store scope of the commission'),
    'received_record_refs': Field('record_refs', 'The paper, its artifact, the sources it derives from and the '
                                  'proposed annotation, passed in custody'),
})


def task_key(task):
    """``<axis>:<kind>``: the one task is ``A108:verified_source_leads``."""
    return task['evidence_axis'] + ':' + task['kind']


def task_schema():
    """The commissioned A108 task: ``verified_source_leads`` with its credit unit."""
    return obj({'version': {'const': VERSION}, 'evidence_axis': {'const': 'A108'},
                'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'kind': {'const': 'verified_source_leads'}})


def commissioned_task(assignment):
    """The task against its schema, a finite credit unit and the proposed annotation."""
    task = assignment['literature_task']
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    if not isinstance(assignment['proposed_annotation_ref'], str):
        raise ContractError('literature_original_proposed_annotation_required')
    return task


def read_from_parent(assignment, message):
    """The parent input: the page, the task, the proposed annotation, the requested components, the scope and the
    passed records."""
    task = commissioned_task(assignment)
    page = {name: assignment[name] for name in ('version', 'source_ref', 'representation', 'artifact_ref',
                                                'question_context_refs', 'prior_delivery_refs')}
    return {'page': page, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            REQUESTED_GRADING: assignment.get(REQUESTED_GRADING, []),
            REQUESTED_AGGREGATION: assignment.get(REQUESTED_AGGREGATION, []),
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
