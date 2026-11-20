"""What the parent gives: the chunk to launch, as controlled values and record references, and nothing else.

``set_refs`` names exactly one record in custody: the set, a FASTA artifact. ``chunk_index`` and ``chunk_count`` say
which contiguous slice of it is this launch's query (one chunk is the whole set); the program, the E-value, the target
and HSP limits are the search's controlled parameters, in the ranges the contract validates. ``analysis_kind`` is the
declared kind, and the job the episode builds is derived to the same kind before it launches. ``handoff_unit`` is the
credit of the handoff. This is the only place the assignment is read. A record the parent does not hold, or a value
the contract refuses, fails the run where the code first reads it, with its error."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_all_vs_all_job import (
    PROGRAMS)

VERSION = 'all_vs_all_launch_assignment_v1'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', VERSION),
    'analysis_kind': DeclaredField('text', 'The declared analysis kind: a set of sequences searched against itself. '
                                           'The job built is checked against it', 'all_vs_all'),
    'set_refs': Field('record_refs', 'The one sequence set, a FASTA artifact in custody'),
    'program': ChoiceField('text', 'The BLAST program', PROGRAMS),
    'evalue': Field('number', 'The E-value threshold of the search (above 0, at most 1000)'),
    'max_target_seqs': Field('integer', 'The most subject sequences kept per query (1 to 100000)'),
    'max_hsps': Field('integer', 'The most local alignments kept per pair (1 to 10); omitted for the default of the '
                                 'program', required=False),
    'chunk_index': Field('integer', 'The position of this chunk among the chunks of the set (from 0)'),
    'chunk_count': Field('integer', 'The number of chunks the set is split into (1 for the whole set)'),
    'resource_id': Field('text', 'The one local resource the job runs on'),
    'handoff_unit': Field('number', 'The credit of the handoff (positive)'),
})


def read_from_parent(assignment, message):
    if len(assignment['set_refs']) != 1:
        raise ValueError('all_vs_all_launch_exactly_one_set_record_required')
    unit = assignment['handoff_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('explicit_positive_handoff_unit_required')
    parent = {name: assignment[name] for name in ('analysis_kind', 'program', 'evalue', 'max_target_seqs',
                                                  'chunk_index', 'chunk_count', 'resource_id')}
    parent.update(set_ref=assignment['set_refs'][0], handoff_unit=unit)
    if 'max_hsps' in assignment:
        parent['max_hsps'] = assignment['max_hsps']
    return parent
