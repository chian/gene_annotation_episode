"""The A106 literature binding of role ``literature_strategy``; its behaviour is the shared ``literature_binding``."""
from __future__ import annotations

from ..literature_binding import LiteratureBinding


class EvidenceSearchStrategyImprovementEpisode(LiteratureBinding):
    binding_path = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    commissioning_parent = 'perturbation_evidence/published_evidence_assessment'
    role = 'literature_strategy'
    child_role_names = ('literature_search',)
    assignment_shape = ('question', 'strategy_assignment_v1', 'prior_search_refs')
    instruction = ('Investigate which search approach is productive. Keep the information objective and evidence '
                   'context separate from a literal provider query. Revise terms or source choices in light of actual '
                   'search/read outcomes; a search child can investigate which returned sources deserve examination.')
