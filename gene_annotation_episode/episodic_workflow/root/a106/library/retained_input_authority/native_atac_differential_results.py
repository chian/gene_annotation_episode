"""Selected atac result work inside the existing results episode.

The episode selects status or collection. This binding records that original
action, retains closed output, invokes one finite calculator and returns only
the requested fields. It makes no scientific decision or resource selection.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.communication import plain
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.atac_differential_result_receipts import AtacDifferentialResultReceipts, decode, empty_facts, require, same, unique
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.atac_differential_return_views import FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE, validate_atac_fact_values
from gene_annotation_episode.episodic_workflow.root.a106.native_file_capture import retained_native_file

def _bundle_files(bundle):
    yield bundle['sheet']
    yield from (row['file'] for row in bundle['tables'])

class NativeAtacDifferentialResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.receipts = AtacDifferentialResultReceipts(owner)

    def applies(self, context):
        return context.role == 'results' and plain(context.assignment).get('selector', {}).get('version') == 'atac_differential_result_selector_v1'

    def _verify_artifacts(self, receipt):
        files = receipt['qualified_files']
        if receipt['facts'][PROJECTION_SOURCE]:
            for role in ('sheet', 'calculations', 'projection'):
                retained_native_file(self.store, files[role])
            wanted = {'interval_components': 'components', 'derived_regions': 'regions'}.get(receipt['projection']['kind'])
            for row in files['calculated_tables']:
                if row['role'] == wanted and row['file'] is not None:
                    retained_native_file(self.store, row['file'])
            require(same(decode(retained_native_file(self.store, files['projection']).read_bytes()), receipt['projection']))
        for bundle in receipt['facts'][SAVED_SOURCE]:
            for file in _bundle_files(bundle):
                retained_native_file(self.store, file)

    def own_fact_groups(self, context, *, verify_artifacts):
        require(type(verify_artifacts) is bool)
        groups = empty_facts()
        for receipt in self.receipts.completed_receipts(context):
            if verify_artifacts:
                self._verify_artifacts(receipt)
            for source in FACT_SOURCES:
                groups[source].extend(receipt['facts'][source])
        return {source: unique(rows) for source, rows in groups.items()}

    def completed_saved_bundle_origins(self, context, bundle):
        validate_atac_fact_values(SAVED_SOURCE, [bundle])
        return tuple(({'episode_id': receipt['intent']['episode_id'], 'operation_key': receipt['intent']['operation_key']} for receipt in self.receipts.completed_receipts(context) if any((same(bundle, row) for row in receipt['facts'][SAVED_SOURCE]))))

    def resolve_own(self, context, reference, namespace):
        if namespace not in {None, 'artifact'}:
            return False
        return any((file['artifact_ref'] == reference for bundle in self.own_fact_groups(context, verify_artifacts=False)[SAVED_SOURCE] for file in _bundle_files(bundle)))

    def owns_reference(self, reference):
        return self.receipts.owns_reference(reference)
