"""The A102 ``structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination``
literature binding.

Its behaviour is the shared A102 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ....literature_binding import LiteratureBinding


class SourceEvidenceExaminationEpisode(LiteratureBinding):
    """Improve the examination of one source for applicable structural evidence."""
    binding_path = 'structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    commissioning_parent = 'structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    acquisition = False
    instruction = ('Investigate where and how this exact source should be examined. Choose ordinary source operations '
                   'or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph '
                   'projections omit some XML headings, tables and footnotes; retained original bytes remain '
                   'addressable.')
