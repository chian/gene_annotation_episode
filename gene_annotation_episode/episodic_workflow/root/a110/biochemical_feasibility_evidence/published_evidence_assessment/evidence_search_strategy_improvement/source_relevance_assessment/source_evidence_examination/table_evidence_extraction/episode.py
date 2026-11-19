"""The A110 table_evidence_extraction literature binding.

Its behaviour is the shared A110 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from .....literature_binding import LiteratureBinding


class TableEvidenceExtractionEpisode(LiteratureBinding):
    """Extract applicable evidence from source tables."""
    binding_path = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
    grain_name = binding_path.replace('/', '__')
    goal = 'Extract applicable evidence from source tables'
    unit = 'One table-extraction action'
    result = 'The extracted table evidence'
    child_slots = MappingProxyType({})
    commissioning_parent = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    acquisition = False
    instruction = 'Extract the applicable evidence from the assigned source tables: read the actual rows, keep their native units, conditions and identities, and commit what they establish.'
