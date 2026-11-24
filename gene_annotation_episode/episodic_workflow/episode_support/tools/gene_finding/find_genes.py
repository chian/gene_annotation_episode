"""Finding the protein genes of a DNA sequence with the gene finder pyrodigal (a Python binding of Prodigal), in the mode and under
the genetic code it is given. This module decides nothing and checks nothing: which mode, which code and whether to run at all are
the caller's.

The two modes of the finder: ``self_trained`` (``GeneFinder().train(sequence, translation_table=code)`` then ``find_genes``), which
the finder itself refuses below ``SELF_TRAINED_MINIMUM`` nt, and ``pre_trained`` (``GeneFinder(meta=True)``), which ignores the code
(the sheet records ``code_applied`` false).

``find_genes`` reads the sequence through custody, runs the finder, grades (``gene_finding_sheet``: one reading), keeps the finder's
calls as a data product (``gene_calls``) and the grading with a source record (provider ``gene_finding``, native artifact the calls,
operand the sequence's record) labelled a ``tool_grading_sheet`` product. Writes only through ``ctx.store``."""
import json

import pyrodigal

from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_finding import gene_finding_sheet as sheets
from gene_annotation_episode.episodic_workflow.episode_support.grading.tool_grading.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import record_product
from gene_annotation_episode.episodic_workflow.episode_support.records.dna_sequence import record_sequence

PROVIDER = sheets.PROVIDER
PRODUCT_KIND = 'gene_calls'
FINDER = 'pyrodigal'
SELF_TRAINED_MINIMUM = 20000   # a fact of the finder: the least nt it accepts for training on the sequence itself
FINDERS = {'self_trained': lambda: pyrodigal.GeneFinder(), 'pre_trained': lambda: pyrodigal.GeneFinder(meta=True)}


def run_finder(sequence, mode, code):
    """The finder's genes on ``sequence`` (upper case) in ``mode`` under ``code``. The self-trained finder is trained on the
    sequence first; the pre-trained one is not and ignores the code."""
    data = sequence.encode('ascii')
    finder = FINDERS[mode]()
    if mode == 'self_trained':
        finder.train(data, translation_table=code)
    return finder.find_genes(data)


def gene_rows(genes):
    """The sheet's rows of the finder's genes, in the finder's order (see ``gene_finding_sheet``)."""
    return [{'begin': int(gene.begin), 'end': int(gene.end), 'strand': '+' if gene.strand == 1 else '-',
             'start_codon': gene.start_type, 'partial_begin': bool(gene.partial_begin), 'partial_end': bool(gene.partial_end),
             'rbs_motif': gene.rbs_motif, 'rbs_spacer': gene.rbs_spacer, 'score': float(gene.score),
             'confidence': float(gene.confidence()), 'translation': gene.translate()} for gene in genes]


def read_genes(sequence, *, piece_ref, mode, code):
    """The sheet of the reading of ``sequence`` in ``mode`` under ``code`` (the finder run, graded): no store involved."""
    return sheets.grade_gene_finding(gene_rows(run_finder(sequence, mode, code)), piece_ref=piece_ref, length=len(sequence),
                                     code=code, mode=mode)


def find_genes(ctx, *, piece_ref, mode, code):
    """Find the genes of the held sequence record ``piece_ref`` in ``mode`` under ``code`` and keep the calls and the sheet through
    custody (see the module). ``ctx`` is the tool's ``UnitContext``."""
    store = ctx.store
    sequence_ref = store.get(piece_ref)['sequence_ref']
    sheet = read_genes(record_sequence(store, piece_ref), piece_ref=piece_ref, mode=mode, code=code)
    grading = {'sheet': sheet}
    calls = {'finder': FINDER, 'finder_version': pyrodigal.__version__, 'mode': sheet['mode'], 'code': code,
             'code_applied': sheet['code_applied'],
             'genes': [{name: value for name, value in row.items() if name != 'translation'} for row in sheet['genes']]}
    product_settings = {'finder': FINDER, 'finder_version': pyrodigal.__version__, 'mode': sheet['mode'], 'code': code,
                        'code_applied': sheet['code_applied']}
    with store.transaction():
        calls_ref = store.artifact(json.dumps(calls, sort_keys=True, separators=(',', ':')).encode(), 'application/json')
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=calls_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': piece_ref, 'uri': None, 'artifact_ref': calls_ref, 'text_ref': None,
            'request_ref': None, 'version': pyrodigal.__version__, 'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref],
            'operand_refs': [piece_ref]}, origin='tool')
        product = record_product(store, artifact_ref=calls_ref, kind=PRODUCT_KIND, generated_by=source['id'], used=[sequence_ref],
                                 settings=product_settings)
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[calls_ref, sequence_ref],
                                                 derived_from=[product['id']])
    graded = [source['id'], grading_ref, product['id'], grading_product['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'graded_refs': graded, 'record_refs': graded,
            'source_ref': source['id'], 'mode': sheet['mode'], 'code': code, 'code_applied': sheet['code_applied'],
            'gene_count': sheet['gene_count'], 'coding_share': sheet['coding_share'], 'score_sum': sheet['score_sum'],
            **({} if sheet['median_gene_nt'] is None else {'median_gene_nt': sheet['median_gene_nt']})}


__all__ = ['FINDER', 'FINDERS', 'PRODUCT_KIND', 'PROVIDER', 'SELF_TRAINED_MINIMUM', 'find_genes', 'gene_rows', 'read_genes',
           'run_finder']
