"""What the parent gives: the source being read (a page), the window where document-order reading starts, the
scope, and the records passed in custody. This is the only place the assignment is read."""
from method_loop import DeclaredField, Field, RecordForm

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source being read'),
    'representation': Field('text', 'The representation of the source read: text, original, stdout or stderr'),
    'artifact_ref': Field('text', "The source's artifact of that representation"),
    'question_context_refs': Field('list', 'References to the question context records'),
    'prior_delivery_refs': Field('list', 'References to prior deliveries'),
})
WINDOW_FORM = RecordForm({
    'source_ref': Field('text', "The window's source: the page's source"),
    'representation': Field('text', "The window's representation: the page's representation"),
    'offset': Field('integer', 'The UTF-8 byte offset where document-order reading starts, at least 0'),
    'limit': Field('integer', 'The UTF-8 byte length of the first window, at least 1'),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The one window where document-order reading starts', form=WINDOW_FORM),
    # New fields the final form needs (the old code read them from the commissioning request, not the assignment).
    'scope': Field('record', "The fixed scope of the investigation: the parent's fixed subject and optional segments"),
    'record_refs': Field('record_refs', 'Every record this episode reads: the source, its artifact, the question '
                                        'context and prior delivery records, and the sources the source derives from'),
    'gene_context_evidence': Field('record', "The parent's constraints, context, evidence operands and guidance",
                                   required=False),
})


def read_from_parent(assignment, message):
    """The assignment as the parent input. The old assignment's own constraints are checked here, where the
    assignment is read: representation choices, offset at least 0, limit at least 1, and the window names the
    page's source and representation."""
    page, window = assignment['page'], assignment['selection']
    for name, representation in (('page', page['representation']), ('window', window['representation'])):
        if representation not in REPRESENTATIONS:
            raise ValueError('a103_' + name + '_representation_unknown:' + repr(representation))
    if window['source_ref'] != page['source_ref']:
        raise ValueError('literature_reading_source_mismatch')
    if window['representation'] != page['representation']:
        raise ValueError('literature_reading_representation_mismatch')
    if window['offset'] < 0:
        raise ValueError('window_offset_must_be_a_natural_number')
    if window['limit'] < 1:
        raise ValueError('window_limit_must_be_positive')
    parent_input = {'version': assignment['version'], 'page': page, 'selection': window,
                    'scope': assignment['scope'], 'record_refs': assignment['record_refs']}
    if 'gene_context_evidence' in assignment:
        parent_input['gene_context_evidence'] = assignment['gene_context_evidence']
    return parent_input
