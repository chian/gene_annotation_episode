from __future__ import annotations
from .execution_contracts import VERSION
from .execution_contracts import deepcopy

class NativeBindingRecord:

    def as_record(self):
        return {'binding_id': 'biochemical_feasibility_evidence/hpc_work_planning/execution_job_submission/local_job_execution', 'version': VERSION, 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information), 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles), **({'require_private_yield': True} if self.private_yield_binding else {}), **({'results_yield_profiles': deepcopy(self.results_yield_profiles)} if self.results_yield_profiles else {}), **({'task_yield_profiles': deepcopy(self.task_yield_profiles)} if self.task_yield_profiles else {})}}
