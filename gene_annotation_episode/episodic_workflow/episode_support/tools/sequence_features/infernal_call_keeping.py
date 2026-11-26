"""Keeping the feature calls of one graded ``cmscan`` scan: the step that follows a completed scan (``rna_family_scan``) in the
same unit.

``keep_infernal_calls`` reads the kept sheet of the scan through custody, turns its hits into statements
(``infernal_calls.infernal_call_sheet``), and keeps through custody: the call sheet as a
retained grading labelled a ``tool_grading_sheet`` data product, and a source record of the provider
``feature_calling.infernal_calls`` whose operand is the sequence the statements are about. The sheet of feature calls reads
that source (``feature_candidates.feature_tests``); the scan's own source is not read by it (its sheet has no reader there).
The feature records of the candidates are then settled (``feature_record_keeping.settle_feature_records``).

The sequence the statements are about is the searched sequence itself, or, when the searched sequence is a product derived
from another (an extracted stretch: its record has a ``mapping``), the sequence its mapping leads back to. Nothing is decided
and nothing is checked here: whether and what to scan is the caller's. Writes only through ``ctx.store``.

Settings read (``ctx.settings``): ``covariance_databases`` (name -> the path of the database's manifest; its file
``family_types`` is the table of the type Rfam gives each family, which the statements' types are converted from)."""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.infernal_calls import (
    SCAN_SHEET, infernal_call_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    GRADING_KIND, record_grading_product, retain_tool_grading, source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_features.feature_record_keeping import (
    settle_feature_records)

PROVIDER = 'feature_calling.infernal_calls'


def keep_infernal_calls(ctx, *, scan_source_ref, searched_ref):
    """Turn the kept sheet of the scan whose source is ``scan_source_ref`` into feature calls and claims about the sequence
    ``searched_ref`` was scanned for, and keep them (see the module). Returns ``{'call_count', 'refs'}``: the number of
    statements and the references kept (the statements' source, the retained call sheet, its data product and the feature
    records)."""
    store = ctx.store
    (entry,) = [entry for entry in source_tool_grading_entries(store, scan_source_ref)
                if entry['grading']['sheet']['schema'] == SCAN_SHEET]
    mapping = store.get(searched_ref).get('mapping')
    subject_ref = searched_ref if mapping is None else mapping['path'][0]['subject_ref']
    # the table of family types of the database the scan was made against, named by that database's manifest
    manifest = json.loads(Path(ctx.settings['covariance_databases'][entry['grading']['sheet']['database']]).read_text())
    family_types = json.loads(Path(manifest['files']['family_types']['path']).read_text())
    sheet = infernal_call_sheet(entry['grading'], family_types, mapping)
    table_ref = store.get(scan_source_ref)['artifact_ref']
    scan_gradings = [row['id'] for row in products(store, GRADING_KIND) if row['generated_by'] == scan_source_ref]
    with store.transaction():
        grading = {'sheet': {**sheet, 'subject_ref': subject_ref}}
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=table_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': table_ref, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref],
            'operand_refs': [subject_ref]}, origin='tool')
        product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                         source_ref=source['id'], used=[entry['artifact_ref']], derived_from=scan_gradings)
    feature_refs = settle_feature_records(ctx, subject_ref=subject_ref, source_ref=source['id'])
    return {'call_count': len(sheet['statements']), 'refs': [source['id'], grading_ref, product['id'], *feature_refs]}


__all__ = ['PROVIDER', 'keep_infernal_calls']
