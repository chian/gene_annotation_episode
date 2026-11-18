"""Private grading contextual subscoring invocation."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_contracts import ContractError

class ContextualSubscoring:

    def _required_grading_repository(self, context=None):
        return self._a108_grading_repository()

    def _a108_grading_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_grading_storage import LiteratureA108GradingRepository
        if not hasattr(self, '_a108_grading_repo'):
            self._a108_grading_repo = LiteratureA108GradingRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._a108_grading_repo
