"""The A106 literature binding of role ``literature_page``; its behaviour is the shared ``literature_binding``."""
from __future__ import annotations

from ....literature_binding import LiteratureBinding


class SourceEvidenceExaminationEpisode(LiteratureBinding):
    binding_path = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    commissioning_parent = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    role = 'literature_page'
    child_role_names = ('literature_table', 'literature_ordered', 'literature_targeted')
    assignment_shape = ('page',)
    instruction = ('Investigate where and how this exact source should be examined. Choose ordinary source operations or '
                   'selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections '
                   'omit some XML headings, tables and footnotes; retained original bytes remain addressable.')
