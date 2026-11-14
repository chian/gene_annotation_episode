from __future__ import annotations
'Connect the predefined private literature responsibilities.'
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.from_child_evidence_search_strategy_improvement import FromEvidenceSearchStrategyImprovement
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.to_child_evidence_search_strategy_improvement import to_child as to_evidence_search_strategy_improvement
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.task import LiteratureTask
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.source_contracts import ROLES, _CHILDREN, deepcopy
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.configuration import LiteratureConfiguration
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.binding_record import LiteratureBindingRecord
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.goal import LiteratureGoal
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.internal_summary import LiteratureSummary
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.scientific_records import LiteratureScientificRecords
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.task import LiteratureOperations
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.from_parent import LiteratureAssignment
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.source_operations import LiteratureSourceOperations
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.source_references import LiteratureReferences
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.to_parent import LiteratureReport
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.received_evidence import LiteratureReceivedEvidence
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.credit import LiteratureCredit
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.waiting import LiteratureWaiting
from importlib import import_module
LiteratureYield = import_module('.yield', __package__).LiteratureYield
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.to_child_evidence_search_strategy_improvement import prepare_request as prepare_evidence_search_strategy_improvement
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.from_child_evidence_search_strategy_improvement import receive_report as receive_evidence_search_strategy_improvement
from .grading.experimental_interpretation import ExperimentalInterpretation
from .grading.assay_subscoring import AssaySubscoring
from .scoring.experimental_main_sheet import ExperimentalMainSheet

from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_prompt import render_literature_experimental_prompt

class LiteratureEpisode(LiteratureConfiguration, LiteratureBindingRecord, LiteratureGoal, LiteratureSummary, LiteratureScientificRecords, LiteratureOperations, LiteratureAssignment, LiteratureSourceOperations, LiteratureReferences, LiteratureReport, LiteratureReceivedEvidence, LiteratureCredit, LiteratureWaiting, LiteratureYield, FromEvidenceSearchStrategyImprovement, ExperimentalInterpretation, AssaySubscoring, ExperimentalMainSheet):
    decision_source_type = LiteratureTask
    decision_prompt_renderer = staticmethod(render_literature_experimental_prompt)
    binding_path = 'published_evidence_assessment'
    commissioning_parent = 'legacy_annotation'
    'C7 binding for C10 assignments; no model connection or private loop.'
    roles = ('literature',)
    entry_roles = ('literature',)

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
        if role != 'literature':
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
        return role == 'literature' if role in family_roles else 'literature' == 'literature'

    def prepare_child_request(self, parent, role, assignment):
        handlers = {'literature_strategy': to_evidence_search_strategy_improvement}
        return handlers[role](parent, assignment)

    def receive_child_result(self, context, role, form, schema, operation_key):
        handlers = {'literature_strategy': self.receive_evidence_search_strategy_improvement}
        return handlers[role](context, form, schema, operation_key)

    def child_request_preparer(self, role):
        return {'literature_strategy': prepare_evidence_search_strategy_improvement}.get(role)

    def child_report_receiver(self, role):
        return {'literature_strategy': receive_evidence_search_strategy_improvement}.get(role)

def create_binding_tree(services, **configuration):
    """Assemble the original caller configuration as seven private bindings."""
    from copy import deepcopy
    from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.episode import LiteratureEpisode as Child1
    from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode import LiteratureEpisode as Child2
    from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode import LiteratureEpisode as Child3
    from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode import LiteratureEpisode as Child4
    from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode import LiteratureEpisode as Child5
    from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode import LiteratureEpisode as Child6
    return tuple((binding(services, **deepcopy(configuration)) for binding in (LiteratureEpisode, Child1, Child2, Child3, Child4, Child5, Child6)))
