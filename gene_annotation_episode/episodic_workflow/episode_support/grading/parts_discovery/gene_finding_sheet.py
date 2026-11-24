"""The grader and the sheet of the parts-discovery tool ``find_genes``: the protein genes a gene finder calls on the piece under one
genetic code. One sheet is one READING of the piece's protein genes; its score is its ``score_sum``.

THE FINDER (pyrodigal, the Prodigal gene finder) runs in a mode fixed by the length of the piece, not chosen: self-trained on the
piece when the piece has at least ``SELF_TRAINED_MINIMUM`` nt (the finder cannot train on less), under the translation table
``code``; else its pre-trained (metagenomic) mode, which ignores the table (``code_applied`` false). The codes: the default
``DEFAULT_CODE`` (11) and the special codes ``SPECIAL_CODES`` (4 and 25 give the same calls).

THE SHEET: ``mode``, ``code``, ``code_applied``, ``gene_count``, ``median_gene_nt``, ``coding_share`` (the nt in the genes, each
gene its own length, over the length of the piece), ``score_sum`` (the sum of the finder's own score of each gene: its native
statistic) and one row per gene (``genes``): ``begin`` and ``end`` (1-based, inclusive, begin below end), ``strand``,
``start_codon``, ``partial_begin`` and ``partial_end`` (the call runs off that end of the piece), ``rbs_motif``, ``rbs_spacer``,
``score``, ``confidence`` and the ``translation``. A PART is ``protein_gene`` at (strand, begin, end) read under that code. A wrong
code shows as a lower ``score_sum`` (and, by the survey of 2026-11-23, more and shorter genes and a lower coding share); no
threshold is held here: the sheet states, the credit compares.

The sheet is controlled data: numbers, booleans, the finder's own marks and the translated residues."""
from statistics import median

SCHEMA = 'parts_gene_finding_sheet'
PROVIDER = 'gene_finding'
MODES = ('self_trained', 'pre_trained')
DEFAULT_CODE = 11
SPECIAL_CODES = (4, 25)
CODES = (DEFAULT_CODE, *SPECIAL_CODES)
STRANDS = ('+', '-')


def grade_gene_finding(genes, *, piece_ref, length, code, mode):
    """The sheet of one reading: ``genes`` are the finder's rows (``find_genes.gene_rows``), ``length`` the piece's nt, ``code`` the
    code asked, ``mode`` the finder's mode for the piece (``find_genes.mode_of``)."""
    lengths = [row['end'] - row['begin'] + 1 for row in genes]
    return {'schema': SCHEMA, 'provider': PROVIDER, 'piece_ref': piece_ref, 'piece_length': length, 'mode': mode, 'code': code,
            'code_applied': mode == 'self_trained', 'gene_count': len(genes),
            'median_gene_nt': float(median(lengths)) if lengths else None, 'coding_share': sum(lengths) / length,
            'score_sum': sum((row['score'] for row in genes), 0.0), 'genes': genes}


__all__ = ['CODES', 'DEFAULT_CODE', 'MODES', 'PROVIDER', 'SCHEMA', 'SPECIAL_CODES', 'STRANDS',
           'grade_gene_finding']
