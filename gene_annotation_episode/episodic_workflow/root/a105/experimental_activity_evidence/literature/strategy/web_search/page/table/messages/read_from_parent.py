"""What the commissioner gives: the source, the representation, the byte window (offset, limit) that holds the table, the
kind of experiment to extract (a value of the library's ``FORMS``) and the proposed annotation the extraction is for. The
table's text is not passed: it is read from the artifact of the commissioned representation, which is passed in custody.
This is the only place the assignment is read."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    ARTIFACT_FIELD, FORMS)

REPRESENTATIONS = tuple(ARTIFACT_FIELD)
EXPERIMENT_TYPES = tuple(FORMS)
ASSIGNMENT_FORM = RecordForm({
    'source_ref': Field('text', 'The source the table is taken from'),
    'passed_refs': Field('record_refs', 'The source and the artifact of its text, passed in custody'),
    'representation': ChoiceField('text', 'The representation of the source the window is taken from, the one the page '
                                  'commissioned: its artifact is the one read', REPRESENTATIONS),
    'offset': Field('integer', 'The byte offset of the window that holds the table (0 or more)'),
    'limit': Field('integer', 'The length of the window in bytes (1 or more)'),
    'experiment_type': ChoiceField('text', 'The kind of experiment whose grader inputs are extracted', EXPERIMENT_TYPES),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the extraction is for'),
})


def read_from_parent(assignment, message):
    return {'source_ref': assignment['source_ref'], 'representation': assignment['representation'],
            'offset': assignment['offset'], 'limit': assignment['limit'],
            'experiment_type': assignment['experiment_type'],
            'proposed_annotation_ref': assignment['proposed_annotation_ref']}
