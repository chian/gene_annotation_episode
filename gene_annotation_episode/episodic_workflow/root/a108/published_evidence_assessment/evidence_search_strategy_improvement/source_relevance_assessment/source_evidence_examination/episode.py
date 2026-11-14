from __future__ import annotations
'Private A108 literature_page binding and declared responsibility connections.'
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_contracts import ROLES, _CHILDREN
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.configuration import LiteratureConfiguration
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.binding_record import LiteratureBindingRecord
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.from_parent import LiteratureAssignment
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.goal import LiteratureGoal
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_operations import LiteratureOperations
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.internal_summary import LiteratureSummary
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scientific_records import LiteratureScientificRecords
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_references import LiteratureReferences
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.to_parent import LiteratureReport
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.received_evidence import LiteratureReceivedEvidence
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.credit import LiteratureCredit
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.waiting import LiteratureWaiting
from importlib import import_module
from .yield_estimator import LiteratureYield
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.task import LiteratureTask
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.to_child_table_evidence_extraction import prepare_request as prepare_table_evidence_extraction
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.from_child_table_evidence_extraction import receive_report as receive_table_evidence_extraction
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.to_child_source_coverage_improvement import prepare_request as prepare_source_coverage_improvement
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.from_child_source_coverage_improvement import receive_report as receive_source_coverage_improvement
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.to_child_passage_evidence_extraction import prepare_request as prepare_passage_evidence_extraction
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.from_child_passage_evidence_extraction import receive_report as receive_passage_evidence_extraction
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.grading.contextual_interpretation import ContextualInterpretation
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.grading.contextual_subscoring import ContextualSubscoring
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.scoring.contextual_main_sheet import ContextualMainSheet

from gene_annotation_episode.episodic_workflow.root.a108.library.literature_experimental_prompt import render_literature_experimental_prompt

class LiteratureEpisode(LiteratureConfiguration, LiteratureBindingRecord, LiteratureAssignment, LiteratureGoal, LiteratureOperations, LiteratureSummary, LiteratureScientificRecords, LiteratureReferences, LiteratureReport, LiteratureReceivedEvidence, LiteratureCredit, LiteratureWaiting, LiteratureYield, ContextualInterpretation, ContextualSubscoring, ContextualMainSheet):
    decision_source_type = LiteratureTask
    decision_prompt_renderer = staticmethod(render_literature_experimental_prompt)
    binding_path = 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    commissioning_parent = 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    'Private A108 organism and sample context episode binding.'
    roles = ('literature_page',)
    entry_roles = ()

    def contract_information_configuration(self):
        return self._contract_information_profile

    def contract_information_profile(self, context):
        if context.role in ROLES or (context.role == 'annotation' and len(context.path) == 1 and (self.reference_parent_sources is not None)):
            return self._contract_information_profile
        return None

    @staticmethod
    def _role(role):
        if role != 'literature_page':
            raise ValueError('unsupported_literature_role:' + str(role))
        return role

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return _CHILDREN[role]

    def context_hook_applies(self, context):
        """Own local hooks; the literature parent owns external-family delivery hooks."""
        role = getattr(context, 'role', None)
        path = getattr(context, 'path', None)
        if role is None:
            role = path[-1][0] if path else context if isinstance(context, str) else None
        return role == 'literature_page' if role in ROLES else 'literature_page' == 'literature'

    def child_request_preparer(self, role):
        return {'literature_table': prepare_table_evidence_extraction, 'literature_ordered': prepare_source_coverage_improvement, 'literature_targeted': prepare_passage_evidence_extraction}.get(role)

    def child_report_receiver(self, role):
        return {'literature_table': receive_table_evidence_extraction, 'literature_ordered': receive_source_coverage_improvement, 'literature_targeted': receive_passage_evidence_extraction}.get(role)
