"""Private A107 literature_search episode."""
from __future__ import annotations
from importlib import import_module as _import_module
from .task import SourceInvestigationTask
from .task_presentation import present_source_context
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
from .source_repositories import LiteratureRepositories
from gene_annotation_episode.episodic_workflow.root.a107.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.received_execution_information import received_execution_information as _received_execution_information
from gene_annotation_episode.episodic_workflow.root.a107.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.received_api_reports import received_api_reports as _received_api_reports
from .initial_information import initial_information as _private_initial_information

class LiteratureEpisode(LiteratureConfiguration, LiteratureBindingRecord, LiteratureAssignment, LiteratureSourceCustody, LiteratureSourceOperations, LiteratureGoal, LiteratureSummary, LiteratureParentContext, LiteratureNumericalReportFacts, LiteratureReceivedReports, LiteratureReport, LiteratureCredit, LiteratureYield, LiteratureWaiting, LiteratureRepositories):
    received_execution_information = staticmethod(_received_execution_information)
    received_api_reports = staticmethod(_received_api_reports)
    initial_information = staticmethod(_private_initial_information)
    binding_path = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    commissioning_parent = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement'
    "A107's private required-partner literature episode."
    roles = ('literature_search',)
    entry_roles = ()

    @staticmethod
    def _role(role):
        if role != 'literature_search':
            raise ValueError('unsupported_literature_role:' + str(role))
        return role

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ('tool', 'child', 'redeliver_report')

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return ('literature_page',)
    decision_source_type = SourceInvestigationTask
    decision_prompt_renderer = staticmethod(present_source_context)

    def child_request_assembler(self, role):
        if role == 'literature_page':
            from .to_child_source_evidence_examination import assemble_request
            return assemble_request
        return None

    def execution_child_report_receiver(self, role):
        if role == 'literature_page':
            from .from_child_source_evidence_examination import receive_report
            return receive_report
        return None
