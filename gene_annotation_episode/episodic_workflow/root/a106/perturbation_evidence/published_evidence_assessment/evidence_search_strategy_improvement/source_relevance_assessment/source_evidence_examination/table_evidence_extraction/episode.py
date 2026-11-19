"""The A106 literature binding of role ``literature_table``; its behaviour is the shared ``literature_binding``."""
from __future__ import annotations

from .....literature_binding import LiteratureBinding


class TableEvidenceExtractionEpisode(LiteratureBinding):
    binding_path = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
    commissioning_parent = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    role = 'literature_table'
    child_role_names = ()
    assignment_shape = ('reading', 'table')
    instruction = ('Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and '
                   'footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX '
                   'cells/formulas/caches keep their native identity. Article XML tables are read through exact '
                   'original-source windows.')
