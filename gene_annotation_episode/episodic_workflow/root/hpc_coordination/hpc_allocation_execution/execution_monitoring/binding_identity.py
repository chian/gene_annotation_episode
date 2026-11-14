from copy import deepcopy
import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical

def as_record(self):
    root = Path(__file__).resolve().parents[3]
    paths = ('hpc_coordination/hpc_allocation_execution/execution_monitoring/__init__.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/binding_identity.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/credit.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/episode.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/execution_configuration.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/from_child_execution_monitoring.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/from_parent.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/goal.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/internal_summary.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/progress_observation.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/task.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/task_actions.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/task_decision.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/task_instructions.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/task_protocol.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/task_state.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/to_child_execution_monitoring.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/to_parent.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/waiting.py', 'hpc_coordination/hpc_allocation_execution/execution_monitoring/yield_estimator.py', 'progress_observations.py', 'progress_records.py', 'episode_bindings.py', 'numerical.py')
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
    return {'version': 'root_monitor_private_v1', 'binding_id': 'monitor',
        'implementation_sha256': hashlib.sha256(canonical(hashes).encode()).hexdigest(),
        'configuration': {'outcome_page_size': self.outcome_page_size,
            **({'information_unit': self.information_unit, 'yield_settings': deepcopy(self.yield_settings)}
               if self.private_yield_binding else {})}}
