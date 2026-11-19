"""The A110 source_coverage_improvement literature binding.

Its behaviour is the shared A110 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from .....literature_binding import LiteratureBinding


class SourceCoverageImprovementEpisode(LiteratureBinding):
    """Improve coverage of the examined source in order."""
    binding_path = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
    grain_name = binding_path.replace('/', '__')
    goal = 'Improve coverage of the examined source in order'
    unit = 'One ordered-reading action'
    result = 'The added source coverage and its evidence'
    child_slots = MappingProxyType({})
    commissioning_parent = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    acquisition = False
    instruction = 'Improve the coverage of the assigned source by reading it in order from where the examined spans end; commit the applicable evidence the newly read spans contain.'
