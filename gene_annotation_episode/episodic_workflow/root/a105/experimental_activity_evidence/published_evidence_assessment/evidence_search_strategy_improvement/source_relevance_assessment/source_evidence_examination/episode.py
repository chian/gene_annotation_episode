"""The A105 literature_page literature binding; its behaviour is the shared ``LiteratureBinding``."""
from __future__ import annotations

from ....literature_binding import LiteratureBinding


class SourceEvidenceExaminationEpisode(LiteratureBinding):
    """Where and how one exact source should be examined for the A105 question."""
    binding_path = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    commissioning_parent = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    role = 'literature_page'
    child_role_names = ('literature_table', 'literature_ordered', 'literature_targeted')
    acquisition = True
    assignment_shape = ('page',)
    instruction = ('Investigate where and how this exact source should be examined. Choose ordinary source operations or '
                   'selected table, ordered-reading or targeted-passage investigations as useful. Paragraph '
                   'projections omit some XML headings, tables and footnotes; retained original bytes remain '
                   'addressable.')
