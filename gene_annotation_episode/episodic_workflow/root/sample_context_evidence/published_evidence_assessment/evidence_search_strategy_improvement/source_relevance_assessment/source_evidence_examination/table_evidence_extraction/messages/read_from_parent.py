"""What the parent gives: the reading assignment ``reading_assignment`` (the page of one source and the one table
region of it to extract: a window of the page's representation that holds the table), the commissioned A108 literature task
(``verified_source_leads``, the only task accepted), the proposed annotation, the A108 grading components whose cells the
parent will ask for, the Store scope of the commission and the records passed in custody. This is the only place the
assignment is read. The table's text is not passed: it is read from the artifact of the page's representation."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    COMPONENTS as GRADING_COMPONENTS)

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')
REQUESTED_GRADING = 'requested_a108_grading_components'

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment'),
    'source_ref': Field('text', 'The source being read'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier readings of this source'),
})
SELECTION_FORM = RecordForm({
    'source_ref': Field('text', 'The source of the table region; the page source'),
    'representation': ChoiceField('text', 'The representation the offsets count in', REPRESENTATIONS),
    'offset': Field('integer', 'First byte of the window that holds the table region (0 or more)'),
    'limit': Field('integer', 'Bytes of the window (1 or more)'),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The table region of that source to extract', form=SELECTION_FORM),
    'literature_task': Field('record', 'The commissioned A108 literature task: kind verified_source_leads, '
                             'evidence_axis (A108) and credit_unit'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    REQUESTED_GRADING: SubsetField('text', 'The A108 contextual grading components the parent wants returned',
                                   GRADING_COMPONENTS, required=False),
    'scope': Field('record', 'The Store scope of the commission'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'proposed annotation, passed in custody'),
})

TASK_KIND = 'verified_source_leads'


def task_key(task):
    return task['evidence_axis'] + ':' + task['kind']


def read_from_parent(assignment, message):
    """The parent input: the page, the one table region (as the one window of ``spans``), the task, the proposed
    annotation, the requested components, the scope and the passed records, the region checked against the page."""
    page, selection = assignment['page'], assignment['selection']
    if selection['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if selection['representation'] != page['representation']:
        raise ValueError('literature_reading_representation_mismatch')
    if selection['offset'] < 0 or selection['limit'] < 1:
        raise ValueError('literature_reading_window_out_of_range')
    task = assignment['literature_task']
    if task.get('kind') != TASK_KIND or task.get('evidence_axis') != 'A108':
        raise ValueError('literature_original_task_invalid')
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not math.isfinite(unit) or not unit > 0:
        raise ValueError('literature_finite_task_credit_unit_required')
    return {'page': page, 'spans': [selection], 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            REQUESTED_GRADING: list(assignment.get(REQUESTED_GRADING, [])),
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
