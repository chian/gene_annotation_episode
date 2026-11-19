"""The A101 ``sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement`` literature binding.

Its behaviour is the shared A101 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from ..literature_binding import LiteratureBinding


class EvidenceSearchStrategyImprovementEpisode(LiteratureBinding):
    """Improve the search strategy that finds relevant published sources."""
    binding_path = 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    goal = 'Improve the search strategy that finds relevant published sources'
    unit = 'One search action or child'
    result = 'Relevant source candidates with their search records'
    child_slots = MappingProxyType({'source_relevance_assessment': 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'})
    commissioning_parent = 'sequence_homology_evidence/published_evidence_assessment'
    acquisition = True
    instruction = ('Investigate which search approach is productive. Keep the information objective and evidence '
                   'context separate from a literal provider query. Revise terms or source choices in light of actual '
                   'search/read outcomes; a search child can investigate which returned sources deserve examination.')
