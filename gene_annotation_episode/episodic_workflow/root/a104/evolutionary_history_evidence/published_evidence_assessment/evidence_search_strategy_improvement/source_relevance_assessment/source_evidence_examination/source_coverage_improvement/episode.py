"""The A104 ``evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement``
literature binding.

Its behaviour is the shared A104 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from .....literature_binding import LiteratureBinding


class SourceCoverageImprovementEpisode(LiteratureBinding):
    """Improve coverage of the examined source."""
    binding_path = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
    role = 'literature_ordered'
    commissioning_parent = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    acquisition = False
    instruction = ('Investigate the source in document order as useful for the assigned question. Use returned UTF-8 '
                   'byte continuations and retain representation identity. Decide whether to continue, reread, change '
                   'the examined window or interpret obtained evidence from actual outcomes.')
