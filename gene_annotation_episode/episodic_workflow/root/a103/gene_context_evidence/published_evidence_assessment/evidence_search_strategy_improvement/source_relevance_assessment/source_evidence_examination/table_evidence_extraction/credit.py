"""Private A103 literature_table credit."""
from __future__ import annotations

class SourceInvestigationCredit:

    def credit_kind(self, role):
        self._role(role)
        return 'scientific'

    def credit_view(self, context, receiver_selection):
        self._role('literature_table')
        return self.services.scientific_credit(context, receiver_selection)

    def credit_projector(self, context):
        self._role('literature_table')
        return None
