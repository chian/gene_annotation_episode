"""Keeping the claims of one graded BLAST search: the step that follows the grading of a search in the same unit.

``keep_blast_claims`` reads the graded sheet of the search through custody, turns its hits into claims
(``blast_claims.blast_claim_sheet``), and keeps through custody: the claim sheet as a retained grading, and a source
record of the provider ``feature_calling.blast_claims`` whose operand is the
sequence the claims are about. The sheet of feature calls reads that source (``feature_candidates.feature_tests``).
The feature records of the candidates are then settled (``feature_record_keeping.settle_feature_records``): the unit
must hold every graded source of the sequence, so the search child is passed them with its commission.

In the same transaction it keeps the taxon claims of the same hits (``search_taxon_claims.search_taxon_claim_sheet``: per
taxon the hits name, its hits and the closeness and share covered of its best one) for the organism side: the claim sheet
as a retained grading, labelled as a ``tool_grading_sheet`` data product (``record_grading_product``, made from the
search's graded sheet), on a source of its own provider ``feature_calling.search_taxon_claims`` whose operand is the same
sequence. The scoring sheet of candidate taxa reads that source (``taxon_candidates.taxon_tests``); the sheet of feature
calls has no reader for it and passes it over.

The sequence the claims are about is the searched sequence itself, or, when the searched sequence is a product derived
from another (a translation, an extracted stretch: its record has a ``mapping``), the sequence its mapping leads back to.
Nothing is decided and nothing is checked here: whether and what to search is the caller's. Writes only through
``ctx.store``."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.blast_claims import (
    GRADED_SHEET, blast_claim_sheet, place_labels)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading, source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.search_taxon_claims import (
    search_taxon_claim_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_features.feature_record_keeping import (
    settle_feature_records)

PROVIDER = 'feature_calling.blast_claims'
TAXON_PROVIDER = 'feature_calling.search_taxon_claims'
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


def keep_taxon_claims(store, *, search_source_ref, searched_ref):
    """Keep the taxon claims of the hits of the graded search whose source is ``search_source_ref`` (see the module),
    about the sequence ``searched_ref`` was searched for. Returns the references kept: the claims' source, their
    retained sheet and its data-product row."""
    (graded,) = [entry for entry in source_tool_grading_entries(store, search_source_ref)
                 if entry['grading']['sheet']['schema'] == GRADED_SHEET]
    mapping = store.get(searched_ref).get('mapping')
    subject_ref = searched_ref if mapping is None else mapping['path'][0]['subject_ref']
    taxon_sheet = {**search_taxon_claim_sheet(graded['grading']), 'subject_ref': subject_ref}
    report_ref = store.get(search_source_ref)['artifact_ref']
    with store.transaction():
        taxon_grading_ref = retain_tool_grading(store, provider=TAXON_PROVIDER, native_artifact_ref=report_ref,
                                                grading={'sheet': taxon_sheet})
        taxon_source = store.put('source', {
            'provider': TAXON_PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': report_ref, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None, 'auxiliary_artifact_refs': [taxon_grading_ref],
            'operand_refs': [subject_ref]}, origin='tool')
        taxon_product = record_grading_product(store, grading_ref=taxon_grading_ref, grading={'sheet': taxon_sheet},
                                               provider=TAXON_PROVIDER, source_ref=taxon_source['id'],
                                               used=[graded['artifact_ref']])
    return [taxon_source['id'], taxon_grading_ref, taxon_product['id']]


async def keep_blast_claims(ctx, *, search_source_ref, searched_ref):
    """Turn the graded sheet of the search whose source is ``search_source_ref`` into claims about the sequence
    ``searched_ref`` was searched for, and keep them (see the module). Returns ``{'claim_count', 'refs'}``: the number of
    claims and the references kept (the claims' source, the retained claim sheet and the feature records; then the taxon
    claims' source, their retained sheet and its data-product row)."""
    store = ctx.store
    (graded,) = [entry for entry in source_tool_grading_entries(store, search_source_ref)
                 if entry['grading']['sheet']['schema'] == GRADED_SHEET]
    grading = graded['grading']
    mapping = store.get(searched_ref).get('mapping')
    subject_ref = searched_ref if mapping is None else mapping['path'][0]['subject_ref']
    groups = [await same_calls(ctx.model, labels) for labels in place_labels(grading, mapping)]
    sheet = blast_claim_sheet(grading, groups, mapping)
    report_ref = store.get(search_source_ref)['artifact_ref']
    with store.transaction():
        kept = {**sheet, 'subject_ref': subject_ref}
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=report_ref,
                                          grading={'sheet': kept})
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': report_ref, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref],
            'operand_refs': [subject_ref]}, origin='tool')
        # the taxon claims of the same hits, for the organism side, on a source of their own
        taxon_refs = keep_taxon_claims(store, search_source_ref=search_source_ref, searched_ref=searched_ref)
    feature_refs = settle_feature_records(ctx, subject_ref=subject_ref, source_ref=source['id'])
    return {'claim_count': len(sheet['claims']), 'refs': [source['id'], grading_ref, *feature_refs, *taxon_refs]}





def hits_by_bit_score(report, grading, length):
    """The hits of a graded search as ``[(accession, bit score)]``, the highest bit score first, ties by accession: the
    order in which a search's hits are named when the search is read for the features of the searched sequence
    (``bvbrc_blast_search.fetch_and_grade_search``, ``order``). It reads the grader's own facts of each hit, whatever the
    program of the search; ``report`` and ``length`` are not needed for it."""
    sheet = grading['sheet']
    accession = {hit['hit_index']: hit['descriptions'][0]['accession'] for hit in sheet['normalized_result']['hits']}
    return sorted(((accession[hit['hit_index']], hit['measurements']['maximum_bit_score']) for hit in sheet['hits']),
                  key=lambda pair: (-pair[1], pair[0]))


__all__ = ['PROVIDER', 'TAXON_PROVIDER', 'hits_by_bit_score', 'keep_blast_claims', 'keep_taxon_claims']
