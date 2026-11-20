"""What the head gives: the controlled commission of one preparation, as plain values and one record reference (the
sequence set in custody), the local resource to run it on, and the two credit units. This is the only place the
assignment is read. The commission is checked here with the library's own validator (``validate_commission``); a
wrong commission raises its stable ``blast_preparation_*`` error and nothing repairs it. No path, command or free
text can be given: a kind from a fixed vocabulary, a molecule, booleans, a value of a fixed set and numbers in their
native ranges."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.blast_preparation_job import (
    KINDS, MASKING_OUTPUTS, MASKING_PROGRAMS, MOLECULES, validate_commission)

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The version of this assignment form', 'blast_preparation_assignment_v1'),
    'kind': ChoiceField('text', 'What is prepared: a BLAST database build or a masking run', KINDS),
    'molecule': ChoiceField('text', 'The molecule of the sequence set', MOLECULES),
    'input_refs': Field('record_refs', 'The sequence set to prepare from: exactly one FASTA record, passed in custody'),
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
    'resource_id': Field('text', 'The local resource to run the preparation on'),
    'handoff_unit': Field('number', 'The credit one established handoff earns (positive)'),
    'prepared_unit': Field('number', 'The credit one usable prepared-data record earns (positive)'),
})
OPTIONAL = ('parse_seqids', 'hash_index', 'db_version', 'program', 'output_format', 'window', 'level', 'linker',
            'locut', 'hicut')


def read_from_parent(assignment, message):
    if len(assignment['input_refs']) != 1:
        raise ValueError('blast_preparation_exactly_one_input_record_required')
    (input_ref,) = assignment['input_refs']
    for name in ('handoff_unit', 'prepared_unit'):
        if not math.isfinite(assignment[name]) or assignment[name] <= 0:
            raise ValueError('blast_preparation_' + name + '_must_be_positive')
    fields = {'kind': assignment['kind'], 'molecule': assignment['molecule'], 'input_ref': input_ref,
              **{name: assignment[name] for name in OPTIONAL if name in assignment}}
    return {'fields': validate_commission(fields), 'resource_id': assignment['resource_id'],
            'handoff_unit': assignment['handoff_unit'], 'prepared_unit': assignment['prepared_unit']}
