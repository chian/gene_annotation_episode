"""What the parent gives: the search to submit, as controlled values and record references only.

``query_subject_refs`` names exactly one subject record in custody, the query; ``record_refs`` holds every record the
code reads, passed in custody: that record and the sequence artifact it names. The program is one of the five BLAST
programs, the hosted database one of this episode's vocabulary, the hit-list size a positive integer; none of them is
text the parent or a model writes. This is the only place the assignment is read. A record the parent does not hold, or
a program that does not take the query's molecule, fails the run where the code first reads them, with its error."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

VERSION = 'database_blast_launch_api_assignment_v1'
PROGRAMS = ('blastn', 'blastp', 'blastx', 'tblastn', 'tblastx')
HOSTED_DATABASES = ('swissprot', 'nr', 'refseq_protein', 'pdbaa', 'nt')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', VERSION),
    'resource_id': Field('text', 'The resource of the job service the job is submitted on: a bound API route'),
    'service': ChoiceField('text', 'The public web service of that resource', ('ncbi_blast',)),
    'query_subject_refs': Field('record_refs', 'The one subject record that is the query of the search'),
    'program': ChoiceField('text', 'The BLAST program; it must take a query of the assigned molecule', PROGRAMS),
    'database': ChoiceField('text', 'The hosted database to search', HOSTED_DATABASES),
    'hitlist_size': Field('integer', 'The largest number of database sequences to report (positive)'),
    'completion_target': Field('number', 'The credit the established handoff earns (positive)'),
    'record_refs': Field('record_refs', 'Every record the code reads, passed in custody: the query record and the '
                                        'sequence artifact it names'),
})


def read_from_parent(assignment, message):
    if len(assignment['query_subject_refs']) != 1:
        raise ValueError('database_blast_launch_exactly_one_query_record_required')
    if assignment['hitlist_size'] < 1:
        raise ValueError('database_blast_launch_hitlist_size_must_be_positive')
    target = assignment['completion_target']
    if not math.isfinite(target) or target <= 0:
        raise ValueError('explicit_positive_completion_target_required')
    return {'resource_id': assignment['resource_id'], 'service': assignment['service'],
            'query_subject_ref': assignment['query_subject_refs'][0], 'program': assignment['program'],
            'database': assignment['database'], 'hitlist_size': assignment['hitlist_size'],
            'completion_target': target}
