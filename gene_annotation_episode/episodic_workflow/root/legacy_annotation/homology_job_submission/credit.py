"""Scoped job-role bindings for the existing shared method_loop.

No production score, timing exchange rate, itinerary or private decision loop.
The caller owns resource/scoring configuration; the parent owns commissioning.
"""
from __future__ import annotations
from copy import deepcopy
import math
ROLES = ('job_launch',)

def _launch_credit(self, store, assignment, episode_id, run_id):
    return self._job_credit_calculator(store, role='job_launch', assignment=deepcopy(assignment), episode_id=episode_id, run_id=run_id)

def initial_credit(self, store, role, assignment, episode_id, run_id):
    bindings = {'job_launch': self._launch_credit}
    if role not in bindings:
        raise ValueError('unknown_job_episode_role')
    value = bindings[role](store, assignment, episode_id, run_id)
    value = float(value['credit'] if isinstance(value, dict) else value)
    if not math.isfinite(value):
        raise ValueError('finite_operational_credit_required')
    return value

def binding_for(self, role):
    if role not in ROLES:
        raise ValueError('unknown_job_episode_role')
    return deepcopy(self._role_credit_bindings[role])

def credit_kind(self, role):
    """Declare the information kind of the existing controller projection."""
    if role not in ROLES:
        raise ValueError('unknown_job_episode_role')
    return 'operational'

def has_information_channel(self, role):
    return getattr(self.monitoring_projector, 'include_handoff_checks', False) and role in getattr(self.monitoring_projector, 'information_roles', ()) and callable(getattr(self.monitoring_projector, 'information_view', None))

def credit_view(self, source):
    role = 'job_launch'
    information = self.monitoring_projector.information_view(source.workflow.store, assignment=self.assignment(source), episode_id=source.episode_id, run_id=source.workflow.run_id) if self.has_information_channel(role) else {}
    value = self.initial_credit(source.workflow.store, role, self.assignment(source), source.episode_id, source.workflow.run_id)
    return {'credit': value, **information}
