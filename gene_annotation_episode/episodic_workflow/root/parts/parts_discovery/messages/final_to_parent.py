"""The return. Always returned: ``credit`` (``completion['credit']``: the progress signal, which no field restates) and ``finding``:
the piece (its record reference, length, GC fraction and GC skew), the READING REPORTED (the held gene-finding sheet of the highest
score: its mode, genetic code, whether the code was applied, gene count, median gene length, coding share and score, the sum of the
finder's scores of its genes), the number of readings held, the number of RNA genes, and the leading parts (at most ``LEADING_PER_KIND``
of each kind, the highest score first within each kind: kind, begin, end, strand, whether each end is cut off by the end of the
piece, the score, and for an RNA gene its Rfam family accession). All of it numbers, booleans, values of a fixed vocabulary,
looked-up identifiers and record references: no paragraph. The gene rows, translations and composition tables stay in the sheets,
which the episode keeps; the parts are rows of the sheets, one record per part is not made.

Selectable: ``committed_record_refs`` (the graded records this episode holds: the records its credit reads, which a parent passes back
on a later visit) and ``data_product_refs`` (the held data-product rows). EVERY RETURNED RECORD LIST IS CLOSED UNDER NAMING: each is
``internal_summary``'s ``returned_refs`` entry, built with ``job_records.returned_with_names``."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery.gene_finding_sheet import (
    CODES, MODES, STRANDS)
from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery.held_sheets import PART_KINDS

PIECE_FORM = RecordForm({
    'ref': Field('text', 'The piece of DNA: an input record of the scope (a record reference)'),
    'length': Field('integer', 'The length of the piece in nt'),
    'gc_fraction': Field('number', 'The fraction of G and C among the unambiguous bases of the piece, 0 to 1'),
    'gc_skew': Field('number', '(G - C) / (G + C) over the piece, -1 to 1'),
})
READING_FORM = RecordForm({
    'mode': ChoiceField('text', 'The gene finder\'s mode, fixed by the length of the piece: self_trained (trained on the piece, '
                                'for a piece of at least 20000 nt) or pre_trained (for a shorter piece)', MODES),
    'code': ChoiceField('integer', 'The genetic code (translation table) asked: 11 the default, 4 or 25 the special codes', CODES),
    'code_applied': Field('boolean', 'Whether the code was applied: false for a pre_trained reading, which ignores the code'),
    'gene_count': Field('integer', 'The protein genes the reading calls'),
    'median_gene_nt': Field('number', 'The median length of the called genes in nt; absent when none is called', required=False),
    'coding_share': Field('number', 'The nucleotides in the called genes (each gene its own length) over the length of the piece'),
    'score_sum': Field('number', 'The reading\'s score: the sum of the gene finder\'s own scores of its genes'),
})
PART_FORM = RecordForm({
    'kind': ChoiceField('text', 'protein_gene (a gene the finder called) or rna_gene (a hit of an Rfam family not overlapped by a '
                                'better hit of its clan)', PART_KINDS),
    'begin': Field('integer', 'The first position on the piece, 1-based, inclusive'),
    'end': Field('integer', 'The last position on the piece, 1-based, inclusive'),
    'strand': ChoiceField('text', 'The strand the part reads on', STRANDS),
    'partial_begin': Field('boolean', 'Whether the part runs off the beginning of the piece'),
    'partial_end': Field('boolean', 'Whether the part runs off the end of the piece'),
    'score': Field('number', 'The part\'s score: the finder\'s own score of a protein gene, the bit score of an RNA gene'),
    'family_accession': Field('text', 'For an RNA gene: its Rfam family accession (the looked-up identifier of the family)',
                              required=False),
})
FINDING_FORM = RecordForm({
    'arm': ChoiceField('text', 'The arm', ('parts_discovery',)),
    'piece': Field('record', 'The piece of DNA and its composition', form=PIECE_FORM),
    'reading': Field('record', 'The reading of the protein genes reported: the held one of the highest score', form=READING_FORM),
    'readings_held': Field('integer', 'The readings of the protein genes held (one per genetic code read)'),
    'rna_gene_count': Field('integer', 'The RNA genes found: hits not overlapped by a better hit of their clan'),
    'leading_parts': Field('list', 'The leading parts: of each kind at most 10, the highest score first within each kind',
                           items=PART_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The piece, the reading reported and the leading parts with their scores', form=FINDING_FORM),
    'committed_record_refs': Field('record_refs', 'The graded records this episode holds: what its credit reads', required=False),
    'data_product_refs': Field('record_refs', 'The data-product rows it holds (labelled files: EDAM type and format, what made them, '
                                              'where else they lie)', required=False),
})


def final_to_parent(summary, completion, selection):
    reported, description = summary['reported'], summary['description']
    reading = {name: reported[name] for name in READING_FORM.fields if name in reported and reported[name] is not None}
    result = {'credit': completion['credit'],
              'finding': {'arm': 'parts_discovery',
                          'piece': {'ref': summary['piece']['ref'], 'length': summary['piece']['length'],
                                    'gc_fraction': description['gc_fraction'], 'gc_skew': description['gc_skew']},
                          'reading': reading, 'readings_held': len(summary['readings']),
                          'rna_gene_count': sum(row['part_count'] for row in summary['rna_scans']),
                          'leading_parts': summary['leading_parts']}}
    result.update({name: refs for name, refs in summary['returned_refs'].items() if name in selection})
    return result
