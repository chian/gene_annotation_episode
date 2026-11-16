"""Record of the actual private binding and its configuration."""
from copy import deepcopy

def as_record(self):
    return {'version': 'root_hpc_private_v1', 'binding_id': 'root_scientific_process_hpc_coordination_hpc_resource_prediction',
        'configuration': {'resources': deepcopy(self.resources), 'commissions': deepcopy(self.commissions),
            **({'shared_execution_memory': self.memory.as_record()} if self.memory else {}),
            **({'require_commission_yield': True} if self.private_yield_binding else {})}}
