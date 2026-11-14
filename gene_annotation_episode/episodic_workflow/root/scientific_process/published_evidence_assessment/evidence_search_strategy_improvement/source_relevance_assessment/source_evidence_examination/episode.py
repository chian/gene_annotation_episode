from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.configuration import LiteratureConfiguration
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.policy import LiteraturePolicy
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.from_parent import LiteratureAssignment
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.goal import LiteratureGoal
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.task import LiteratureTaskOperations
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_operations import LiteratureSourceOperations
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.internal_summary import LiteratureSummary
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scientific_records import LiteratureScientificRecords
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.population_custody import LiteraturePopulationCustody
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.received_evidence import LiteratureReceivedEvidence
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.to_parent import LiteratureReport
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.credit import LiteratureCredit
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.continuation import LiteratureContinuation
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.aggregate_records import private_record
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.decision_source import LiteratureDecisionSource
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.decision_presentation import render_decision_context

class LiteratureEpisode(LiteratureConfiguration, LiteraturePolicy, LiteratureAssignment, LiteratureGoal, LiteratureTaskOperations, LiteratureSourceOperations, LiteratureSummary, LiteratureScientificRecords, LiteraturePopulationCustody, LiteratureReceivedEvidence, LiteratureReport, LiteratureCredit, LiteratureContinuation):
    roles = ('literature_page',)
    entry_roles = ()
    binding_path = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    commissioning_parent = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    decision_source_type = LiteratureDecisionSource
    decision_prompt_renderer = staticmethod(render_decision_context)

    def as_record(self):
        return private_record(self, 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination')

    @staticmethod
    def child_message_exchange(role):
        if role == 'literature_table':
            from .to_child_table_evidence_extraction import prepare_request
            from .from_child_table_evidence_extraction import admit_return
            return prepare_request, admit_return
        if role == 'literature_ordered':
            from .to_child_source_coverage_improvement import prepare_request
            from .from_child_source_coverage_improvement import admit_return
            return prepare_request, admit_return
        if role == 'literature_targeted':
            from .to_child_passage_evidence_extraction import prepare_request
            from .from_child_passage_evidence_extraction import admit_return
            return prepare_request, admit_return
        return None


# Exact private declaration identity; custom callbacks retain runtime fallback.
_declared_child_message_exchange = vars(LiteratureEpisode)["child_message_exchange"]
