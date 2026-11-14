"""Private A101 launch_hpc binding record."""
from __future__ import annotations
from .execution_contracts import VERSION, deepcopy

class OperationalBindingRecord:

    def as_record(self):
        return {'binding_id': 'execution_job_submission/hpc_job_execution', 'version': VERSION, 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information), 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles), **({'require_private_yield': True} if self.private_yield_binding else {}), **({'results_yield_profiles': deepcopy(self.results_yield_profiles)} if self.results_yield_profiles else {}), **({'task_yield_profiles': deepcopy(self.task_yield_profiles)} if self.task_yield_profiles else {})}}
