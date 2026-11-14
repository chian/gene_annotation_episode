"""Private launch_local credit behavior for A101."""
from __future__ import annotations
from .execution_contracts import ROLES

class ResourceEpisodeCredit:

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_resource_episode_role')
        return 'operational'

    def credit_view(self, context, receiver_selection):
        return self.services.bound_role_credit(context, receiver_selection)
