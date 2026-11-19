"""A107 literature binding ``partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement``.

Its behaviour is the shared A107 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ..... import literature_binding


class LiteratureEpisode(literature_binding.LiteratureBinding):
    binding_path = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
    goal = 'Improve the coverage of one source examined in reading order'
    unit = 'One ordered reading action'
    result = 'Findings from the newly covered portions of the source'
    child_slots = {}
    commissioning_parent = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    acquisition = False
    instruction = ('Investigate the source in document order as useful for the assigned question. Use returned UTF-8 '
                   'byte continuations and retain representation identity. Decide whether to continue, reread, change '
                   'the examined window or interpret obtained evidence from actual outcomes.')
