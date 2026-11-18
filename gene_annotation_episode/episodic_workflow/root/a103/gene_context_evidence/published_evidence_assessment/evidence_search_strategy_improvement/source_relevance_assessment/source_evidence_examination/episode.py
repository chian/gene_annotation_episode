"""Connect the predefined private A103 literature_page source investigation."""
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
from .to_child_table_evidence_extraction import TableEvidenceExtractionRequest
from .from_child_table_evidence_extraction import receive_table_evidence_extraction_report
from .to_child_source_coverage_improvement import SourceCoverageImprovementRequest
from .from_child_source_coverage_improvement import receive_source_coverage_improvement_report
from .to_child_passage_evidence_extraction import PassageEvidenceExtractionRequest
from .from_child_passage_evidence_extraction import receive_passage_evidence_extraction_report

from .action_policy import SourceActionPolicy
from .child_commissioning import SourceChildCommissioning

class LiteratureEpisode(SourceActionPolicy, SourceChildCommissioning,SourceEpisodeConfiguration, SourceEpisodeBindingRecord, SourceInvestigationGoal, SourceAssignment, SourceOperations, SourceInterpretation, SourceScientificRecords, SourceReferences, SourceInvestigationSummary, SourceInvestigationReport, SourceReceivedEvidence, SourceInvestigationCredit, SourceInvestigationYield, SourceInvestigationWaiting, TableEvidenceExtractionRequest, SourceCoverageImprovementRequest, PassageEvidenceExtractionRequest):
    decision_source_type = SourceInvestigationTask
    decision_prompt_renderer = staticmethod(render_receiver_prompt)
    binding_path = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    commissioning_parent = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    'C7 binding for C10 assignments; no model connection or private loop.'
    roles = ('literature_page',)
    entry_roles = ()

