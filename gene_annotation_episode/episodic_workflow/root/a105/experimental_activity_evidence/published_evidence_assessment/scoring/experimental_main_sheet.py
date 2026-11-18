"""Private scoring experimental main sheet invocation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.published_evidence_assessment.source_contracts import json, validate_schema
from gene_annotation_episode.domain import ContractError

class ExperimentalMainSheet:

    def _a105_aggregation_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_aggregation_storage import LiteratureA105AggregationRepository
        if not hasattr(self, '_a105_aggregation_repo'):
            self._a105_aggregation_repo = LiteratureA105AggregationRepository(self.services.workflow.store, self.services.workflow.run_id, read_cells=lambda context, sheet_ref, components: self._assay_grading_repository().fact_cells(context, [sheet_ref], components=components))
        return self._a105_aggregation_repo
