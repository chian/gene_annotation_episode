"""A107 literature binding ``partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction``.

Its behaviour is the shared A107 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ..... import literature_binding


class LiteratureEpisode(literature_binding.LiteratureBinding):
    binding_path = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
    goal = 'Improve the evidence extracted from targeted passages of one source'
    unit = 'One targeted passage action'
    result = 'Passage-anchored findings and cells'
    child_slots = {}
    commissioning_parent = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    acquisition = False
    instruction = ('Investigate the supplied source-bound passages for the assigned question. Read neighboring context, '
                   'qualifications or alternative passages as needed and revise the interpretation from actual '
                   'outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.')
