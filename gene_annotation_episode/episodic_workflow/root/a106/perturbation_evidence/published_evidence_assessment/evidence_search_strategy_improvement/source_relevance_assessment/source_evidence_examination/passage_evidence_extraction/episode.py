"""The A106 literature binding of role ``literature_targeted``; its behaviour is the shared ``literature_binding``."""
from __future__ import annotations

from .....literature_binding import LiteratureBinding


class PassageEvidenceExtractionEpisode(LiteratureBinding):
    binding_path = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
    commissioning_parent = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    role = 'literature_targeted'
    child_role_names = ()
    assignment_shape = ('reading', 'spans')
    instruction = ('Investigate the supplied source-bound passages for the assigned question. Read neighboring context, '
                   'qualifications or alternative passages as needed and revise the interpretation from actual '
                   'outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.')
