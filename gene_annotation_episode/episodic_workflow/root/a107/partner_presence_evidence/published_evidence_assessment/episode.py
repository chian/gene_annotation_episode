"""A107 literature binding ``partner_presence_evidence/published_evidence_assessment``.

Its behaviour is the shared A107 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from . import literature_binding


class LiteratureEpisode(literature_binding.LiteratureBinding):
    binding_path = 'partner_presence_evidence/published_evidence_assessment'
    goal = 'Improve the published partner-requirement, omission/addback and coexpression evidence retained for the assigned question'
    unit = 'One literature action or commissioned search-strategy child'
    result = 'Retained literature findings and partner cells with their sources and limitations'
    child_slots = {'literature_strategy': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement'}
    commissioning_parent = 'partner_presence_evidence'
    acquisition = True
    instruction = ('Investigate which published evidence bears on the assigned scientific question. You can pursue '
                   'ordinary searches and source reads directly, or assign a strategy investigation when that '
                   'narrower question warrants iteration.')
