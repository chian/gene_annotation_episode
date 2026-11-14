"""Private job_launch credit behavior for A101."""
from __future__ import annotations
from .execution_contracts import ROLES, deepcopy, math

class HomologyEpisodeCredit:

    def _launch_credit(self, store, assignment, episode_id, run_id):
        return self._job_credit_calculator(store, role='job_launch', assignment=deepcopy(assignment), episode_id=episode_id, run_id=run_id)

    # Retained public compatibility method; this private role does not select it.
    def _monitor_credit(self, store, assignment, episode_id, run_id):
        return self.monitoring_projector(store, role='job_monitor', assignment=deepcopy(assignment), episode_id=episode_id, run_id=run_id)

    # Retained public compatibility method; this private role does not select it.
    def _results_credit(self, store, assignment, episode_id, run_id):
        return self._job_credit_calculator(store, role='job_results', assignment=deepcopy(assignment), episode_id=episode_id, run_id=run_id)

    def initial_credit(self, store, role, assignment, episode_id, run_id):
        self.credit_kind(role)
        value = self._launch_credit(store, assignment, episode_id, run_id)
        value = float(value['credit'] if isinstance(value, dict) else value)
        if not math.isfinite(value):
            raise ValueError('finite_operational_credit_required')
        return value

    def credit_kind(self, role):
        """Declare the information kind of the existing controller projection."""
        if role not in self.roles:
            raise ValueError('unknown_job_episode_role')
        return 'operational'

    def credit_view(self, source):
        self.credit_kind(source.path[-1][0])
        role = 'job_launch'
        information = self.monitoring_projector.information_view(source.workflow.store, assignment=self.assignment(source), episode_id=source.episode_id, run_id=source.workflow.run_id) if self.has_information_channel('job_launch') else {}
        value = self.initial_credit(source.workflow.store, 'job_launch', self.assignment(source), source.episode_id, source.workflow.run_id)
        return {'credit': value, **information}
