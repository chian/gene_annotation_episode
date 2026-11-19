"""The A108 published-evidence assessment binding (role ``literature``) and the literature home factory.

Its behaviour is the shared literature implementation (``literature_binding``,
``literature_source``, ``literature_credit``); this binding declares only what
is its own.
"""
from __future__ import annotations

from copy import deepcopy

from .literature_binding import LiteratureBinding


class PublishedEvidenceAssessmentEpisode(LiteratureBinding):
    """Which published evidence bears on the commissioned A108 question."""
    binding_path = 'sample_context_evidence/published_evidence_assessment'
    commissioning_parent = 'sample_context_evidence'
    role = 'literature'
    child_role_names = ('literature_strategy',)
    acquisition = True
    assignment_shape = ('question', 'literature_assignment_v1', 'source_refs')
    instruction = ('Investigate which published evidence bears on the assigned scientific question. You can pursue '
                   'ordinary searches and source reads directly, or assign a strategy investigation when that '
                   'narrower question warrants iteration.')


def create_binding_tree(*, store, tools, yield_bindings, outcome_page_size):
    """Construct the seven A108 literature bindings, each with its own tool registry over the run's store.

    ``tools`` are the A108 ``ToolRegistry`` settings; ``yield_bindings`` declares each binding's continuation per
    commissioned task kind; ``outcome_page_size`` bounds the own-outcome page presented with each decision.
    """
    from gene_annotation_episode.episodic_workflow.episode_support.tools.sample_context_evidence.tools import ToolRegistry
    from .evidence_search_strategy_improvement.episode import EvidenceSearchStrategyImprovementEpisode
    from .evidence_search_strategy_improvement.source_relevance_assessment.episode import (
        SourceRelevanceAssessmentEpisode)
    from .evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode import (
        SourceEvidenceExaminationEpisode)
    from .evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.\
        passage_evidence_extraction.episode import PassageEvidenceExtractionEpisode
    from .evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.\
        source_coverage_improvement.episode import SourceCoverageImprovementEpisode
    from .evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.\
        table_evidence_extraction.episode import TableEvidenceExtractionEpisode
    bindings = tuple(binding(tool_registry=ToolRegistry(store, **deepcopy(dict(tools))),
                             yield_bindings=deepcopy(yield_bindings), outcome_page_size=outcome_page_size)
                     for binding in (PublishedEvidenceAssessmentEpisode, EvidenceSearchStrategyImprovementEpisode,
                                     SourceRelevanceAssessmentEpisode, SourceEvidenceExaminationEpisode,
                                     TableEvidenceExtractionEpisode, SourceCoverageImprovementEpisode,
                                     PassageEvidenceExtractionEpisode))
    by_role = {binding.role: binding for binding in bindings}
    for binding in bindings:
        binding.bind_children({role: by_role[role] for role in binding.child_role_names})
    return bindings
