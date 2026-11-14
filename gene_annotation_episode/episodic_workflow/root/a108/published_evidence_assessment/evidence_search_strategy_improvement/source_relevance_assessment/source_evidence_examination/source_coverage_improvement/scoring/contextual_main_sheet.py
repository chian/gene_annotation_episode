"""Private scoring contextual main sheet invocation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.source_contracts import ContractError

class ContextualMainSheet:

    def _a108_aggregation_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_aggregation_storage import LiteratureA108AggregationRepository
        if not hasattr(self, '_a108_aggregation_repo'):
            self._a108_aggregation_repo = LiteratureA108AggregationRepository(self.services.workflow.store, self.services.workflow.run_id, read_cells=lambda context, sheet_ref, components: self._a108_grading_repository().fact_cells(context, [sheet_ref], components=components))
        return self._a108_aggregation_repo
