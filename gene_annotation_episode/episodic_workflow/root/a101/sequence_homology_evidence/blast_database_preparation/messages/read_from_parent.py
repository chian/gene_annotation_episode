"""What the parent gives: the commission of one preparation, controlled values and record references only. This is
the only place the assignment is read. The commission fields are checked with the library's own validator
(``validate_commission``): a wrong commission raises its error and the run fails, nothing repairs it. The kind
and the molecule are choices of a fixed vocabulary. ``windowmasker`` is not offered: the owner has not ruled on it.

``input_refs``: exactly one record, the FASTA sequence set (an artifact record), passed in custody.
``prepared_refs``: prepared-data records the parent already holds (passed in custody); a usable record of the same
key built here is a repeat and earns nothing. ``prepared_unit``: the credit a newly established usable record
earns."""
import math

from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_preparation_job import (
    KINDS, MASKING_OUTPUTS, MASKING_PROGRAMS, MOLECULES, validate_commission)

ASSIGNMENT_FORM = RecordForm({
    'kind': ChoiceField('text', 'What is prepared: a BLAST database build or a masking run', KINDS),
    'molecule': ChoiceField('text', 'The molecule of the sequence set', MOLECULES),
    'input_refs': Field('record_refs', 'The sequence set: exactly one FASTA record, passed in custody'),
    'prepared_refs': Field('record_refs', 'Prepared-data records the parent already holds, passed in custody',
                           required=False),
    'parse_seqids': Field('boolean', 'A build: whether sequence identifiers are parsed', required=False),
    'hash_index': Field('boolean', 'A build: whether a hash index is made', required=False),
    'db_version': Field('integer', 'A build: the BLAST database version (4 or 5)', required=False),
    'program': ChoiceField('text', 'Masking: the masking program', MASKING_PROGRAMS, required=False),
    'output_format': ChoiceField('text', 'Masking: the output format', MASKING_OUTPUTS, required=False),
    'window': Field('integer', 'Masking: the window parameter of the program', required=False),
    'level': Field('integer', 'Masking (dustmasker): the level parameter', required=False),
    'linker': Field('integer', 'Masking (dustmasker): the linker parameter', required=False),
    'locut': Field('number', 'Masking (segmasker): the low cut parameter', required=False),
    'hicut': Field('number', 'Masking (segmasker): the high cut parameter', required=False),
    'prepared_unit': Field('number', 'The credit a newly established usable prepared-data record earns (positive)'),
})
OPTIONAL = ('parse_seqids', 'hash_index', 'db_version', 'program', 'output_format', 'window', 'level', 'linker',
            'locut', 'hicut')


def read_from_parent(assignment, message):
    (input_ref,) = assignment['input_refs']
    unit = assignment['prepared_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('blast_preparation_prepared_unit_must_be_positive')
    fields = {'kind': assignment['kind'], 'molecule': assignment['molecule'], 'input_ref': input_ref,
              **{name: assignment[name] for name in OPTIONAL if name in assignment}}
    return {'fields': validate_commission(fields), 'prepared_unit': unit,
            'prior_prepared_refs': list(assignment.get('prepared_refs', []))}
