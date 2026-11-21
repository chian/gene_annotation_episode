"""What the commissioner gives: the chunk (the source, the byte offset and the length of the window of its text),
the kind of experiment to extract, and the proposed annotation the extraction is for. The chunk's text is not
passed: it is read from the artifact of the source's representation the page commissioned (``representation``), which is
passed in custody. This is the only place the assignment is
read."""
from method_loop import ChoiceField, Field, RecordForm

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')   # the page's own vocabulary (page/messages/read_from_parent.py)
EXPERIMENT_TYPES = ('spr', 'itc', 'bli', 'gci', 'fp', 'fret', 'mst', 'trp_quenching', 'fcs', 'elisa', 'alphascreen', 'radioligand', 'spa', 'pulldown', 'emsa', 'sec', 'dialysis', 'auc', 'cetsa', 'split_reporter', 'dsf', 'y2h', 'pla', 'proximity', 'bret')
ASSIGNMENT_FORM = RecordForm({
    'source_ref': Field('text', 'The source the chunk is taken from'),
    'passed_refs': Field('record_refs', 'The source and the artifact of its text, passed in custody'),
    'representation': ChoiceField('text', 'The representation of the source the window is taken from, the one the page '
                                  'commissioned: its artifact is the one read', REPRESENTATIONS),
    'offset': Field('integer', 'The byte offset of the chunk in that representation (0 or more)'),
    'limit': Field('integer', 'The length of the chunk in bytes (1 or more)'),
    'experiment_type': ChoiceField('text', 'The kind of experiment whose grader inputs are extracted',
                                   EXPERIMENT_TYPES),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the extraction is for'),
})


def read_from_parent(assignment, message):
    return {'source_ref': assignment['source_ref'], 'representation': assignment['representation'],
            'offset': assignment['offset'], 'limit': assignment['limit'],
            'experiment_type': assignment['experiment_type'],
            'proposed_annotation_ref': assignment['proposed_annotation_ref']}
