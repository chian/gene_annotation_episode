"""The A101 ``sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment`` literature binding.

Its behaviour is the shared A101 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from ...literature_binding import LiteratureBinding


class SourceRelevanceAssessmentEpisode(LiteratureBinding):
    """Improve the assessment of which found sources are relevant."""
    binding_path = 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    goal = 'Improve the assessment of which found sources are relevant'
    unit = 'One relevance action or child'
    result = 'Relevance assessments of the found sources'
    child_slots = MappingProxyType({'source_evidence_examination': 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'})
    commissioning_parent = 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    acquisition = True
    instruction = ('Investigate which returned sources merit examination for the assigned question. Search results are '
                   'source-discovery information. Examine original sources and their conditions before asserting '
                   'biological evidence. A page child can investigate where and how to examine a selected source.')
