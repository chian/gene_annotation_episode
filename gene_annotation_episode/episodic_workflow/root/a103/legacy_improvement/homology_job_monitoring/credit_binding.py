"""Private homology monitoring credit binding."""
from __future__ import annotations
from .contracts import deepcopy

class MonitorCreditBinding:

    def binding_for(self, role):
        if role not in self._role_credit_bindings:
            raise ValueError('unknown_job_episode_role')
        return deepcopy(self._role_credit_bindings[role])

    def has_information_channel(self, role):
        return getattr(self.monitoring_projector, 'include_handoff_checks', False) and role in getattr(self.monitoring_projector, 'information_roles', ()) and callable(getattr(self.monitoring_projector, 'information_view', None))
