"""The A105 literature_targeted literature binding; its behaviour is the shared ``LiteratureBinding``."""
from __future__ import annotations

from .....literature_binding import LiteratureBinding


class PassageEvidenceExtractionEpisode(LiteratureBinding):
    """The passage evidence of one examined source."""
    binding_path = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
    commissioning_parent = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    role = 'literature_targeted'
    child_role_names = ()
    acquisition = False
    assignment_shape = ('reading', 'spans')
    instruction = ('Investigate the supplied source-bound passages for the assigned question. Read neighboring context, '
                   'qualifications or alternative passages as needed and revise the interpretation from actual '
                   'outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.')
