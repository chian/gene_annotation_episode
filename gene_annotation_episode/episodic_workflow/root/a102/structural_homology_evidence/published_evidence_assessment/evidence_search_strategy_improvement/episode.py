"""The A102 ``structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement``
literature binding.

Its behaviour is the shared A102 literature implementation
(``published_evidence_assessment/literature_binding.py``); this binding declares only what is its own.
"""
from __future__ import annotations

from ..literature_binding import LiteratureBinding


class EvidenceSearchStrategyImprovementEpisode(LiteratureBinding):
    """Improve the search strategy that finds applicable published structural evidence."""
    binding_path = 'structural_homology_evidence/published_evidence_assessment/evidence_search_strategy_improvement'
    commissioning_parent = 'structural_homology_evidence/published_evidence_assessment'
    acquisition = True
    instruction = ('Investigate which search approach is productive. Keep the information objective and evidence '
                   'context separate from a literal provider query. Revise terms or source choices in light of actual '
                   'search/read outcomes; a relevance child can investigate which returned sources deserve examination.')
