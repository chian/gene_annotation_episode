"""The A104 ``evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction``
literature binding.

Its behaviour is the shared A104 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from .....literature_binding import LiteratureBinding


class TableEvidenceExtractionEpisode(LiteratureBinding):
    """Extract evidence from source tables."""
    binding_path = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
    role = 'literature_table'
    commissioning_parent = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    acquisition = False
    instruction = ('Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions '
                   'and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX '
                   'cells/formulas/caches keep their native identity. Article XML tables are read through exact '
                   'original-source windows.')
