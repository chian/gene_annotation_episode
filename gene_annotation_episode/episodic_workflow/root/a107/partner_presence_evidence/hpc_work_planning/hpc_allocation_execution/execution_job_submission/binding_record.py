"""Private A107 Launch binding record"""
from __future__ import annotations
from .binding_roles import VERSION
from copy import deepcopy

class LaunchBindingRecord:

    def as_record(self):
        return {'binding_id': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission', 'version': VERSION, 'configuration': {'resources': deepcopy(self.resources), 'initial_information': deepcopy(self.initial_information), 'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit, 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles), **({'require_private_yield': True} if self.private_yield_binding else {}), **({'results_yield_profiles': deepcopy(self.results_yield_profiles)} if self.results_yield_profiles else {}), **({'task_yield_profiles': deepcopy(self.task_yield_profiles)} if self.task_yield_profiles else {})}}
