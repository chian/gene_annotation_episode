"""Private configuration for A103 prediction."""
from __future__ import annotations
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a103.communication import plain
from gene_annotation_episode.episodic_workflow.root.a103.hpc_campaign import validate_commission



class PredictionConfiguration:
    def __init__(self, services, *, store, run_id, directory, resources, commissions,
                 shared_execution_memory=None, require_commission_yield=False):
        self.services, self.store, self.run_id = services, store, run_id
        self.directory = Path(directory)
        self.resources = plain(resources)
        commissions = plain(commissions)
        if not isinstance(commissions, dict):
            raise ValueError('explicit_hpc_commissions_required')
        if not any(row.get('kind') == 'pbs_ssh' for row in self.resources.values()):
            raise ValueError('explicit_hpc_resource_required')
        self.commissions = {key: validate_commission(plain(value), self.resources)
                            for key, value in commissions.items()}
        if type(require_commission_yield) is not bool:
            raise TypeError('hpc_private_yield_binding_requires_boolean')
        self.private_yield_binding = require_commission_yield
        if require_commission_yield and any('yield_bindings' not in value
                for value in self.commissions.values()):
            raise ValueError('hpc_static_commission_yield_binding_required')
        from gene_annotation_episode.episodic_workflow.root.a103.execution_memory import ExecutionMemory
        self.memory = (None if shared_execution_memory is None else
                       ExecutionMemory(**plain(shared_execution_memory)))
