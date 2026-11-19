"""The A108 source coverage improvement binding (role ``literature_ordered``).

Its behaviour is the shared literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from .....literature_binding import LiteratureBinding


class SourceCoverageImprovementEpisode(LiteratureBinding):
    """The examined coverage of one source, read in document order."""
    binding_path = ('sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                    'source_relevance_assessment/source_evidence_examination/source_coverage_improvement')
    commissioning_parent = ('sample_context_evidence/published_evidence_assessment/'
                            'evidence_search_strategy_improvement/source_relevance_assessment/'
                            'source_evidence_examination')
    role = 'literature_ordered'
    child_role_names = ()
    acquisition = False
    assignment_shape = ('reading', 'window')
    instruction = ('Investigate the source in document order as useful for the assigned question. Use returned UTF-8 '
                   'byte continuations and retain representation identity. Decide whether to continue, reread, change '
                   'the examined window or interpret obtained evidence from actual outcomes.')
