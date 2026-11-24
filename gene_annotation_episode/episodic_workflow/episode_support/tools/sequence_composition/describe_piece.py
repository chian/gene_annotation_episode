"""The composition and signature of a DNA sequence, as facts. This module decides nothing and checks nothing: whether and when
it runs is the caller's.

``describe_piece`` reads the sequence through custody, grades (``description_sheet``), keeps the grading with a source record
(provider ``sequence_composition``, native artifact the sequence's own artifact, operand the sequence's record) and labels it a
``tool_grading_sheet`` product. Writes only through ``ctx.store``."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_composition import description_sheet as sheets
from gene_annotation_episode.episodic_workflow.episode_support.grading.tool_grading.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.records.dna_sequence import record_sequence

PROVIDER = sheets.PROVIDER


def describe_piece(ctx, *, piece_ref):
    """Describe the held sequence record ``piece_ref`` and keep the sheet through custody (see the module). ``ctx`` is the tool's
    ``UnitContext``."""
    store = ctx.store
    sequence_ref = store.get(piece_ref)['sequence_ref']
    sheet = sheets.grade_piece_description(record_sequence(store, piece_ref), piece_ref=piece_ref)
    grading = {'sheet': sheet}
    with store.transaction():
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=sequence_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': piece_ref, 'uri': None, 'artifact_ref': sequence_ref, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref],
            'operand_refs': [piece_ref]}, origin='tool')
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[sequence_ref])
    refs = [source['id'], grading_ref, grading_product['id']]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'graded_refs': [], 'record_refs': refs,
            'source_ref': source['id'], 'length': sheet['length'], 'gc_fraction': sheet['gc_fraction'],
            'gc_skew': sheet['gc_skew'], 'window_count': sheet['window_count']}


__all__ = ['PROVIDER', 'describe_piece']
