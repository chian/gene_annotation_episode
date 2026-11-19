"""The A110 source_evidence_examination literature binding.

Its behaviour is the shared A110 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from ....literature_binding import LiteratureBinding


class SourceEvidenceExaminationEpisode(LiteratureBinding):
    """Examine one source for applicable evidence."""
    binding_path = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    grain_name = binding_path.replace('/', '__')
    goal = 'Examine one source for applicable evidence'
    unit = 'One source-examination action'
    result = 'The examined evidence with its subscoring sheet'
    child_slots = MappingProxyType({'passage_evidence_extraction': 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'source_coverage_improvement': 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement', 'table_evidence_extraction': 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'})
    commissioning_parent = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    acquisition = False
    instruction = 'Examine one assigned source for applicable chemical, reaction or resource evidence. Read its actual representation; commission table extraction, passage extraction or ordered coverage children for the parts of the source that need them.'
