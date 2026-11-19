"""What the parent gives: the page assignment ``page_assignment_v1`` (one source in one representation), the
commissioned A108 literature task, the proposed annotation, the A108 grading and aggregation components the parent wants
returned, the Store scope of the commission and the records passed in custody. This is the only place the assignment is
read.

``version``, ``source_ref``, ``representation``, ``artifact_ref``, ``question_context_refs`` and ``prior_delivery_refs``
are the properties of the old page schema (old ``from_parent.py`` ``_PAGE``); ``literature_task``,
``proposed_annotation_ref`` and the two requested-component properties are the old assignment's other properties
(``goal.task_schema`` and the grading/aggregation ``REQUESTED`` properties), all under their names. The old assignment
was itself the page (``assignment.get('page', assignment)``). ``scope`` and ``received_record_refs`` are new fields: the
old episode took the scope from its request and the records it received from its binding context; the new commission
names both. The old ``yield_settings`` of the task (filled from the owner's yield bindings) are this episode's
settings now, not assignment fields.

Carried here from the old ``goal.py`` (private copies, library candidates): ``_task_key``, ``task_schema`` and
``commissioned_task`` (its checks that need no request or Store). The old ``_yield_kind`` (which controller a task
uses) is the choice made in ``yield_estimator.py``.
Not carried: the checks of the old ``commissioned_task`` against the request's report contract
(``literature_task_typed_return_mismatch``, ``literature_task_return_components_mismatch``,
``literature_task_original_commission_mismatch``) and the Store checks of the old assignment validation (``_validate_page``:
the source and the context and delivery references in scope, the artifact against the source's artifact for the
representation, the child's proposed annotation equal to the parent's): they check a commission, and a wrong commission
fails where its records are read."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_aggregation import (
    COMPONENTS as AGGREGATION_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    COMPONENTS as GRADING_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError, REF, obj, validate_schema)

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')
REQUESTED_GRADING = 'requested_a108_grading_components'
REQUESTED_AGGREGATION = 'requested_a108_aggregation_components'
VERSION = 'literature_local_task_v1'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source to examine'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier examinations of this source'),
    'literature_task': Field('record', 'The commissioned A108 literature task: version, evidence_axis A108, '
                             'credit_unit, and its kind (verified_source_leads, or source_answer with answer_kind '
                             'assessment and source_refs, or screening and the examined spans)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    REQUESTED_GRADING: SubsetField('text', 'The A108 contextual grading components the parent wants returned',
                                   GRADING_COMPONENTS, required=False),
    REQUESTED_AGGREGATION: SubsetField('text', 'The A108 aggregation components the parent wants returned',
                                       AGGREGATION_COMPONENTS, required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'proposed annotation, passed in custody (new field: old binding-context '
                                  'received records)'),
})


def task_key(task):
    """The old ``_task_key``: ``<axis>:<name>`` where the name is the kind and, for a source answer,
    ``:<answer_kind>`` follows."""
    name = task['kind']
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def task_schema():
    """The old ``goal.task_schema`` of the commissioned A108 result without the old ``yield_settings`` property
    (this episode's settings carry the cutoff and the uncertainty)."""
    base = {'version': {'const': VERSION}, 'evidence_axis': {'const': 'A108'},
            'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}}
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0},
                'end': {'type': 'integer', 'minimum': 1}})
    return {'anyOf': [
        obj({**base, 'kind': {'const': 'verified_source_leads'}}),
        obj({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'},
             'source_refs': refs}),
        obj({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'},
             'examined': {'type': 'array', 'minItems': 1, 'items': span}})]}


def commissioned_task(assignment):
    """The old ``commissioned_task`` over the assignment alone: the task against its schema, a finite credit unit, the
    proposed annotation, the screening spans, and the task's sources and artifact against the assigned page (the old
    ``assigned_page = assignment.get('page', assignment)``: for this episode the assignment is itself the page)."""
    task = assignment['literature_task']
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    if not isinstance(assignment['proposed_annotation_ref'], str):
        raise ContractError('literature_original_proposed_annotation_required')
    for span in task.get('examined', ()):
        if span['end'] <= span['start']:
            raise ContractError('literature_task_screening_span_invalid')
    page = assignment
    selected = task.get('source_refs', []) + [span['source_ref'] for span in task.get('examined', [])]
    if any(ref != page['source_ref'] for ref in selected):
        raise ContractError('literature_task_outside_assigned_source')
    if task.get('answer_kind') == 'screening' and any(span['artifact_ref'] != page['artifact_ref']
                                                      for span in task['examined']):
        raise ContractError('literature_task_screening_artifact_mismatch')
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
