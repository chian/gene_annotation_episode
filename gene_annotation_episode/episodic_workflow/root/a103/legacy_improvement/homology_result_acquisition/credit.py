"""Private job_results credit behavior for A103."""
from __future__ import annotations
from .contracts import ROLES, deepcopy, math

class HomologyEpisodeCredit:

    def _results_credit(self, store, assignment, episode_id, run_id):
        return self._job_credit_calculator(store, role='job_results', assignment=deepcopy(assignment), episode_id=episode_id, run_id=run_id)

    def initial_credit(self, store, role, assignment, episode_id, run_id):
        bindings = {'job_results': self._results_credit}
        if role not in bindings:
            raise ValueError('unknown_job_episode_role')
        value = bindings[role](store, assignment, episode_id, run_id)
        value = float(value['credit'] if isinstance(value, dict) else value)
        if not math.isfinite(value):
            raise ValueError('finite_operational_credit_required')
        return value

    def credit_kind(self, role):
        """Declare the information kind of the existing controller projection."""
        if role not in ROLES:
            raise ValueError('unknown_job_episode_role')
        return 'operational'

    def credit_view(self, source):
        role = source.path[-1][0]
        information = self.monitoring_projector.information_view(source.workflow.store, assignment=self.assignment(source), episode_id=source.episode_id, run_id=source.workflow.run_id) if self.has_information_channel(role) else {}
        value = self.initial_credit(source.workflow.store, role, self.assignment(source), source.episode_id, source.workflow.run_id)
        return {'credit': value, **information}
