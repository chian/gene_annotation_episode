"""Private A102 API credit."""
from __future__ import annotations
from .execution_contracts import math, plain

class APICredit:

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_execution_episode_role')
        return 'operational'

    def project_credit(self, context, receiver_selection):
        closed = self._closed_operational_credit_view(context, receiver_selection)
        return self._live_project_credit(context, receiver_selection) if closed is None else closed

    def _live_project_credit(self, context, receiver_selection):
        if self.native_protein_structure_results.applies(context):
            return self.native_protein_structure_results.credit_view(context, receiver_selection)
        return self.api_execution.credit_view(context, receiver_selection)

    def credit_view(self, context, receiver_selection):
        return self.project_credit(context, receiver_selection)
