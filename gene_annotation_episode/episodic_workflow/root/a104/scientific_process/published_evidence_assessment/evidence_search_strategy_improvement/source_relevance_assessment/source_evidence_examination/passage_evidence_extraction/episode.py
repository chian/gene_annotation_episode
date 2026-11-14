"""Private literature_targeted episode behavior for A104."""
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
    binding_path = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
    commissioning_parent = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    'Private scientific investigation with its own task and original configured services.'
    roles = ('literature_targeted',)
    entry_roles = ()

    decision_source_type = SourceInvestigationTask
    decision_prompt_renderer = staticmethod(present_source_context)
