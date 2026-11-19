"""The A103 ``gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination`` literature binding.

Its behaviour is the shared A103 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from ....literature_binding import LiteratureBinding


class LiteratureEpisode(LiteratureBinding):
    binding_path = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    grain_name = 'gene_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment__source_evidence_examination'
    goal = 'Improve the evidence extracted from one examined source'
    unit = 'One examination action or child extraction'
    result = 'The evidence extracted from the source'
    child_slots = MappingProxyType({'passage_evidence_extraction': 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'source_coverage_improvement': 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement', 'table_evidence_extraction': 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'})
    commissioning_parent = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    acquisition = False
    instruction = ('Investigate where and how this exact source should be examined. Choose ordinary source operations '
                   'or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph '
                   'projections omit some XML headings, tables and footnotes; retained original bytes remain '
                   'addressable.')
