"""The A104 ``evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination``
literature binding.

Its behaviour is the shared A104 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ....literature_binding import LiteratureBinding


class SourceEvidenceExaminationEpisode(LiteratureBinding):
    """Examine one source for applicable evolutionary-history evidence."""
    binding_path = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    role = 'literature_page'
    commissioning_parent = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    acquisition = False
    instruction = ('Investigate where and how this exact source should be examined. Choose ordinary source operations '
                   'or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph '
                   'projections omit some XML headings, tables and footnotes; retained original bytes remain '
                   'addressable.')
