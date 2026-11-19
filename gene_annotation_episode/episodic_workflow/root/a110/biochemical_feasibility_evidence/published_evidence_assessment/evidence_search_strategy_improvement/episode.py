"""The A110 evidence_search_strategy_improvement literature binding.

Its behaviour is the shared A110 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from ..literature_binding import LiteratureBinding


class EvidenceSearchStrategyImprovementEpisode(LiteratureBinding):
    """Improve the search strategy for applicable published evidence."""
    binding_path = 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    grain_name = binding_path.replace('/', '__')
    goal = 'Improve the search strategy for applicable published evidence'
    unit = 'One search-strategy action'
    result = 'The improved search strategy and its findings'
    child_slots = MappingProxyType({'source_relevance_assessment': 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'})
    commissioning_parent = 'biochemical_feasibility_evidence/published_evidence_assessment'
    acquisition = True
    instruction = 'Investigate which search approach is productive for the commissioned A110 question. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search and read outcomes; a source-relevance child can assess which returned sources deserve examination.'
