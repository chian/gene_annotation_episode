"""The A110 published_evidence_assessment literature binding.

Its behaviour is the shared A110 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from .literature_binding import LiteratureBinding


class PublishedEvidenceAssessmentEpisode(LiteratureBinding):
    """Improve the published evidence on the biochemical-feasibility question."""
    binding_path = 'biochemical_feasibility_evidence/published_evidence_assessment'
    grain_name = binding_path.replace('/', '__')
    goal = 'Improve the published evidence on the biochemical-feasibility question'
    unit = 'One literature action or commissioned search'
    result = 'The graded literature findings'
    child_slots = MappingProxyType({'evidence_search_strategy_improvement': 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement'})
    commissioning_parent = 'biochemical_feasibility_evidence'
    acquisition = True
    instruction = 'Answer the commissioned A110 literature question. Find and examine published evidence about the reaction, pathway, stoichiometry, cofactors, carriers, resources or energetics the question names. Commission a search-strategy child when the search approach itself needs improvement.'
