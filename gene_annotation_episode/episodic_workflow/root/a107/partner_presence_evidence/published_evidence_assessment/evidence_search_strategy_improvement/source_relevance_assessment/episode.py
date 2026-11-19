"""A107 literature binding ``partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment``.

Its behaviour is the shared A107 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ... import literature_binding


class LiteratureEpisode(literature_binding.LiteratureBinding):
    binding_path = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    goal = 'Improve the assessment of which located sources are relevant to the assigned question'
    unit = 'One relevance action or commissioned source-examination child'
    result = 'Relevance findings for the located sources'
    child_slots = {'literature_page': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'}
    commissioning_parent = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    acquisition = True
    instruction = ('Investigate which returned sources merit examination for the assigned question. Search results are '
                   'source-discovery information. Examine original sources and their conditions before asserting '
                   'biological evidence. A page child can investigate where and how to examine a selected source.')
