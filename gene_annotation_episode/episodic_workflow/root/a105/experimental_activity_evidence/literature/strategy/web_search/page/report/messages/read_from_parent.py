"""What the commissioner gives: the source, the representation, the windows to read in document order (``windows``: the
byte intervals ``[start, end]`` the page made of its remaining prose chunks, ``literature_page_content.report_windows``),
the sheet class of the claim (not an experiment type: the page has not read the source, and the leaf names the method each
window reports) and the proposed annotation the extraction is for. The source's text is not passed: it is read from the
artifact of the commissioned representation, which is passed in custody. This is the only place the assignment is read; a
window that is not an increasing interval after the one before it is a wrong commission and fails here."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    ARTIFACT_FIELD, SHEET_CLASSES)

REPRESENTATIONS = tuple(ARTIFACT_FIELD)
ASSIGNMENT_FORM = RecordForm({
    'source_ref': Field('text', 'The source read in document order'),
    'passed_refs': Field('record_refs', 'The source and the artifact of its text, passed in custody'),
    'representation': ChoiceField('text', 'The representation of the source the windows are taken from, the one the page '
                                  'commissioned: its artifact is the one read', REPRESENTATIONS),
    'windows': Field('list', 'The byte windows [start, end] to read, in document order, each once (1 or more)'),
    'sheet_class': ChoiceField('text', 'The sheet class of the claim: the class whose experiment types a window may report',
                               SHEET_CLASSES),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the extraction is for'),
})


def read_from_parent(assignment, message):
    windows = [[int(start), int(end)] for start, end in assignment['windows']]
    if not windows or any(start >= end for start, end in windows) or any(
            later[0] < earlier[1] for earlier, later in zip(windows, windows[1:])):
        raise ValueError('literature_reading_windows_invalid')
    return {'source_ref': assignment['source_ref'], 'representation': assignment['representation'],
            'windows': windows, 'sheet_class': assignment['sheet_class'],
            'proposed_annotation_ref': assignment['proposed_annotation_ref']}
