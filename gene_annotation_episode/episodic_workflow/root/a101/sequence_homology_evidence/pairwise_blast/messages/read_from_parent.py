"""What the parent gives: the comparison to make, as controlled values and record references, and nothing else.

``query_refs`` and ``subject_refs`` each name exactly one subject record in custody; ``record_refs`` holds every
record the code reads, passed in custody: those two records and the sequence artifacts they name. ``analysis_kind`` is
the declared kind of the analysis; this episode only performs ``pairwise``, so the form admits nothing else, and the
job the episode builds is derived to the same kind before it launches. This is the only place the assignment is read.
A record the parent does not hold, or two molecules the program cannot compare, fails the run where the code first
reads them, with its error."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_contracts import (
    PROGRAMS)

VERSION = 'pairwise_blast_assignment_v1'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', VERSION),
    'analysis_kind': DeclaredField('text', 'The declared analysis kind: pairwise, one query sequence against one '
                                           'subject sequence. The job built is checked against it', 'pairwise'),
    'program': ChoiceField('text', 'The BLAST program that compares the two sequences', PROGRAMS),
    'query_refs': Field('record_refs', 'The one query subject record, in custody'),
    'subject_refs': Field('record_refs', 'The one subject record the query is searched against, in custody'),
    'resource_id': Field('text', 'The one local resource the job runs on'),
    'information_unit': Field('number', 'The credit of establishing the correspondence of the two sequences '
                                        '(positive)'),
    'record_refs': Field('record_refs', 'Every record the code reads, passed in custody: the two subject records and '
                                        'the sequence artifacts they name'),
})


def read_from_parent(assignment, message):
    if len(assignment['query_refs']) != 1:
        raise ValueError('pairwise_blast_exactly_one_query_record_required')
    if len(assignment['subject_refs']) != 1:
        raise ValueError('pairwise_blast_exactly_one_subject_record_required')
    unit = assignment['information_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('explicit_positive_information_unit_required')
    return {'analysis_kind': assignment['analysis_kind'], 'program': assignment['program'],
            'query_ref': assignment['query_refs'][0], 'subject_ref': assignment['subject_refs'][0],
            'resource_id': assignment['resource_id'], 'information_unit': unit}
