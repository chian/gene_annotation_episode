"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the one window
to start reading from, in document order), the commissioned literature task, the proposed annotation, the A108
components whose cells the parent will ask for, the Store scope of the commission and the records passed in
custody. This is the only place the assignment is read.

``version``, ``page``, ``selection``, ``literature_task``, ``proposed_annotation_ref`` and the two requested
component lists are the old assignment's properties under their names (old ``from_parent.py``
``LiteratureAssignment.assignment_schema``). ``scope`` and ``received_record_refs`` are new fields: the old episode
took the scope from its request and the records it received from its binding context; the new commission names
both. ``task_schema`` and the task checks of ``read_from_parent`` are the old ``goal.py`` ``task_schema`` and
``commissioned_task`` (the checks that need no Store and no request)."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_aggregation import (
    COMPONENTS as AGGREGATION_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    COMPONENTS as GRADING_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    REF, obj, validate_schema)

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')
VERSION = 'literature_local_task_v1'
GRADING_REQUESTED = 'requested_a108_grading_components'
AGGREGATION_REQUESTED = 'requested_a108_aggregation_components'

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source being read'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier readings of this source'),
})
WINDOW_FORM = RecordForm({
    'source_ref': Field('text', 'The source of the window; the page source'),
    'representation': ChoiceField('text', 'The representation the offsets count in', REPRESENTATIONS),
    'offset': Field('integer', 'First byte of the window to start reading from (0 or more)'),
    'limit': Field('integer', 'Bytes of the window (1 or more)'),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The window of that source to start reading from, in document order',
                       form=WINDOW_FORM),
    'literature_task': Field('record', 'The commissioned literature task (evidence_axis A108): verified_source_leads, '
                             'or source_answer with answer_kind assessment (source_refs) or screening (examined '
                             'spans); with its credit_unit'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    GRADING_REQUESTED: Field('list', 'The A108 grading components whose cells the parent will ask for',
                             required=False),
    AGGREGATION_REQUESTED: Field('list', 'The A108 aggregation components whose cells the parent will ask for',
                                 required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'proposed annotation, passed in custody (new field: old binding-context '
                                  'received records)'),
})


def task_schema():
    """The old ``goal.task_schema``: the commissioned A108 result and its explicit local credit unit. A108 score
    computation is automatic work, not an episode-credit task."""
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']},
                          'cutoff': {'type': 'number', 'minimum': 0},
                          'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    base = {'version': {'const': VERSION}, 'evidence_axis': {'const': 'A108'},
            'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'yield_settings': yield_settings}

    def task_object(properties):
        return obj(properties, required=[key for key in properties if key != 'yield_settings'])
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0},
                'end': {'type': 'integer', 'minimum': 1}})
    return {'anyOf': [task_object({**base, 'kind': {'const': 'verified_source_leads'}}),
                      task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'},
                                   'source_refs': refs}),
                      task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'},
                                   'examined': {'type': 'array', 'minItems': 1, 'items': span}})]}


def task_key(task):
    """The old ``goal._task_key``: ``<axis>:<kind>`` and, for a source answer, ``:<answer_kind>``."""
    name = task['kind']
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def requested_components(assignment, name, allowed):
    selected = assignment.get(name, [])
    if len(set(selected)) != len(selected) or any(item not in allowed for item in selected):
        raise ValueError('a108_component_selection_invalid:' + name)
    return list(selected)


def read_from_parent(assignment, message):
    """The parent input: the page, the window, the task with its key, the proposed annotation, the requested
    components, the scope and the passed records. The window is checked against the page (old
    ``_validate_assignment``) and the task against the page (old ``commissioned_task``)."""
    page, window = assignment['page'], assignment['selection']
    if window['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if window['representation'] != page['representation']:
        raise ValueError('literature_reading_representation_mismatch')
    if window['offset'] < 0 or window['limit'] < 1:
        raise ValueError('literature_reading_window_out_of_range')
    task = assignment['literature_task']
    validate_schema(task, task_schema())
    unit = task['credit_unit']
    if type(unit) not in (int, float) or not math.isfinite(unit):
        raise ValueError('literature_finite_task_credit_unit_required')
    for span in task.get('examined', ()):
        if span['end'] <= span['start']:
            raise ValueError('literature_task_screening_span_invalid')
    selected_sources = task.get('source_refs', []) + [span['source_ref'] for span in task.get('examined', [])]
    if any(ref != page['source_ref'] for ref in selected_sources):
        raise ValueError('literature_task_outside_assigned_source')
    if task.get('answer_kind') == 'screening' and any(span['artifact_ref'] != page['artifact_ref']
                                                      for span in task['examined']):
        raise ValueError('literature_task_screening_artifact_mismatch')
    return {'page': page, 'window': window, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            GRADING_REQUESTED: requested_components(assignment, GRADING_REQUESTED, GRADING_COMPONENTS),
            AGGREGATION_REQUESTED: requested_components(assignment, AGGREGATION_REQUESTED, AGGREGATION_COMPONENTS),
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
