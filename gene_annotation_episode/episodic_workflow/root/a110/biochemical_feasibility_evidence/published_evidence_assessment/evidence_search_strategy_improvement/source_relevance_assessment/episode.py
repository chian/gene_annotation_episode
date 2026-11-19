"""The A110 source_relevance_assessment literature binding.

Its behaviour is the shared A110 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from ...literature_binding import LiteratureBinding


class SourceRelevanceAssessmentEpisode(LiteratureBinding):
    """Assess the relevance of found sources."""
    binding_path = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    grain_name = binding_path.replace('/', '__')
    goal = 'Assess the relevance of found sources'
    unit = 'One source-relevance assessment'
    result = 'The relevant sources and their assessments'
    child_slots = MappingProxyType({'source_evidence_examination': 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'})
    commissioning_parent = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    acquisition = True
    instruction = 'Assess which found sources bear on the commissioned A110 question by reading their actual content, not their metadata. Commission a source-examination child for a source that deserves examination.'
