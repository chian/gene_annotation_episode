"""Selected FBA-result operations within the existing results episode.

The native writer, finite numerical worker, return authority and episode
controller retain their separate responsibilities. This host records one
selected operation and publishes its original qualified values.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.communication import plain
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.flux_balance_result_receipts import FluxBalanceResultReceipts, empty_facts, require, same, unique, FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE
from gene_annotation_episode.episodic_workflow.root.a106.native_file_capture import retained_native_file
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_flux_balance_storage import read_json

class NativeFluxBalanceResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.receipts = FluxBalanceResultReceipts(owner)

    def applies(self, context):
        return context.role == 'results' and plain(context.assignment).get('selector', {}).get('version') == 'flux_balance_result_selector_v1'

    def _verify_artifacts(self, receipt):
        files = receipt['qualified_files']
        if receipt['facts'][PROJECTION_SOURCE]:
            retained_native_file(self.store, files['projection'])
            require(same(read_json(retained_native_file(self.store, files['projection'])), receipt['projection']))
        for file in receipt['facts'][SAVED_SOURCE]:
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

    def resolve_own(self, context, reference, namespace):
        if namespace not in {None, 'artifact'}:
            return False
        return any((file['artifact_ref'] == reference for file in self.own_fact_groups(context, verify_artifacts=False)[SAVED_SOURCE]))

    def owns_reference(self, reference):
        return self.receipts.owns_reference(reference)
