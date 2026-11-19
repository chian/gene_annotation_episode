"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the one
window where document-order reading starts), the commissioned literature task, the proposed annotation, the Store
scope of the commission and the records passed in custody. This is the only place the assignment is read.

``version``, ``page``, ``selection``, ``literature_task`` and ``proposed_annotation_ref`` are the old assignment's
properties under their names (old ``from_parent.py`` ``assignment_schema`` and ``assignment_fields.py``).
``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from its request and the
records it received from its binding context; the new commission names both. The old rate-population properties
(``requested_*_components``, ``requested_*_views``, ``requested_*_component_keys``) exist only under the old
``rate_population`` configuration, which is off by default and not built here: a commission that sends one is
refused by this form."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source being read'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier readings of this source'),
})
WINDOW_FORM = RecordForm({
    'source_ref': Field('text', "The window's source: the page's source"),
    'representation': ChoiceField('text', "The window's representation: the page's representation", REPRESENTATIONS),
    'offset': Field('integer', 'The UTF-8 byte offset where document-order reading starts (0 or more)'),
    'limit': Field('integer', 'The UTF-8 byte length of the first window (1 or more)'),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The one window where document-order reading starts', form=WINDOW_FORM),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads, '
                             'source_answer, a105_experiments or a105_assembly), evidence_axis, credit_unit and, '
                             'for a source answer, answer_kind with its source_refs (assessment), examined spans '
                             '(screening) or selection and components (measurement)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from, the '
                                  'question context and prior delivery records and the proposed annotation, passed '
                                  'in custody (new field: old binding-context received records)'),
})

TASK_KINDS = ('verified_source_leads', 'source_answer', 'a105_experiments', 'a105_assembly')
ANSWER_KINDS = ('assessment', 'screening', 'measurement')


def task_key(task):
    """The old ``_task_key``: ``<axis>:<name>`` where the name is the kind (``a105_experiments`` is
    ``experiments``, ``a105_assembly`` is ``assembly``) and, for a source answer, ``:<answer_kind>`` follows."""
    name = {'a105_experiments': 'experiments', 'a105_assembly': 'assembly'}.get(task['kind'], task['kind'])
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def read_from_parent(assignment, message):
    """The parent input: the page, the window, the task, the proposed annotation, the scope and the passed records.
    The window is checked against the page (the old ``_validate_assignment`` checks that need no Store)."""
    page, window = assignment['page'], assignment['selection']
    if window['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if window['representation'] != page['representation']:
        raise ValueError('literature_reading_representation_mismatch')
    if window['offset'] < 0 or window['limit'] < 1:
        raise ValueError('literature_reading_window_out_of_range')
    task = assignment['literature_task']
    if task.get('kind') not in TASK_KINDS or (task['kind'] == 'source_answer'
                                              and task.get('answer_kind') not in ANSWER_KINDS):
        raise ValueError('literature_original_task_invalid')
    if not isinstance(task.get('evidence_axis'), str) or not task['evidence_axis']:
        raise ValueError('literature_original_task_invalid')
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not math.isfinite(unit) or not unit > 0:
        raise ValueError('literature_finite_task_credit_unit_required')
    if task['kind'] == 'a105_experiments':
        experiments = [item['experiment_ref'] for item in task['experiments']]
        if not experiments or len(set(experiments)) != len(experiments):
            raise ValueError('literature_task_duplicate_experiment')
    return {'page': page, 'window': window, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
