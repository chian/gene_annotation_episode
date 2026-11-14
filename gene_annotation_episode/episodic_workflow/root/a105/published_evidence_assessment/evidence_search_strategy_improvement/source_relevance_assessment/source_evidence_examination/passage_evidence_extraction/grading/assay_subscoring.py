"""Private grading assay subscoring invocation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.source_contracts import json, validate_schema
from gene_annotation_episode.domain import ContractError

class AssaySubscoring:

    def _required_grading_repository(self, context=None):
        if self._enabled('assay_grading_population', context):
            return self._assay_grading_repository()
        return None

    def _assay_grading_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import LiteratureAssayGradingRepository
        if not hasattr(self, '_assay_grading_repo'):
            self._assay_grading_repo = LiteratureAssayGradingRepository(self.services.workflow.store, self.services.workflow.run_id, read_cells=self._assay_grading_source_cells)
        return self._assay_grading_repo
