from __future__ import annotations

def credit_kind(self, role):
    self._role(role)
    return 'monitoring'

def credit_view(self, context, receiver_selection):
    self._role(context.role)
    return self.services.bound_role_credit(context, receiver_selection)
