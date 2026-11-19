"""The A102 ``structural_homology_evidence/published_evidence_assessment``
literature binding.

Its behaviour is the shared A102 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from .literature_binding import LiteratureBinding


class PublishedEvidenceAssessmentEpisode(LiteratureBinding):
    """Improve the published structural evidence received for the assigned question."""
    binding_path = 'structural_homology_evidence/published_evidence_assessment'
    commissioning_parent = 'structural_homology_evidence'
    acquisition = True
    instruction = ('Investigate which published evidence bears on the assigned structural question. You can pursue '
                   'ordinary searches and source reads directly, or assign a strategy investigation when that '
                   'narrower question warrants iteration.')
