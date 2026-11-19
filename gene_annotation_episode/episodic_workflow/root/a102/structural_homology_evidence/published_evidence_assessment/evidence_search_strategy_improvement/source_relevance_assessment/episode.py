"""The A102 ``structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment``
literature binding.

Its behaviour is the shared A102 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ...literature_binding import LiteratureBinding


class SourceRelevanceAssessmentEpisode(LiteratureBinding):
    """Improve the relevance assessment of candidate sources."""
    binding_path = 'structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    commissioning_parent = 'structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    acquisition = True
    instruction = ('Investigate which returned sources merit examination for the assigned question. Search results are '
                   'source-discovery information. Examine original sources and their conditions before asserting '
                   'structural evidence. An examination child can investigate where and how to examine a selected source.')
