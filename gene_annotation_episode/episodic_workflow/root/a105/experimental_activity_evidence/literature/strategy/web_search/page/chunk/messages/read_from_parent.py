"""What the commissioner gives: the chunk (the source, the byte offset and the length of the window of its text),
the sheet class of the claim, and the proposed annotation the extraction is for. The page has not read the text, so it
names no experiment type: the leaf names the method the chunk reports, from the types of the sheet class. The chunk's text
is not passed: it is read from the artifact of the source's representation the page commissioned (``representation``), which
is passed in custody. This is the only place the assignment is read."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    SHEET_CLASSES)

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')   # the page's own vocabulary (page/messages/read_from_parent.py)
ASSIGNMENT_FORM = RecordForm({
    'source_ref': Field('text', 'The source the chunk is taken from'),
    'passed_refs': Field('record_refs', 'The source and the artifact of its text, passed in custody'),
    'representation': ChoiceField('text', 'The representation of the source the window is taken from, the one the page '
                                  'commissioned: its artifact is the one read', REPRESENTATIONS),
    'offset': Field('integer', 'The byte offset of the chunk in that representation (0 or more)'),
    'limit': Field('integer', 'The length of the chunk in bytes (1 or more)'),
    'sheet_class': ChoiceField('text', 'The sheet class of the claim: the class whose experiment types the chunk may report',
                               SHEET_CLASSES),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the extraction is for'),
})


def read_from_parent(assignment, message):
    return {'source_ref': assignment['source_ref'], 'representation': assignment['representation'],
            'offset': assignment['offset'], 'limit': assignment['limit'],
            'sheet_class': assignment['sheet_class'],
            'proposed_annotation_ref': assignment['proposed_annotation_ref']}
