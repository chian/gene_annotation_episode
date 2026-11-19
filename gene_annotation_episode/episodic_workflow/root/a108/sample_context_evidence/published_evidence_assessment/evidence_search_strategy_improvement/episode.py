"""The A108 evidence-search strategy improvement binding (role ``literature_strategy``).

Its behaviour is the shared literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ..literature_binding import LiteratureBinding


class EvidenceSearchStrategyImprovementEpisode(LiteratureBinding):
    """Which search approach is productive for the commissioned A108 question."""
    binding_path = 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    commissioning_parent = 'sample_context_evidence/published_evidence_assessment'
    role = 'literature_strategy'
    child_role_names = ('literature_search',)
    acquisition = True
    assignment_shape = ('question', 'strategy_assignment_v1', 'prior_search_refs')
    instruction = ('Investigate which search approach is productive. Keep the information objective and evidence '
                   'context separate from a literal provider query. Revise terms or source choices in light of '
                   'actual search/read outcomes; a search child can investigate which returned sources deserve '
                   'examination.')
