"""Private A101 job_monitor binding record."""
from __future__ import annotations
from .execution_contracts import ROLES, _binding, deepcopy

class OperationalBindingRecord:

    def as_record(self):
        return {'binding_id': 'homology_job_monitoring', 'version': 'homology_episode_bindings_v4', 'registry_directory': str(self.jobs.directory), 'registry_configuration': self.jobs.config, 'parser_policy': self.parser_policy.to_dict(), 'job_credit_calculator': _binding(self._job_credit_calculator), 'monitoring_projector': _binding(self.monitoring_projector), 'role_credit_bindings': deepcopy(self._role_credit_bindings), 'monitoring_projector_parameters': self.monitoring_projector.as_record() if callable(getattr(self.monitoring_projector, 'as_record', None)) else None, 'statistics': None if self.statistics is None else self.statistics.as_record()}

    def describe(self):
        return {role: {'report_facts': self.fact_sources(role), 'responsibility': self.instructions(role)} for role in self.roles}
