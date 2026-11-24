"""The parts-discovery tool ``describe_piece``: the composition and signature of the bare DNA of the piece, as facts. It proposes
nothing and earns no credit. The first unit of the head's first pass (owed, no choice).

THE REQUEST: ``piece_ref`` (the one input record of the scope). ``check_describe_piece_request`` is the one check: it refuses a
piece that is not the scope's piece and a piece already described. THE UNIT: read the sequence through custody, grade
(``description_sheet``), keep the grading with a source record (provider ``piece_description``, native artifact the piece's own
sequence artifact, operand the piece) and label it a ``tool_grading_sheet`` product. Writes only through ``ctx.store``."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery import description_sheet as sheets
from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery.held_sheets import piece_sequence
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)

PROVIDER = sheets.PROVIDER
TOOL_NAME = 'describe_piece'


def check_describe_piece_request(request, *, piece_ref, described):
    """The things to fix in a ``describe_piece`` request, before anything runs; an empty list means it can run. ``piece_ref`` is
    the scope's piece, ``described`` the pieces already described."""
    if request['piece_ref'] != piece_ref:
        return [{'code': 'piece_is_not_the_scope_piece', 'field': 'piece_ref', 'choose_from': [piece_ref]}]
    if request['piece_ref'] in described:
        return [{'code': 'piece_already_described', 'field': 'piece_ref', 'choose_from': []}]
    return []


def describe_piece(ctx, *, piece_ref):
    """Describe the held piece ``piece_ref`` and keep the sheet through custody (see the module). ``ctx`` is the tool's
    ``UnitContext``."""
    store = ctx.store
    sequence_ref = store.get(piece_ref)['sequence_ref']
    sheet = sheets.grade_piece_description(piece_sequence(store, piece_ref), piece_ref=piece_ref)
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


__all__ = ['PROVIDER', 'TOOL_NAME', 'check_describe_piece_request', 'describe_piece']
