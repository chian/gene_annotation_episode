"""The A103 ``gene_context_evidence/published_evidence_assessment`` literature binding.

Its behaviour is the shared A103 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from .literature_binding import LiteratureBinding


class LiteratureEpisode(LiteratureBinding):
    binding_path = 'gene_context_evidence/published_evidence_assessment'
    grain_name = 'gene_context_evidence__published_evidence_assessment'
    goal = 'Improve the published literature evidence bearing on the parent gene-context question'
    unit = 'One literature action or child literature commission'
    result = 'Assessed literature findings with their record references'
    child_slots = MappingProxyType({'evidence_search_strategy_improvement': 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'})
    commissioning_parent = 'gene_context_evidence'
    acquisition = True
    instruction = ('Investigate which published evidence bears on the assigned scientific question. You can pursue '
                   'ordinary searches and source reads directly, or assign a strategy investigation when that '
                   'narrower question warrants iteration.')
