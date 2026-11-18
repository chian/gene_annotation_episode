"""Private A103 Results received records."""
from __future__ import annotations
from .execution_contracts import BLAST_GRADED_RETURN_SOURCE, RESULT_PROVIDER, deepcopy, plain

class ResultsReceivedRecords:

    def _has_appservice(self):
        return self.api_execution is not None and any((service.service == 'bvbrc_appservice' for service in self.api_execution.services.values()))

    def _has_uniprot(self):
        return self.api_execution is not None and any((service.service == 'uniprot' for service in self.api_execution.services.values()))

    @staticmethod
    def _appservice_sources():
        from gene_annotation_episode.episodic_workflow.root.a103.bvbrc_homology_returns import homology_fact_sources
        return {**homology_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning': 'Actually received AppService preparation, Workspace, upload or observation receipts; these are not scientific result acquisitions.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'}, 'x-source': 'bvbrc_appservice_support_refs'}}}

    def _received(self, context, selection=None, *, _handoff_read=None):
        with self.store.read_snapshot():
            selection = self._selection(context, selection)
            read = self.job_progress_provider.targets._handoff_reader() if _handoff_read is None else _handoff_read
            handoffs, results = ({}, {})
            for reference in dict.fromkeys(selection['known_record_refs']):
                source = self.store.get(reference)
                if source.get('provider') == RESULT_PROVIDER:
                    if source.get('version') in {'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1', 'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1', 'native_protein_structure_bundle_v1', 'native_rna_structure_bundle_v1'}:
                        continue
                    body = self._read_result(reference, context.scope)
                    if context.role == 'results' and body['assignment'] != plain(context.assignment):
                        continue
                    results[reference] = body
                    continue
                if source.get('provider') != 'episode.practical_receipt' and (not (self.api_execution is not None and self.api_execution.is_handoff_source(reference))):
                    continue
                try:
                    target, _, returnable = read(reference, context.scope)
                except (ValueError, KeyError):
                    continue
                try:
                    self._context_target(context, target)
                except ValueError:
                    continue
                if returnable:
                    handoffs[reference] = target
            return (selection, handoffs, results)

    def _forwards_bvbrc_reports(self, role):
        return role in {'annotation', 'gene_context_evidence'} and self.api_execution is not None and any((service.service == 'bvbrc_data' for service in self.api_execution.services.values()))

    def _forwards_minhash_reports(self, role):
        return role in {'annotation', 'gene_context_evidence'} and self.api_execution is not None and any((service.service == 'bvbrc_minhash' for service in self.api_execution.services.values()))

