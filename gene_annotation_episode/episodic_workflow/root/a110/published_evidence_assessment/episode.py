"""Private literature episode behavior for A110."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.published_evidence_assessment.received_execution_information import received_execution_information as _received_execution_information
from .initial_information import initial_information as _private_initial_information
from importlib import import_module as _import_module
from .configuration import LiteratureConfiguration
from .binding_record import LiteratureBindingRecord
from .from_parent import LiteratureAssignment
from .source_custody import LiteratureSourceCustody
from .source_operations import LiteratureSourceOperations
from .goal import LiteratureGoal
from .internal_summary import LiteratureSummary
from .parent_context import LiteratureParentContext
from .numerical_report_facts import LiteratureNumericalReportFacts
from .received_reports import LiteratureReceivedReports
from .to_parent import LiteratureReport
from .credit import LiteratureCredit
LiteratureYield = _import_module('.yield', __package__).LiteratureYield
from .waiting import LiteratureWaiting
from .reaction_records import LiteratureReactionRecords
from .task import SourceInvestigationTask
from .task_presentation import present_source_context
from gene_annotation_episode.episodic_workflow.root.a110.published_evidence_assessment.received_execution_information import received_execution_information as _received_execution_information
from .initial_information import initial_information as _private_initial_information

class LiteratureEpisode(LiteratureConfiguration, LiteratureBindingRecord, LiteratureAssignment, LiteratureSourceCustody, LiteratureSourceOperations, LiteratureGoal, LiteratureSummary, LiteratureParentContext, LiteratureNumericalReportFacts, LiteratureReceivedReports, LiteratureReport, LiteratureCredit, LiteratureYield, LiteratureWaiting, LiteratureReactionRecords):
    received_execution_information = staticmethod(_received_execution_information)
    initial_information = staticmethod(_private_initial_information)
    binding_path = 'published_evidence_assessment'
    commissioning_parent = 'legacy_annotation'
    "A110's private reaction and feasibility literature episode."
    roles = ('literature',)
    entry_roles = ('literature',)

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
        return ('literature_strategy',)

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ('tool', 'child', 'redeliver_report')
    decision_source_type = SourceInvestigationTask
    decision_prompt_renderer = staticmethod(present_source_context)

    def child_request_assembler(self, role):
        if role == 'literature_strategy':
            from .to_child_evidence_search_strategy_improvement import assemble_request
            return assemble_request
        return None

    def execution_child_report_receiver(self, role):
        if role == 'literature_strategy':
            from .from_child_evidence_search_strategy_improvement import receive_report
            return receive_report
        return None

def create_binding_tree(services, **configuration):
    """Assemble the original caller configuration as seven private bindings."""
    from copy import deepcopy
    from gene_annotation_episode.episodic_workflow.root.a110.published_evidence_assessment.evidence_search_strategy_improvement.episode import LiteratureEpisode as Child1
    from gene_annotation_episode.episodic_workflow.root.a110.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode import LiteratureEpisode as Child2
    from gene_annotation_episode.episodic_workflow.root.a110.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode import LiteratureEpisode as Child3
    from gene_annotation_episode.episodic_workflow.root.a110.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode import LiteratureEpisode as Child4
    from gene_annotation_episode.episodic_workflow.root.a110.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode import LiteratureEpisode as Child5
    from gene_annotation_episode.episodic_workflow.root.a110.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode import LiteratureEpisode as Child6
    return tuple((binding(services, **deepcopy(configuration)) for binding in (LiteratureEpisode, Child1, Child2, Child3, Child4, Child5, Child6)))
