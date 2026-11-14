"""Connect the predefined private A103 literature_ordered source investigation."""
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
SourceInvestigationYield = import_module('.yield', __package__).SourceInvestigationYield
from .waiting import SourceInvestigationWaiting
from .source_contracts import ROLES, _CHILDREN

from .action_policy import SourceActionPolicy
from .child_commissioning import SourceChildCommissioning

class LiteratureEpisode(SourceActionPolicy, SourceChildCommissioning,SourceEpisodeConfiguration, SourceEpisodeBindingRecord, SourceInvestigationGoal, SourceAssignment, SourceOperations, SourceInterpretation, SourceScientificRecords, SourceReferences, SourceInvestigationSummary, SourceInvestigationReport, SourceReceivedEvidence, SourceInvestigationCredit, SourceInvestigationYield, SourceInvestigationWaiting):
    decision_source_type = SourceInvestigationTask
    decision_prompt_renderer = staticmethod(render_receiver_prompt)
    binding_path = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
    commissioning_parent = 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    'C7 binding for C10 assignments; no model connection or private loop.'
    roles = ('literature_ordered',)
    entry_roles = ()

