"""Private A102 resource credit."""
from __future__ import annotations
from .resource_contracts import ROLES

class ResourceCredit:

    def credit_kind(self, role):
        if role not in ROLES:
            raise ValueError('unknown_resource_episode_role')
        return 'operational'

    def credit_view(self, context, receiver_selection):
        return self.services.bound_role_credit(context, receiver_selection)
