"""The A104 ``evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement``
literature binding.

Its behaviour is the shared A104 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ..literature_binding import LiteratureBinding


class EvidenceSearchStrategyImprovementEpisode(LiteratureBinding):
    """Improve the evidence search strategy."""
    binding_path = 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    role = 'literature_strategy'
    commissioning_parent = 'evolutionary_history_evidence/published_evidence_assessment'
    acquisition = True
    instruction = ('Investigate which search approach is productive. Keep the information objective and evidence '
                   'context separate from a literal provider query. Revise terms or source choices in light of actual '
                   'search/read outcomes; a relevance child can investigate which returned sources deserve examination.')
