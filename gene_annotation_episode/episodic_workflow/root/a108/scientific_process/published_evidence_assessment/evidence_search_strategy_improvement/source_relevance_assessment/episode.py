from __future__ import annotations
'Private A108 literature_search binding and declared responsibility connections.'
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_contracts import ROLES, _CHILDREN
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.configuration import LiteratureConfiguration
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.binding_record import LiteratureBindingRecord
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.from_parent import LiteratureAssignment
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.goal import LiteratureGoal
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_operations import LiteratureOperations
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.internal_summary import LiteratureSummary
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.scientific_records import LiteratureScientificRecords
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_references import LiteratureReferences
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.to_parent import LiteratureReport
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.received_evidence import LiteratureReceivedEvidence
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.credit import LiteratureCredit
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.waiting import LiteratureWaiting
from importlib import import_module
LiteratureYield = import_module('.yield', __package__).LiteratureYield
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.task import LiteratureTask
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.to_child_source_evidence_examination import prepare_request as prepare_source_evidence_examination
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.from_child_source_evidence_examination import receive_report as receive_source_evidence_examination
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.grading.contextual_interpretation import ContextualInterpretation
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.grading.contextual_subscoring import ContextualSubscoring
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.scoring.contextual_main_sheet import ContextualMainSheet

from gene_annotation_episode.episodic_workflow.root.a108.library.literature_experimental_prompt import render_literature_experimental_prompt

class LiteratureEpisode(LiteratureConfiguration, LiteratureBindingRecord, LiteratureAssignment, LiteratureGoal, LiteratureOperations, LiteratureSummary, LiteratureScientificRecords, LiteratureReferences, LiteratureReport, LiteratureReceivedEvidence, LiteratureCredit, LiteratureWaiting, LiteratureYield, ContextualInterpretation, ContextualSubscoring, ContextualMainSheet):
    decision_source_type = LiteratureTask
    decision_prompt_renderer = staticmethod(render_literature_experimental_prompt)
    binding_path = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    commissioning_parent = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement'
    'Private A108 organism and sample context episode binding.'
    roles = ('literature_search',)
    entry_roles = ()

    def contract_information_configuration(self):
        return self._contract_information_profile

    def contract_information_profile(self, context):
        if context.role in ROLES or (context.role == 'annotation' and len(context.path) == 1 and (self.reference_parent_sources is not None)):
            return self._contract_information_profile
        return None

    @staticmethod
    def _role(role):
        if role != 'literature_search':
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
        return role == 'literature_search' if role in ROLES else 'literature_search' == 'literature'

    def child_request_preparer(self, role):
        return {'literature_page': prepare_source_evidence_examination}.get(role)

    def child_report_receiver(self, role):
        return {'literature_page': receive_source_evidence_examination}.get(role)
