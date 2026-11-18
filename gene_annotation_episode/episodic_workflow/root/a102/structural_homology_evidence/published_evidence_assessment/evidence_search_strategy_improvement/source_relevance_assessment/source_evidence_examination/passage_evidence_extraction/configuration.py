"""Private A102 literature_targeted configuration."""
from __future__ import annotations
from .source_contracts import ROLES

class SourceConfiguration:

    def contract_information_configuration(self):
        return self._contract_information_profile

    def contract_information_profile(self, context):
        if context.role in ROLES or (context.role == 'annotation' and len(context.path) == 1 and (self.reference_parent_sources is not None)):
            return self._contract_information_profile
        return None
