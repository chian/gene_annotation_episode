"""Keeping the claims of one graded BLAST search: the step that follows the grading of a search in the same unit.

``keep_blast_claims`` reads the graded sheet of the search through custody, turns its hits into claims
(``blast_claims.blast_claim_sheet``), and keeps through custody: one ``feature`` record for each claim (the sequence the
claim is about, its type, its positions and its strand), the claim sheet with the reference of each claim's feature
record as a retained grading, and a source record of the provider ``feature_calling.blast_claims`` whose operand is the
sequence the claims are about. The sheet of feature calls reads that source (``feature_candidates.feature_tests``).

The sequence the claims are about is the searched sequence itself, or, when the searched sequence is a product derived
from another (a translation, an extracted stretch: its record has a ``mapping``), the sequence its mapping leads back to.
Nothing is decided and nothing is checked here: whether and what to search is the caller's. Writes only through
``ctx.store``."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.blast_claims import (
    GRADED_SHEET, blast_claim_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    retain_tool_grading, source_tool_grading_entries)

PROVIDER = 'feature_calling.blast_claims'


def keep_blast_claims(ctx, *, search_source_ref, searched_ref):
    """Turn the graded sheet of the search whose source is ``search_source_ref`` into claims about the sequence
    ``searched_ref`` was searched for, and keep them (see the module). Returns ``{'claim_count', 'refs'}``: the number of
    claims and the references kept (the claims' source, the retained claim sheet and the feature records)."""
    store = ctx.store
    (grading,) = [entry['grading'] for entry in source_tool_grading_entries(store, search_source_ref)
                  if entry['grading']['sheet']['schema'] == GRADED_SHEET]
    mapping = store.get(searched_ref).get('mapping')
    subject_ref = searched_ref if mapping is None else mapping['path'][0]['subject_ref']
    sheet = blast_claim_sheet(grading, mapping)
    report_ref = store.get(search_source_ref)['artifact_ref']
    with store.transaction():
        feature_refs = [store.put('feature', {'subject_ref': subject_ref, 'kind': claim['kind'],
                                              'segments': claim['segments'], 'strand': claim['strand'],
                                              'context_refs': []}, origin='tool')['id']
                        for claim in sheet['claims']]
        kept = {**sheet, 'subject_ref': subject_ref,
                'claims': [{**claim, 'feature_ref': ref} for claim, ref in zip(sheet['claims'], feature_refs)]}
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=report_ref,
                                          grading={'sheet': kept})
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': report_ref, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref],
            'operand_refs': [subject_ref]}, origin='tool')
    return {'claim_count': len(feature_refs), 'refs': [source['id'], grading_ref, *dict.fromkeys(feature_refs)]}





def hits_by_bit_score(report, grading, length):
    """The hits of a graded search as ``[(accession, bit score)]``, the highest bit score first, ties by accession: the
    order in which a search's hits are named when the search is read for the features of the searched sequence
    (``bvbrc_blast_search.fetch_and_grade_search``, ``order``). It reads the grader's own facts of each hit, whatever the
    program of the search; ``report`` and ``length`` are not needed for it."""
    sheet = grading['sheet']
    accession = {hit['hit_index']: hit['descriptions'][0]['accession'] for hit in sheet['normalized_result']['hits']}
    return sorted(((accession[hit['hit_index']], hit['measurements']['maximum_bit_score']) for hit in sheet['hits']),
                  key=lambda pair: (-pair[1], pair[0]))


__all__ = ['PROVIDER', 'hits_by_bit_score', 'keep_blast_claims']
