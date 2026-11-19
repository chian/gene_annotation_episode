"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the spans to
read), the commissioned literature task, the proposed annotation, the structure components requested, the Store
scope of the commission and the records passed in custody.

``version``, ``page``, ``selection``, ``literature_task``, ``proposed_annotation_ref``
are the old assignment's properties under their names (old ``from_parent.py``
``assignment_schema``). ``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from
its request and the records it received from its binding context; the new commission names both."""
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
    'source_ref': Field('text', 'The source of the passage; the page source'),
    'representation': ChoiceField('text', 'The representation the offsets count in', REPRESENTATIONS),
    'offset': Field('integer', 'First byte of the passage (0 or more)'),
    'limit': Field('integer', 'Bytes of the passage (1 or more)'),
})
SELECTION_FORM = RecordForm({
    'spans': Field('list', 'The passages to investigate: one or more windows', items=WINDOW_FORM),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The passages of that source to investigate', form=SELECTION_FORM),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads or '
                             'source_answer), evidence_axis, credit_unit and, for a source answer, answer_kind '
                             'with its source_refs (assessment) or examined spans (screening)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'proposed annotation, passed in custody (new field: old binding-context '
                                  'received records)'),
})

TASK_KINDS = ('verified_source_leads', 'source_answer')
ANSWER_KINDS = ('assessment', 'screening')


def task_key(task):
    """The old ``_task_key``: ``<axis>:<kind>`` and, for a source answer, ``:<answer_kind>``."""
    name = task['kind']
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def read_from_parent(assignment, message):
    """The parent input: the page, the spans, the task, the proposed annotation, the scope and the passed records,
    each span checked against the page (the old assignment validation that needs no Store)."""
    page, spans = assignment['page'], assignment['selection']['spans']
    if not spans:
        raise ValueError('reading_assignment_requires_a_span')
    for window in spans:
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
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not unit > 0 or unit == float('inf'):
        raise ValueError('literature_finite_task_credit_unit_required')
    return {'page': page, 'spans': spans, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs']}
