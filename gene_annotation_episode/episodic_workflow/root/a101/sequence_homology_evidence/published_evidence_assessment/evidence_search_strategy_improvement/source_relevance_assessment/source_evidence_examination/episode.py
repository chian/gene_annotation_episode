"""The A101 ``sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination`` literature binding.

Its behaviour is the shared A101 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from types import MappingProxyType

from ....literature_binding import LiteratureBinding


class SourceEvidenceExaminationEpisode(LiteratureBinding):
    """Improve the examination of a relevant source for applicable evidence."""
    binding_path = 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    goal = 'Improve the examination of a relevant source for applicable evidence'
    unit = 'One examination action or child'
    result = 'Source-grounded evidence findings from the examined source'
    child_slots = MappingProxyType({'passage_evidence_extraction': 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'table_evidence_extraction': 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction', 'source_coverage_improvement': 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'})
    commissioning_parent = 'sequence_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    acquisition = False
    instruction = ('Investigate where and how this exact source should be examined. Choose ordinary source operations '
                   'or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph '
                   'projections omit some XML headings, tables and footnotes; retained original bytes remain '
                   'addressable.')
