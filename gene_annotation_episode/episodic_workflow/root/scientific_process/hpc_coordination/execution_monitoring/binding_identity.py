from copy import deepcopy
import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical

def as_record(self):
    root = Path(__file__).resolve().parents[3]
    paths = ('scientific_process/hpc_coordination/execution_monitoring/__init__.py', 'scientific_process/hpc_coordination/execution_monitoring/binding_identity.py', 'scientific_process/hpc_coordination/execution_monitoring/credit.py', 'scientific_process/hpc_coordination/execution_monitoring/episode.py', 'scientific_process/hpc_coordination/execution_monitoring/execution_configuration.py', 'scientific_process/hpc_coordination/execution_monitoring/from_child_execution_monitoring.py', 'scientific_process/hpc_coordination/execution_monitoring/from_parent.py', 'scientific_process/hpc_coordination/execution_monitoring/goal.py', 'scientific_process/hpc_coordination/execution_monitoring/internal_summary.py', 'scientific_process/hpc_coordination/execution_monitoring/progress_observation.py', 'scientific_process/hpc_coordination/execution_monitoring/task.py', 'scientific_process/hpc_coordination/execution_monitoring/task_actions.py', 'scientific_process/hpc_coordination/execution_monitoring/task_decision.py', 'scientific_process/hpc_coordination/execution_monitoring/task_instructions.py', 'scientific_process/hpc_coordination/execution_monitoring/task_protocol.py', 'scientific_process/hpc_coordination/execution_monitoring/task_state.py', 'scientific_process/hpc_coordination/execution_monitoring/to_child_execution_monitoring.py', 'scientific_process/hpc_coordination/execution_monitoring/to_parent.py', 'scientific_process/hpc_coordination/execution_monitoring/waiting.py', 'scientific_process/hpc_coordination/execution_monitoring/yield.py', 'progress_observations.py', 'progress_records.py', 'episode_bindings.py', 'numerical.py')
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
    return {'version': 'root_monitor_private_v1', 'binding_id': 'monitor',
        'implementation_sha256': hashlib.sha256(canonical(hashes).encode()).hexdigest(),
        'configuration': {'outcome_page_size': self.outcome_page_size,
            **({'information_unit': self.information_unit, 'yield_settings': deepcopy(self.yield_settings)}
               if self.private_yield_binding else {})}}
