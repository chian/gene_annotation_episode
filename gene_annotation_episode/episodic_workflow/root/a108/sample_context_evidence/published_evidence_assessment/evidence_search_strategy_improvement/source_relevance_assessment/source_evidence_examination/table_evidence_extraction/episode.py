"""The A108 table evidence extraction binding (role ``literature_table``).

Its behaviour is the shared literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from .....literature_binding import LiteratureBinding


class TableEvidenceExtractionEpisode(LiteratureBinding):
    """The scientific meaning of one selected table or sheet of an examined source."""
    binding_path = ('sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/'
                    'source_relevance_assessment/source_evidence_examination/table_evidence_extraction')
    commissioning_parent = ('sample_context_evidence/published_evidence_assessment/'
                            'evidence_search_strategy_improvement/source_relevance_assessment/'
                            'source_evidence_examination')
    role = 'literature_table'
    child_role_names = ()
    acquisition = False
    assignment_shape = ('reading', 'table')
    instruction = ('Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions '
                   'and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX '
                   'cells/formulas/caches keep their native identity. Article XML tables are read through exact '
                   'original-source windows.')
