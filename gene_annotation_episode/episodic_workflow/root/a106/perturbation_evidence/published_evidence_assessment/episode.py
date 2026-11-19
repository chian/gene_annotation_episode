"""The A106 literature binding of role ``literature``; its behaviour is the shared ``literature_binding``."""
from __future__ import annotations

from .literature_binding import LiteratureBinding


class PublishedEvidenceAssessmentEpisode(LiteratureBinding):
    binding_path = 'perturbation_evidence/published_evidence_assessment'
    commissioning_parent = 'perturbation_evidence'
    role = 'literature'
    child_role_names = ('literature_strategy',)
    assignment_shape = ('question', 'literature_assignment_v1', 'source_refs')
    instruction = ('Investigate which published evidence bears on the assigned scientific question. You can pursue '
                   'ordinary searches and source reads directly, or assign a strategy investigation when that '
                   'narrower question warrants iteration.')
