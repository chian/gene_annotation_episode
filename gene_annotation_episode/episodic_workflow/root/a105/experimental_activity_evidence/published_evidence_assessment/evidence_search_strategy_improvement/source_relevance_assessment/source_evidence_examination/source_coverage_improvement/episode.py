"""The A105 literature_ordered literature binding; its behaviour is the shared ``LiteratureBinding``."""
from __future__ import annotations

from .....literature_binding import LiteratureBinding


class SourceCoverageImprovementEpisode(LiteratureBinding):
    """The ordered-reading coverage of one examined source."""
    binding_path = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
    commissioning_parent = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
    role = 'literature_ordered'
    child_role_names = ()
    acquisition = False
    assignment_shape = ('reading', 'window')
    instruction = ('Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte '
                   'continuations and retain representation identity. Decide whether to continue, reread, change the '
                   'examined window or interpret obtained evidence from actual outcomes.')
