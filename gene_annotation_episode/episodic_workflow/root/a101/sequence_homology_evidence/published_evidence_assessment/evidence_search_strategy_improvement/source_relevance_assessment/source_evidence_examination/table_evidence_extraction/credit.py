"""Private literature_table credit behavior for A101."""
from __future__ import annotations

class LiteratureCredit:
    def credit_kind(self, role):
        self._role(role)
        return "scientific"

    def credit_view(self, context, receiver_selection):
        self._role(context.role)
        return self.services.scientific_credit(context, receiver_selection)

    def credit_projector(self, context):
        self._role(context.role)
        return None
