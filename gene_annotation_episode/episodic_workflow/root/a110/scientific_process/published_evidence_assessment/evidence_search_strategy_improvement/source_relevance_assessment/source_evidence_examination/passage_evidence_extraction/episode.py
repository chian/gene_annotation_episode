"""Private literature_targeted episode behavior for A110."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.received_execution_information import received_execution_information as _received_execution_information
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
from .yield_estimator import LiteratureYield
from .waiting import LiteratureWaiting
from .reaction_records import LiteratureReactionRecords
from .task import SourceInvestigationTask
from .task_presentation import present_source_context
from gene_annotation_episode.episodic_workflow.root.a110.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.received_execution_information import received_execution_information as _received_execution_information
from .initial_information import initial_information as _private_initial_information

class LiteratureEpisode(LiteratureConfiguration, LiteratureBindingRecord, LiteratureAssignment, LiteratureSourceCustody, LiteratureSourceOperations, LiteratureGoal, LiteratureSummary, LiteratureParentContext, LiteratureNumericalReportFacts, LiteratureReceivedReports, LiteratureReport, LiteratureCredit, LiteratureYield, LiteratureWaiting, LiteratureReactionRecords):
    received_execution_information = staticmethod(_received_execution_information)
    initial_information = staticmethod(_private_initial_information)
    binding_path = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
    commissioning_parent = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    "A110's private reaction and feasibility literature episode."
    roles = ('literature_targeted',)
    entry_roles = ()

    @staticmethod
    def _role(role):
        if role != 'literature_targeted':
            raise ValueError('unsupported_literature_role:' + str(role))
        return role

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        return self.child_roles(parent.role, context=parent)

    def child_roles(self, role, *, context=None):
        self._role(role)
        return ()

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ('tool', 'child', 'redeliver_report')
    decision_source_type = SourceInvestigationTask
    decision_prompt_renderer = staticmethod(present_source_context)
