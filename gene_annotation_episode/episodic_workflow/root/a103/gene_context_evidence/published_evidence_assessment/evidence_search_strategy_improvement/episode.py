"""Connect the predefined private A103 literature_strategy source investigation."""
from __future__ import annotations
from .task_presentation import render_receiver_prompt
from .task import SourceInvestigationTask
from .configuration import SourceEpisodeConfiguration
from .binding_record import SourceEpisodeBindingRecord
from .goal import SourceInvestigationGoal
from .from_parent import SourceAssignment
from .source_operations import SourceOperations
from .source_interpretation import SourceInterpretation
from .scientific_records import SourceScientificRecords
from .source_references import SourceReferences
from .internal_summary import SourceInvestigationSummary
from .to_parent import SourceInvestigationReport
from .received_evidence import SourceReceivedEvidence
from .credit import SourceInvestigationCredit
from importlib import import_module
from .yield_estimator import SourceInvestigationYield
from .waiting import SourceInvestigationWaiting
from .source_contracts import ROLES, _CHILDREN
from .to_child_source_relevance_assessment import SourceRelevanceAssessmentRequest
from .from_child_source_relevance_assessment import receive_source_relevance_assessment_report

from .action_policy import SourceActionPolicy
from .child_commissioning import SourceChildCommissioning

class LiteratureEpisode(SourceActionPolicy, SourceChildCommissioning,SourceEpisodeConfiguration, SourceEpisodeBindingRecord, SourceInvestigationGoal, SourceAssignment, SourceOperations, SourceInterpretation, SourceScientificRecords, SourceReferences, SourceInvestigationSummary, SourceInvestigationReport, SourceReceivedEvidence, SourceInvestigationCredit, SourceInvestigationYield, SourceInvestigationWaiting, SourceRelevanceAssessmentRequest):
    decision_source_type = SourceInvestigationTask
    decision_prompt_renderer = staticmethod(render_receiver_prompt)
    binding_path = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    commissioning_parent = 'gene_context_evidence/published_evidence_assessment'
    'C7 binding for C10 assignments; no model connection or private loop.'
    roles = ('literature_strategy',)
    entry_roles = ()

