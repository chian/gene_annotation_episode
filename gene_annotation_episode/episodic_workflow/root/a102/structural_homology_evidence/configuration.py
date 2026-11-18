"""Private A102 scientific configuration."""
from __future__ import annotations
from .scientific_contracts import ROLE

class ScientificConfiguration:

    def contract_information_profile(self, context):
        """Expose frozen contract information to scientific commissioning parents."""
        return self._contract_information_profile if context.role in ('annotation', ROLE) else None
