"""The A108 source relevance assessment binding (role ``literature_search``).

Its behaviour is the shared literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ...literature_binding import LiteratureBinding


class SourceRelevanceAssessmentEpisode(LiteratureBinding):
    """Which returned sources merit examination for the commissioned A108 question."""
    binding_path = ('sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                    'source_relevance_assessment')
    commissioning_parent = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    role = 'literature_search'
    child_role_names = ('literature_page',)
    acquisition = True
    assignment_shape = ('question', 'search_assignment_v1', 'search_result_refs')
    instruction = ('Investigate which returned sources merit examination for the assigned question. Search results '
                   'are source-discovery information. Examine original sources and their conditions before asserting '
                   'biological evidence. A page child can investigate where and how to examine a selected source.')
