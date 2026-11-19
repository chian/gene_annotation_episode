"""The A108 passage evidence extraction binding (role ``literature_targeted``).

Its behaviour is the shared literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from .....literature_binding import LiteratureBinding


class PassageEvidenceExtractionEpisode(LiteratureBinding):
    """The evidence in supplied source-bound passages of one examined source."""
    binding_path = ('sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                    'source_relevance_assessment/source_evidence_examination/passage_evidence_extraction')
    commissioning_parent = ('sample_context_evidence/published_evidence_assessment/'
                            'evidence_search_strategy_improvement/source_relevance_assessment/'
                            'source_evidence_examination')
    role = 'literature_targeted'
    child_role_names = ()
    acquisition = False
    assignment_shape = ('reading', 'spans')
    instruction = ('Investigate the supplied source-bound passages for the assigned question. Read neighboring '
                   'context, qualifications or alternative passages as needed and revise the interpretation from '
                   'actual outcomes. Separate spans remain separate; never concatenate them into a fabricated '
                   'quotation.')
