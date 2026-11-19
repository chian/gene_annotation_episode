"""The A105 literature_strategy literature binding; its behaviour is the shared ``LiteratureBinding``."""
from __future__ import annotations

from ..literature_binding import LiteratureBinding


class EvidenceSearchStrategyImprovementEpisode(LiteratureBinding):
    """Which search approach finds the published experimental evidence for the A105 question."""
    binding_path = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    commissioning_parent = 'experimental_activity_evidence/published_evidence_assessment'
    role = 'literature_strategy'
    child_role_names = ('literature_search',)
    acquisition = True
    assignment_shape = ('question', 'strategy_assignment_v1', 'prior_search_refs')
    instruction = ('Investigate which search approach is productive. Keep the information objective and evidence context '
                   'separate from a literal provider query. Revise terms or source choices in light of actual '
                   'search/read outcomes; a search child can investigate which returned sources deserve examination.')
