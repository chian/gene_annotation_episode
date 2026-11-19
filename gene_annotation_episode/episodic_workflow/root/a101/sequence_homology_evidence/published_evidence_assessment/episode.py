"""The A101 ``sequence_homology_evidence/published_evidence_assessment`` literature binding.

Its behaviour is the shared A101 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from .literature_binding import LiteratureBinding


class PublishedEvidenceAssessmentEpisode(LiteratureBinding):
    """Improve the published evidence bearing on the sequence-homology question."""
    binding_path = 'sequence_homology_evidence/published_evidence_assessment'
    goal = 'Improve the published evidence bearing on the sequence-homology question'
    unit = 'One literature action or child'
    result = 'Graded published-evidence findings with source references'
    child_slots = MappingProxyType({'evidence_search_strategy_improvement': 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement'})
    commissioning_parent = 'sequence_homology_evidence'
    acquisition = True
    instruction = ('Investigate which published evidence bears on the assigned scientific question. You can pursue '
                   'ordinary searches and source reads directly, or assign a strategy investigation when that '
                   'narrower question warrants iteration.')
