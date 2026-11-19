"""The A104 ``evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment``
literature binding.

Its behaviour is the shared A104 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ...literature_binding import LiteratureBinding


class SourceRelevanceAssessmentEpisode(LiteratureBinding):
    """Assess the relevance of returned sources."""
    binding_path = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    role = 'literature_search'
    commissioning_parent = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    acquisition = True
    instruction = ('Investigate which returned sources merit examination for the assigned question. Search results are '
                   'source-discovery information. Examine original sources and their conditions before asserting '
                   'evolutionary evidence. An examination child can investigate where and how to examine a selected source.')
