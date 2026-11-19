"""The A103 ``gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment`` literature binding.

Its behaviour is the shared A103 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from ...literature_binding import LiteratureBinding


class LiteratureEpisode(LiteratureBinding):
    binding_path = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    grain_name = 'gene_context_evidence__published_evidence_assessment__evidence_search_strategy_improvement__source_relevance_assessment'
    goal = 'Improve the set of sources judged relevant to the question'
    unit = 'One relevance judgement or child source examination'
    result = 'The sources judged relevant, with their judgements'
    child_slots = MappingProxyType({'source_evidence_examination': 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'})
    commissioning_parent = 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    acquisition = True
    instruction = ('Investigate which returned sources merit examination for the assigned question. Search results are '
                   'source-discovery information. Examine original sources and their conditions before asserting '
                   'biological evidence. A page child can investigate where and how to examine a selected source.')
