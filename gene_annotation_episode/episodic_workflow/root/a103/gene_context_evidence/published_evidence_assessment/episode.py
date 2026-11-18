"""Connect the predefined private A103 literature source investigation."""
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
from .source_contracts import ROLES, _CHILDREN, deepcopy
from .to_child_evidence_search_strategy_improvement import EvidenceSearchStrategyImprovementRequest
from .from_child_evidence_search_strategy_improvement import receive_evidence_search_strategy_improvement_report

from .action_policy import SourceActionPolicy
from .child_commissioning import SourceChildCommissioning

class LiteratureEpisode(SourceActionPolicy, SourceChildCommissioning,SourceEpisodeConfiguration, SourceEpisodeBindingRecord, SourceInvestigationGoal, SourceAssignment, SourceOperations, SourceInterpretation, SourceScientificRecords, SourceReferences, SourceInvestigationSummary, SourceInvestigationReport, SourceReceivedEvidence, SourceInvestigationCredit, SourceInvestigationYield, SourceInvestigationWaiting, EvidenceSearchStrategyImprovementRequest):
    decision_source_type = SourceInvestigationTask
    decision_prompt_renderer = staticmethod(render_receiver_prompt)
    binding_path = 'gene_context_evidence/published_evidence_assessment'
    commissioning_parent = 'gene_context_evidence'
    'C7 binding for C10 assignments; no model connection or private loop.'
    roles = ('literature',)
    entry_roles = ('literature',)

def create_binding_tree(services, **configuration):
    """Assemble the original caller configuration as seven private bindings."""
    from copy import deepcopy
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.episode import LiteratureEpisode as Child1
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode import LiteratureEpisode as Child2
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode import LiteratureEpisode as Child3
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode import LiteratureEpisode as Child4
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode import LiteratureEpisode as Child5
    from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode import LiteratureEpisode as Child6
    return tuple((binding(services, **deepcopy(configuration)) for binding in (LiteratureEpisode, Child1, Child2, Child3, Child4, Child5, Child6)))
