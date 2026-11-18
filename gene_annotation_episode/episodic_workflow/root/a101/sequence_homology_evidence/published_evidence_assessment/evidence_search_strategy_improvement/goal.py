"""Private A101 literature_strategy goal."""
from __future__ import annotations
from .source_contracts import _ROLE_INSTRUCTIONS

class LiteratureGoal:

    def instructions(self, context):
        self._role(context.role)
        return 'For A101, identify the actual sequence or region and its aligned homolog before using a source claim. Keep alignment coverage, residue or domain correspondence, characterized homolog measurements, database labels, and their applicability to the target distinct and source-grounded.\n\n' + _ROLE_INSTRUCTIONS['literature_strategy']
