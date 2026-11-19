"""A107 literature binding ``partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction``.

Its behaviour is the shared A107 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ..... import literature_binding


class LiteratureEpisode(literature_binding.LiteratureBinding):
    binding_path = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
    goal = 'Improve the evidence extracted from the tables of one source'
    unit = 'One table-reading or extraction action'
    result = 'Table-derived findings and cells with their anchors'
    child_slots = {}
    commissioning_parent = 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    acquisition = False
    instruction = ('Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions '
                   'and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX '
                   'cells/formulas/caches keep their native identity. Article XML tables are read through exact '
                   'original-source windows.')
