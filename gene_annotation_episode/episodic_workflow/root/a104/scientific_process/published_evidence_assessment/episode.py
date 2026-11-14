"""Private literature episode behavior for A104."""
from __future__ import annotations
from importlib import import_module as _import_module
from .task import SourceInvestigationTask
from .task_presentation import present_source_context
from .contracts import ROLES, _CHILDREN
from .configuration import LiteratureConfiguration
from .binding_record import LiteratureBindingRecord
from .from_parent import LiteratureAssignment
from .source_custody import LiteratureSourceCustody
from .source_operations import LiteratureSourceOperations
from .goal import LiteratureGoal
from .internal_summary import LiteratureSummary
from .parent_context import LiteratureParentContext
from .scientific_interpretation import LiteratureScientificInterpretation
from .numerical_report_facts import LiteratureNumericalReportFacts
from .received_reports import LiteratureReceivedReports
from .to_parent import LiteratureReport
from .credit import LiteratureCredit
from .yield_estimator import LiteratureYield
from .waiting import LiteratureWaiting
from .source_repositories import LiteratureRepositories

from .role_policy import LiteratureRolePolicy

class LiteratureEpisode(LiteratureRolePolicy, LiteratureConfiguration, LiteratureBindingRecord, LiteratureAssignment, LiteratureSourceCustody, LiteratureSourceOperations, LiteratureGoal, LiteratureSummary, LiteratureParentContext, LiteratureScientificInterpretation, LiteratureNumericalReportFacts, LiteratureReceivedReports, LiteratureReport, LiteratureCredit, LiteratureYield, LiteratureWaiting, LiteratureRepositories):
    binding_path = 'scientific_process/published_evidence_assessment'
    commissioning_parent = 'scientific_process'
    'Private scientific investigation with its own task and original configured services.'
    roles = ('literature',)
    entry_roles = ('literature',)

    decision_source_type = SourceInvestigationTask
    decision_prompt_renderer = staticmethod(present_source_context)

    def child_request_assembler(self, role):
        if role == 'literature_strategy':
            from .to_child_evidence_search_strategy_improvement import assemble_request
            return assemble_request
        return None

    def child_report_receiver(self, role):
        if role == 'literature_strategy':
            from .from_child_evidence_search_strategy_improvement import receive_report
            return receive_report
        return None

def create_binding_tree(services, **configuration):
    """Assemble the original caller configuration as seven private bindings."""
    from copy import deepcopy
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.episode import LiteratureEpisode as Child1
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode import LiteratureEpisode as Child2
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode import LiteratureEpisode as Child3
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode import LiteratureEpisode as Child4
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode import LiteratureEpisode as Child5
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode import LiteratureEpisode as Child6
    return tuple((binding(services, **deepcopy(configuration)) for binding in (LiteratureEpisode, Child1, Child2, Child3, Child4, Child5, Child6)))
