"""A107 literature binding ``partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement``.

Its behaviour is the shared A107 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from .. import literature_binding


class LiteratureEpisode(literature_binding.LiteratureBinding):
    binding_path = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    goal = 'Improve the search strategy that locates published sources bearing on the assigned partner question'
    unit = 'One search action or commissioned relevance-assessment child'
    result = 'Located sources and the strategy findings that selected them'
    child_slots = {'literature_search': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'}
    commissioning_parent = 'partner_presence_evidence/published_evidence_assessment'
    acquisition = True
    instruction = ('Investigate which search approach is productive. Keep the information objective and evidence '
                   'context separate from a literal provider query. Revise terms or source choices in light of actual '
                   'search/read outcomes; a search child can investigate which returned sources deserve examination.')
