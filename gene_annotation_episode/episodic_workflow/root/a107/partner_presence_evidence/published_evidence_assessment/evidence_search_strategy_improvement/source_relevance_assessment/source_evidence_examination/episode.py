"""A107 literature binding ``partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination``.

Its behaviour is the shared A107 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from .... import literature_binding


class LiteratureEpisode(literature_binding.LiteratureBinding):
    binding_path = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    goal = 'Improve the evidence examined from one relevant source'
    unit = 'One source-reading action or commissioned table, coverage or passage child'
    result = 'Source-grounded findings and graded cells from that source'
    child_slots = {'literature_targeted': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'literature_ordered': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement', 'literature_table': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'}
    commissioning_parent = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    acquisition = False
    instruction = ('Investigate where and how this exact source should be examined. Choose ordinary source operations '
                   'or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph '
                   'projections omit some XML headings, tables and footnotes; retained original bytes remain '
                   'addressable.')
