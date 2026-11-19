"""The A104 ``evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction``
literature binding.

Its behaviour is the shared A104 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from .....literature_binding import LiteratureBinding


class PassageEvidenceExtractionEpisode(LiteratureBinding):
    """Extract evidence from targeted source passages."""
    binding_path = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
    role = 'literature_targeted'
    commissioning_parent = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    acquisition = False
    instruction = ('Investigate the supplied source-bound passages for the assigned question. Read neighboring context, '
                   'qualifications or alternative passages as needed and revise the interpretation from actual '
                   'outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.')
