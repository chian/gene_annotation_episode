"""The parts-discovery tool ``find_genes``: the protein genes of the piece, by the gene finder pyrodigal (a Python binding of
Prodigal), read under one genetic code. One fixed workflow, called the same way for any piece.

THE REQUEST (one controlled field besides the piece): ``code`` (an integer of ``gene_finding_sheet.CODES``: the default 11, or a
special code 4 or 25). THE MODE is a fixed rule of the piece's length, not a choice (``gene_finding_sheet.mode_of``): self-trained
on the piece (``GeneFinder().train(piece, translation_table=code)`` then ``find_genes``) at ``SELF_TRAINED_MINIMUM`` nt or more;
else the pre-trained mode (``GeneFinder(meta=True)``), which ignores the code (the sheet records ``code_applied`` false).

``check_find_genes_request`` is the one check. It refuses: a piece that is not the scope's piece; a code outside ``CODES``; a
reading under that code already held (a repeat earns nothing); a special code for a piece below ``SELF_TRAINED_MINIMUM`` nt (its
code would not be applied, the reading would be the default's again). A request that passes simply works.

THE UNIT: read the sequence through custody, run the finder, grade (``gene_finding_sheet``: one reading), keep the finder's calls
as a data product (``gene_calls``) and the grading with a source record (provider ``gene_finding``, native artifact the calls,
operand the piece) labelled a ``tool_grading_sheet`` product. Writes only through ``ctx.store``."""
import json

import pyrodigal

from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery import gene_finding_sheet as sheets
from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery.held_sheets import piece_sequence
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import record_product

PROVIDER = sheets.PROVIDER
TOOL_NAME = 'find_genes'
PRODUCT_KIND = 'gene_calls'
FINDER = 'pyrodigal'


def offered_codes(length, held_codes):
    """The codes a request may name now: the codes of ``CODES`` with no reading held, the special ones only for a piece of
    ``SELF_TRAINED_MINIMUM`` nt or more."""
    return [code for code in sheets.CODES if code not in held_codes
            and (code == sheets.DEFAULT_CODE or length >= sheets.SELF_TRAINED_MINIMUM)]


def check_find_genes_request(request, *, piece_ref, length, held_codes):
    """The things to fix in a ``find_genes`` request, before anything runs; an empty list means it can run. ``length`` is the piece's
    nt, ``held_codes`` the codes of the readings held."""
    offered = offered_codes(length, held_codes)
    if request['piece_ref'] != piece_ref:
        return [{'code': 'piece_is_not_the_scope_piece', 'field': 'piece_ref', 'choose_from': [piece_ref]}]
    code = request['code']
    if code not in sheets.CODES:
        return [{'code': 'code_is_not_offered', 'field': 'code', 'choose_from': offered}]
    if code in held_codes:
        return [{'code': 'reading_under_the_code_already_held', 'field': 'code', 'choose_from': offered}]
    if code != sheets.DEFAULT_CODE and length < sheets.SELF_TRAINED_MINIMUM:
        return [{'code': 'code_is_not_applied_below_the_self_trained_minimum', 'field': 'code', 'choose_from': offered}]
    return []


def run_finder(sequence, code):
    """The finder's genes on ``sequence`` (upper case) under ``code``, in the mode of the sequence's length."""
    data = sequence.encode('ascii')
    if sheets.mode_of(len(sequence)) == 'self_trained':
        finder = pyrodigal.GeneFinder()
        finder.train(data, translation_table=code)
    else:
        finder = pyrodigal.GeneFinder(meta=True)
    return finder.find_genes(data)


def gene_rows(genes):
    """The sheet's rows of the finder's genes, in the finder's order (see ``gene_finding_sheet``)."""
    return [{'begin': int(gene.begin), 'end': int(gene.end), 'strand': '+' if gene.strand == 1 else '-',
             'start_codon': gene.start_type, 'partial_begin': bool(gene.partial_begin), 'partial_end': bool(gene.partial_end),
             'rbs_motif': gene.rbs_motif, 'rbs_spacer': gene.rbs_spacer, 'score': float(gene.score),
             'confidence': float(gene.confidence()), 'translation': gene.translate()} for gene in genes]


def read_genes(sequence, *, piece_ref, code):
    """The sheet of the reading of ``sequence`` under ``code`` (the finder run, graded): no store involved."""
    return sheets.grade_gene_finding(gene_rows(run_finder(sequence, code)), piece_ref=piece_ref, length=len(sequence), code=code)


def find_genes(ctx, *, piece_ref, code):
    """Find the genes of the held piece ``piece_ref`` under ``code`` and keep the calls and the sheet through custody (see the
    module). ``ctx`` is the tool's ``UnitContext``."""
    store = ctx.store
    sequence_ref = store.get(piece_ref)['sequence_ref']
    sheet = read_genes(piece_sequence(store, piece_ref), piece_ref=piece_ref, code=code)
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


__all__ = ['FINDER', 'PRODUCT_KIND', 'PROVIDER', 'TOOL_NAME', 'check_find_genes_request', 'find_genes', 'gene_rows',
           'offered_codes', 'read_genes', 'run_finder']
