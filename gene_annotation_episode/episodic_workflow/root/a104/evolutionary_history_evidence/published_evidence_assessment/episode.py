"""The A104 ``evolutionary_history_evidence/published_evidence_assessment``
literature binding.

Its behaviour is the shared A104 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from .literature_binding import LiteratureBinding


class PublishedEvidenceAssessmentEpisode(LiteratureBinding):
    """Assess the published evidence bearing on the parent's evolutionary-history question."""
    binding_path = 'evolutionary_history_evidence/published_evidence_assessment'
    role = 'literature'
    commissioning_parent = 'evolutionary_history_evidence'
    acquisition = True
    instruction = ('Investigate which published evidence bears on the assigned evolutionary-history question. You can '
                   'pursue ordinary searches and source reads directly, or assign a strategy investigation when that '
                   'narrower question warrants iteration.')
