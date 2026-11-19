"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the byte
window to begin with), the Store scope of the commission and the records passed in custody.

``version``, ``page`` and ``selection`` are the properties of the old assignment schema (old ``from_parent.py``),
under their names. ``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from its
request and the records it had received from its binding context; the new commission names both in its assignment.
The old checks of this file that needed the Store (the page's artifact against the source, the offset against the
artifact's size, the references in scope, the source descending from the parent's page) are not carried: they were
this episode's checks of its own commission, and a wrong commission fails (see the carried-over table)."""
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
    'source_ref': Field('text', 'The source of the window; the page source'),
    'representation': ChoiceField('text', 'The representation the offsets count in', REPRESENTATIONS),
    'offset': Field('integer', 'First byte of the window (0 or more)'),
    'limit': Field('integer', 'Bytes of the window (1 or more)'),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The byte window of that source to begin reading at', form=WINDOW_FORM),
    'scope': Field('record', 'The Store scope of the commission (new field: the old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact and the sources it derives from, passed '
                                  'in custody (new field: the old binding-context received records)'),
})


def read_from_parent(assignment, message):
    """The parent input: the page, the window, the scope and the passed records. The window must be of the page's
    source and representation, and begin at a non-negative offset with a positive limit (the old
    ``_validate_assignment`` checks that need no Store); each raises."""
    page, window = assignment['page'], assignment['selection']
    if window['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if window['representation'] != page['representation']:
        raise ValueError('literature_reading_representation_mismatch')
    if window['offset'] < 0 or window['limit'] < 1:
        raise ValueError('literature_reading_window_out_of_range')
    return {'page': page, 'window': window, 'scope': assignment['scope'],
            'received_record_refs': assignment['received_record_refs'], 'message': message}
