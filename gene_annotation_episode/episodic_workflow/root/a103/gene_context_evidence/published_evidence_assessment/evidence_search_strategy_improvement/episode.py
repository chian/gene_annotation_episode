"""The A103 ``gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement`` literature binding.

Its behaviour is the shared A103 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from ..literature_binding import LiteratureBinding


class LiteratureEpisode(LiteratureBinding):
    binding_path = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    grain_name = 'gene_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement'
    goal = 'Improve the literature search strategy so that relevant sources are found'
    unit = 'One search-strategy action or child commission'
    result = 'The improved search strategy and the sources it found'
    child_slots = MappingProxyType({'source_relevance_assessment': 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'})
    commissioning_parent = 'gene_context_evidence/published_evidence_assessment'
    acquisition = True
    instruction = ('Investigate which search approach is productive. Keep the information objective and evidence '
                   'context separate from a literal provider query. Revise terms or source choices in light of actual '
                   'search/read outcomes; a search child can investigate which returned sources deserve examination.')
