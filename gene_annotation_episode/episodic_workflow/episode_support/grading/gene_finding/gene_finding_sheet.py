"""The sheet of one gene finding: the protein genes a gene finder called on a DNA sequence, in one mode under one genetic code.
This module states facts only; it holds no threshold and decides nothing.

The finder (pyrodigal, the Prodigal gene finder) ran in the mode it was given: ``self_trained`` on the sequence under the
translation table ``code``, or ``pre_trained``, which ignores the table (``code_applied`` false).

THE SHEET: ``mode``, ``code``, ``code_applied``, ``gene_count``, ``median_gene_nt``, ``coding_share`` (the nt in the genes, each
gene its own length, over the length of the piece), ``score_sum`` (the sum of the finder's own score of each gene: its native
statistic) and one row per gene (``genes``): ``begin`` and ``end`` (1-based, inclusive, begin below end), ``strand``,
``start_codon``, ``partial_begin`` and ``partial_end`` (the call runs off that end of the piece), ``rbs_motif``, ``rbs_spacer``,
``score``, ``confidence`` and the ``translation``.

The sheet is controlled data: numbers, booleans, the finder's own marks and the translated residues."""
from statistics import median

SCHEMA = 'gene_finding_sheet'
PROVIDER = 'gene_finding'
MODES = ('self_trained', 'pre_trained')
STRANDS = ('+', '-')


def grade_gene_finding(genes, *, piece_ref, length, code, mode):
    """The sheet of one gene finding: ``genes`` are the finder's rows (``find_genes.gene_rows``), ``length`` the sequence's nt,
    ``code`` the code asked, ``mode`` the mode the finder ran in."""
    lengths = [row['end'] - row['begin'] + 1 for row in genes]
    return {'schema': SCHEMA, 'provider': PROVIDER, 'piece_ref': piece_ref, 'piece_length': length, 'mode': mode, 'code': code,
            'code_applied': mode == 'self_trained', 'gene_count': len(genes),
            'median_gene_nt': float(median(lengths)) if lengths else None, 'coding_share': sum(lengths) / length,
            'score_sum': sum((row['score'] for row in genes), 0.0), 'genes': genes}


__all__ = ['MODES', 'PROVIDER', 'SCHEMA', 'STRANDS',
           'grade_gene_finding']
