from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.configuration import LiteratureConfiguration
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.policy import LiteraturePolicy
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.from_parent import LiteratureAssignment
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.goal import LiteratureGoal
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.task import LiteratureTaskOperations
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.source_operations import LiteratureSourceOperations
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.internal_summary import LiteratureSummary
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.scientific_records import LiteratureScientificRecords
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.population_custody import LiteraturePopulationCustody
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.received_evidence import LiteratureReceivedEvidence
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.to_parent import LiteratureReport
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.credit import LiteratureCredit
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.continuation import LiteratureContinuation
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.aggregate_records import private_record
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.decision_source import LiteratureDecisionSource
from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.decision_presentation import render_decision_context

class LiteratureEpisode(LiteratureConfiguration, LiteraturePolicy, LiteratureAssignment, LiteratureGoal, LiteratureTaskOperations, LiteratureSourceOperations, LiteratureSummary, LiteratureScientificRecords, LiteraturePopulationCustody, LiteratureReceivedEvidence, LiteratureReport, LiteratureCredit, LiteratureContinuation):
    roles = ('literature',)
    entry_roles = ()
    binding_path = 'legacy_annotation/published_evidence_assessment'
    commissioning_parent = 'legacy_annotation'
    decision_source_type = LiteratureDecisionSource
    decision_prompt_renderer = staticmethod(render_decision_context)

    def as_record(self):
        return private_record(self, 'legacy_annotation/published_evidence_assessment')

    @staticmethod
    def child_message_exchange(role, *, child_binding=None):
        if role == 'literature_strategy':
            from .to_child_evidence_search_strategy_improvement import prepare_request
            from .from_child_evidence_search_strategy_improvement import admit_return
            return prepare_request, admit_return
        if role == 'launch':
            from .execution_job_submission.episode import ExecutionSubmissionBinding
            if type(child_binding) is ExecutionSubmissionBinding:
                from .to_child_execution_job_submission import prepare_request
                from .from_child_execution_job_submission import admit_return
                return prepare_request, admit_return
        if role == 'results':
            from .execution_result_acquisition.episode import ResultAcquisitionBinding
            if type(child_binding) is ResultAcquisitionBinding:
                from .to_child_execution_result_acquisition import prepare_request
                from .from_child_execution_result_acquisition import admit_return
                return prepare_request, admit_return
        return None


# Exact private declaration identity; custom callbacks retain runtime fallback.
_declared_child_message_exchange = vars(LiteratureEpisode)["child_message_exchange"]
