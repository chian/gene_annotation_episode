"""What the parent gives: the source being read (a page), the passages (spans) to investigate, the scope, and the
records passed in custody. This is the only place the assignment is read."""
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
    'offset': Field('integer', 'The byte offset of the passage, at least 0'),
    'limit': Field('integer', 'The byte length of the passage, at least 1'),
})
SELECTION_FORM = RecordForm({
    'spans': Field('list', 'One or more separate passages (windows) of the source to investigate', items=WINDOW_FORM),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The passages to investigate', form=SELECTION_FORM),
    # New fields the final form needs (the old code read them from the commissioning request, not the assignment).
    'scope': Field('record', "The fixed scope of the investigation: the parent's fixed subject and optional segments"),
    'record_refs': Field('record_refs', 'Every record this episode reads: the source, its artifact, the question '
                                        'context and prior delivery records, and the sources the source derives from'),
    'gene_context_evidence': Field('record', "The parent's constraints, context, evidence operands and guidance",
                                   required=False),
})


def _natural(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(name + '_must_be_a_natural_number')


def read_from_parent(assignment, message):
    """The assignment as the parent input: the old assignment schema's own constraints (representation choices,
    at least one span, offset at least 0, limit at least 1) are checked here, where the assignment is read."""
    page, spans = assignment['page'], assignment['selection']['spans']
    for name, representation in [('page', page['representation'])] + [('span', span['representation'])
                                                                       for span in spans]:
        if representation not in REPRESENTATIONS:
            raise ValueError('a103_' + name + '_representation_unknown:' + repr(representation))
    if not spans:
        raise ValueError('a103_selection_requires_at_least_one_span')
    for span in spans:
        _natural(span['offset'], 'span_offset')
        if span['limit'] < 1:
            raise ValueError('span_limit_must_be_positive')
    parent_input = {'version': assignment['version'], 'page': page, 'selection': assignment['selection'],
                    'scope': assignment['scope'], 'record_refs': assignment['record_refs']}
    if 'gene_context_evidence' in assignment:
        parent_input['gene_context_evidence'] = assignment['gene_context_evidence']
    return parent_input
