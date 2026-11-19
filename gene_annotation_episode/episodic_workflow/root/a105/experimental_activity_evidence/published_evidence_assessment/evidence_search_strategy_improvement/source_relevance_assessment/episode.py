"""The A105 literature_search literature binding; its behaviour is the shared ``LiteratureBinding``."""
from __future__ import annotations

from ...literature_binding import LiteratureBinding


class SourceRelevanceAssessmentEpisode(LiteratureBinding):
    """Which returned sources merit examination for the A105 question."""
    binding_path = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment'
    commissioning_parent = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    role = 'literature_search'
    child_role_names = ('literature_page',)
    acquisition = True
    assignment_shape = ('question', 'search_assignment_v1', 'search_result_refs')
    instruction = ('Investigate which returned sources merit examination for the assigned question. Search results are '
                   'source-discovery information. Examine original sources and their conditions before asserting '
                   'biological evidence. A page child can investigate where and how to examine a selected source.')
