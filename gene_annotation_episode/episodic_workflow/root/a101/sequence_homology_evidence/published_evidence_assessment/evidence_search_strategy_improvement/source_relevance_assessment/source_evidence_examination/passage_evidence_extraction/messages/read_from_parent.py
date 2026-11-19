"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the spans
to read), the Store scope of the commission and the records passed in custody.

``version``, ``page`` and ``selection`` are the old assignment's properties under their names. ``scope`` and
``received_record_refs`` are new fields: the old episode took the scope from its request and the records it
received from its binding context; the new commission names both in its assignment."""
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
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact and the sources it derives from, passed '
                                  'in custody (new field: old binding-context received records)'),
})


def read_from_parent(assignment, message):
    """The parent input: the page, the spans, the scope and the passed records, each span checked against the
    page (the old assignment validation that needs no Store)."""
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
    return {'page': page, 'spans': spans, 'scope': assignment['scope'],
            'received_record_refs': assignment['received_record_refs'], 'message': message}
