from __future__ import annotations
'Connect the predefined private literature_ordered responsibilities.'
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.task import LiteratureTask
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.source_contracts import ROLES, _CHILDREN
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.configuration import LiteratureConfiguration
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.binding_record import LiteratureBindingRecord
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.goal import LiteratureGoal
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.internal_summary import LiteratureSummary
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.scientific_records import LiteratureScientificRecords
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.task import LiteratureOperations
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.from_parent import LiteratureAssignment
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.source_operations import LiteratureSourceOperations
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.source_references import LiteratureReferences
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.to_parent import LiteratureReport
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.received_evidence import LiteratureReceivedEvidence
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.credit import LiteratureCredit
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.waiting import LiteratureWaiting
from importlib import import_module
LiteratureYield = import_module('.yield', __package__).LiteratureYield
from .grading.experimental_interpretation import ExperimentalInterpretation
from .grading.assay_subscoring import AssaySubscoring
from .scoring.experimental_main_sheet import ExperimentalMainSheet

from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_prompt import render_literature_experimental_prompt

class LiteratureEpisode(LiteratureConfiguration, LiteratureBindingRecord, LiteratureGoal, LiteratureSummary, LiteratureScientificRecords, LiteratureOperations, LiteratureAssignment, LiteratureSourceOperations, LiteratureReferences, LiteratureReport, LiteratureReceivedEvidence, LiteratureCredit, LiteratureWaiting, LiteratureYield, ExperimentalInterpretation, AssaySubscoring, ExperimentalMainSheet):
    decision_source_type = LiteratureTask
    decision_prompt_renderer = staticmethod(render_literature_experimental_prompt)
    binding_path = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
    commissioning_parent = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    'C7 binding for C10 assignments; no model connection or private loop.'
    roles = ('literature_ordered',)
    entry_roles = ()

    def _enabled(self, option, context=None):
        return option == 'assay_grading_population' and self.assay_grading_population

    def contract_information_configuration(self):
        return self._contract_information_profile

    def contract_information_profile(self, context):
        if context.role in ROLES or (context.role == 'annotation' and len(context.path) == 1 and (self.reference_parent_sources is not None)):
            return self._contract_information_profile
        return None

    @staticmethod
    def _role(role):
        if role != 'literature_ordered':
            raise ValueError('unsupported_literature_role:' + str(role))
        return role

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return _CHILDREN[role]

    def child_assignment_schema(self, parent, role):
        return self.assignment_schema(role, context=parent)

    def context_hook_applies(self, context):
        """Own local hooks; the literature parent owns external-family delivery hooks."""
        role = getattr(context, 'role', None)
        path = getattr(context, 'path', None)
        if role is None:
            role = path[-1][0] if path else context if isinstance(context, str) else None
        family_roles = ('literature', 'literature_strategy', 'literature_search', 'literature_page', 'literature_table', 'literature_ordered', 'literature_targeted')
        return role == 'literature_ordered' if role in family_roles else 'literature_ordered' == 'literature'
