"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the chunks of it to
extract, each a byte window), the commissioned literature task (``verified_source_leads`` only), the proposed annotation,
the Store scope of the commission and the records passed in custody. The chunk's text is not passed: it is read from the
artifact of the page. This is the only place the assignment is read. A task of another kind, or a window that is not of the
page's source and representation, is a wrong commission and fails here."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

REPRESENTATIONS = ('text', 'original')      # the representations a witness of the perturbation form can name

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source being read'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier readings of this source'),
})
WINDOW_FORM = RecordForm({
    'source_ref': Field('text', 'The source of the chunk; the page source'),
    'representation': ChoiceField('text', 'The representation the offsets count in', REPRESENTATIONS),
    'offset': Field('integer', 'First byte of the chunk (0 or more)'),
    'limit': Field('integer', 'Bytes of the chunk (1 or more)'),
})
SELECTION_FORM = RecordForm({
    'spans': Field('list', 'The chunks to extract, in order: one or more windows', items=WINDOW_FORM),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The chunks of that source to extract', form=SELECTION_FORM),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads), '
                             'evidence_axis and credit_unit'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    'scope': Field('record', 'The Store scope of the commission'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'proposed annotation, passed in custody'),
})


def read_from_parent(assignment, message):
    """The parent input: the page, the chunks, the task, the proposed annotation, the scope and the passed records, each
    chunk checked against the page."""
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
    if task.get('kind') != 'verified_source_leads' or task.get('evidence_axis') != 'A106':
        raise ValueError('literature_original_task_invalid')
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not math.isfinite(unit) or not unit > 0:
        raise ValueError('literature_finite_task_credit_unit_required')
    return {'page': page, 'spans': spans, 'task': task, 'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
