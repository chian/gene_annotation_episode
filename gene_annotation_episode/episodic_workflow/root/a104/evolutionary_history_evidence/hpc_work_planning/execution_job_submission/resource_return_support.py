"""Private A104 Launch resource return support."""
from __future__ import annotations

class LaunchResourceReturns:

    def _has_appservice(self):
        return self.api_execution is not None and any((service.service == 'bvbrc_appservice' for service in self.api_execution.services.values()))

    def _has_uniprot(self):
        return self.api_execution is not None and any((service.service == 'uniprot' for service in self.api_execution.services.values()))

    @staticmethod
    def _appservice_sources():
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_homology_returns import homology_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_phylogeny_returns import phylogeny_fact_sources
        from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_returns import proteome_fact_sources
        return {**homology_fact_sources(), **phylogeny_fact_sources(), **proteome_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning': 'Actually received AppService preparation, Workspace, upload or observation receipts; these are not scientific result acquisitions.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'}, 'x-source': 'bvbrc_appservice_support_refs'}}}

    def _forwards_bvbrc_reports(self, role):
        return role in {'annotation', 'evolutionary_history_evidence'} and self.api_execution is not None and any((service.service == 'bvbrc_data' for service in self.api_execution.services.values()))
