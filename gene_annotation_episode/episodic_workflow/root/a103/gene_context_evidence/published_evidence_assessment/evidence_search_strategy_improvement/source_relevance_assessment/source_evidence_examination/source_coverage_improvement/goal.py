"""Private A103 literature_ordered goal."""
from __future__ import annotations
from .source_contracts import _ROLE_INSTRUCTIONS

class SourceInvestigationGoal:

    def instructions(self, context):
        self._role('literature_ordered')
        return 'For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene identity, order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their source and scope.\n\n' + _ROLE_INSTRUCTIONS['literature_ordered']
