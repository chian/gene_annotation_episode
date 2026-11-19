"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and either a
table selection or a byte window to begin with), the Store scope of the commission, the finding unit of its
credit and the records passed in custody.

``version``, ``page`` and ``selection`` are the properties of the old assignment schema (old ``from_parent.py``),
under their names. The old ``selection`` was ``anyOf`` a table selection or a byte window; a form has no union, so
``selection`` is one open record that ``read_from_parent`` admits against exactly one of the two forms below. A null
``header_row`` or ``where`` of the old table selection (and a null ``column``) is the field omitted (a form has no
null). The old schema also took the requested partner component fields of ``partner_source_contracts.
assignment_schema_fields()``; that module is gone from the library, so those fields are not declared here (reported).
``scope``, ``received_record_refs`` and ``finding_unit`` are new fields: the old episode took the scope from its
request, the records it had received from its binding context and its credit unit from the old runner's credit
service; the new commission names them in its assignment.
The old checks of this file that needed the Store (the page's artifact against the source, the offset against the
artifact's size, the references in scope, the source descending from the parent's page) are not carried: they were
this episode's checks of its own commission, and a wrong commission fails."""
from method_loop import ChoiceField, DeclaredField, Field, FormError, RecordForm

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
WHERE_FORM = RecordForm({
    'column': Field('text', 'Column letters; omitted for any column', required=False),
    'match': ChoiceField('text', 'How the value is matched', ('equals', 'contains')),
    'value': Field('text', 'The literal cell value to match'),
    'case_sensitive': Field('boolean', 'Whether the match is case sensitive'),
})
TABLE_FORM = RecordForm({
    'source_ref': Field('text', 'The source of the table; the page source'),
    'sheet_key': Field('text', 'The sheet of the workbook that is examined'),
    'offset': Field('integer', 'Matching rows to skip (0 or more)'),
    'limit': Field('integer', 'Rows to read (0 or more)'),
    'header_row': Field('integer', 'The caller-selected header row (1 or more); omitted for none', required=False),
    'where': Field('record', 'The literal cell filter of the rows; omitted for none', form=WHERE_FORM,
                   required=False),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'Either a table selection (source_ref, sheet_key, offset, limit, header_row, '
                       'where) or a byte window (source_ref, representation, offset, limit) to begin reading at'),
    'scope': Field('record', 'The Store scope of the commission (new field: the old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact and the sources it derives from, passed '
                                  'in custody (new field: the old binding-context received records)'),
    'finding_unit': Field('number', 'The credit of one retained finding (new field: the old runner supplied the '
                          'A107 finding unit to its credit service)'),
})


def admitted_selection(selection):
    """The selection as exactly one of the two old alternatives (a record with a ``sheet_key`` is a table
    selection, otherwise a byte window); a record that fits neither form raises."""
    if not isinstance(selection, dict):
        raise FormError('selection_must_be_a_record')
    if 'sheet_key' in selection:
        return TABLE_FORM.admit(selection, 'selection')
    return WINDOW_FORM.admit(selection, 'selection')


def read_from_parent(assignment, message):
    """The parent input: the page, the selection, the scope, the finding unit and the passed records. The selection
    must be of the page's source and, for a byte window, of the page's representation and begin at a non-negative
    offset with a positive limit (the old ``_validate_assignment`` checks that need no Store); each raises."""
    page = assignment['page']
    selection = admitted_selection(assignment['selection'])
    if selection['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if 'representation' in selection:
        if selection['representation'] != page['representation']:
            raise ValueError('literature_reading_representation_mismatch')
        if selection['offset'] < 0 or selection['limit'] < 1:
            raise ValueError('literature_reading_window_out_of_range')
    elif selection['offset'] < 0 or selection['limit'] < 0:
        raise ValueError('literature_reading_table_out_of_range')
    return {'page': page, 'selection': selection, 'scope': assignment['scope'],
            'received_record_refs': assignment['received_record_refs'],
            'finding_unit': assignment['finding_unit'], 'message': message}
