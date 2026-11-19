"""What the parent gives: a reading assignment (the page of one source and one or more selected passages), the
records passed in custody, and the scope and finding unit the episode's credit is measured over.

Old schema ``reading_assignment_v1``: ``{version, page, selection: {spans: [>=1 window]}}`` plus the partner
fields of the old ``partner_source_contracts.assignment_schema_fields()``. That module was not placed in the
library: its field names are not known to this file (see ``partner_components`` below). The fields
``held_refs``, ``scope`` and ``finding_unit`` are new: the old runner handed the scope and the passed records
through its binding context, which no longer exists."""
from method_loop import ChoiceField, DeclaredField, Field, RecordForm

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source this reading is about'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', 'The artifact of that representation of the source'),
    'question_context_refs': Field('list', 'References to the records that state the question'),
    'prior_delivery_refs': Field('list', 'References to earlier deliveries about this source'),
})
WINDOW_FORM = RecordForm({
    'source_ref': Field('text', 'The source of the passage'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'offset': Field('integer', 'The zero-based UTF-8 byte offset of the passage'),
    'limit': Field('integer', 'The number of bytes of the passage'),
})
SELECTION_FORM = RecordForm({
    'spans': Field('list', 'The selected passages; separate spans stay separate', items=WINDOW_FORM),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source page this reading belongs to', form=PAGE_FORM),
    'selection': Field('record', 'The passages to read', form=SELECTION_FORM),
    'partner_components': Field('list', 'The partner components the parent wants cells for (the old requested '
                                        'component field of the partner population route; name not verified)',
                                required=False),
    'held_refs': Field('record_refs', 'Every record this episode reads: the source and its artifact, the sources '
                                      'it descends from, the question and prior delivery records and the subjects '
                                      'of the scope'),
    'scope': Field('record', 'The scope the findings of this episode are measured over'),
    'finding_unit': Field('number', 'The credit of one distinct retained finding'),
})


def read_from_parent(assignment, message):
    page = assignment['page']
    spans = assignment['selection']['spans']
    if not spans:
        raise ValueError('literature_reading_requires_a_span')
    for window in spans:
        if window['source_ref'] != page['source_ref']:
            raise ValueError('literature_reading_source_mismatch')
        if window['representation'] != page['representation']:
            raise ValueError('literature_reading_representation_mismatch')
    return {'page': page, 'spans': spans,
            'partner_components': assignment['partner_components'] if 'partner_components' in assignment else None,
            'scope': assignment['scope'], 'finding_unit': assignment['finding_unit']}
