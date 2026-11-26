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
    GRADED_SHEET, blast_claim_sheet, place_labels)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    retain_tool_grading, source_tool_grading_entries)

PROVIDER = 'feature_calling.blast_claims'
SAME_CALL_INSTRUCTIONS = (
    'You are shown what a sequence database says of the hits of one search, for one place on a sequence. Each item has a '
    'number (item) and the annotations the database gives the hits it stands for, as written. Sort the items by what '
    'they indicate, not by their wording.\n'
    '- Items that indicate the same thing get the same group number (1, 2, 3, ...). The same thing in other words, in an '
    'abbreviation, with "putative" or "probable" before it, or said more or less specifically without contradiction, is '
    'the same thing.\n'
    '- Items that indicate different things get different group numbers.\n'
    '- An item that states nothing of what the thing is (a bare position or serial name such as an open reading frame '
    'number, with no function or kind of product) gets group 0. "Conserved hypothetical protein" is not such an item: '
    'it gets a group of its own.\n'
    'Answer with one group number for every item, and nothing else.')
SAME_CALL_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['groups'],
    'properties': {'groups': {'type': 'array', 'items': {
        'type': 'object', 'additionalProperties': False, 'required': ['item', 'group'],
        'properties': {'item': {'type': 'integer', 'minimum': 1}, 'group': {'type': 'integer', 'minimum': 0}}}}}}


async def same_calls(model, labels):
    """Which labels of one place indicate the same thing: ``{label: group number}`` (0: states nothing of what the
    feature is). One label needs no judgement and is group 1. Several are sorted by one model call that is shown the
    annotations and answers with numbers only; an answer that does not give every item exactly one group raises."""
    if len(labels) <= 1:
        return {row['label']: 1 for row in labels}
    answer = await model.complete('REASONING', SAME_CALL_INSTRUCTIONS,
                                  {'items': [{'item': number, 'annotations': row['annotations']}
                                             for number, row in enumerate(labels, 1)]}, SAME_CALL_SCHEMA)
    given = {row['item']: row['group'] for row in answer['groups']}
    if len(given) != len(answer['groups']) or set(given) != set(range(1, len(labels) + 1)):
        raise ValueError('same_call_answer_does_not_give_every_item_one_group')
    return {row['label']: given[number] for number, row in enumerate(labels, 1)}


async def keep_blast_claims(ctx, *, search_source_ref, searched_ref):
    """Turn the graded sheet of the search whose source is ``search_source_ref`` into claims about the sequence
    ``searched_ref`` was searched for, and keep them (see the module). Returns ``{'claim_count', 'refs'}``: the number of
    claims and the references kept (the claims' source, the retained claim sheet and the feature records)."""
    store = ctx.store
    (grading,) = [entry['grading'] for entry in source_tool_grading_entries(store, search_source_ref)
                  if entry['grading']['sheet']['schema'] == GRADED_SHEET]
    mapping = store.get(searched_ref).get('mapping')
    subject_ref = searched_ref if mapping is None else mapping['path'][0]['subject_ref']
    groups = [await same_calls(ctx.model, labels) for labels in place_labels(grading, mapping)]
    sheet = blast_claim_sheet(grading, groups, mapping)
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
