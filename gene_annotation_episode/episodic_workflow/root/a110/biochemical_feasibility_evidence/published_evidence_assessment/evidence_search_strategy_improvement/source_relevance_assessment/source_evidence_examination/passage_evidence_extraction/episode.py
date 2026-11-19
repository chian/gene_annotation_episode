"""The A110 passage_evidence_extraction literature binding.

Its behaviour is the shared A110 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from .....literature_binding import LiteratureBinding


class PassageEvidenceExtractionEpisode(LiteratureBinding):
    """Extract applicable evidence from targeted passages."""
    binding_path = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
    grain_name = binding_path.replace('/', '__')
    goal = 'Extract applicable evidence from targeted passages'
    unit = 'One passage-extraction action'
    result = 'The extracted passage evidence'
    child_slots = MappingProxyType({})
    commissioning_parent = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    acquisition = False
    instruction = 'Extract the applicable evidence from the assigned source passages: locate and read the exact passages and commit what they establish, with their species, quantities, units and conditions.'
