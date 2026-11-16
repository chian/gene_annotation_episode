"""Private binding record for A110 hpc_execution."""
from __future__ import annotations
from copy import deepcopy

class HPCBindingRecord:

    def as_record(self):
        return {'version': 'hpc_episode_v1', 'binding_id': 'hpc_work_planning/hpc_allocation_execution', 'configuration': {'resources': deepcopy(self.resources), 'commissions': deepcopy(self.commissions), **({'shared_execution_memory': self.memory.as_record()} if self.memory else {}), **({'require_commission_yield': True} if self.private_yield_binding else {})}}
