from copy import deepcopy
import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical

def as_record(self):
    root = Path(__file__).resolve().parents[3]
    paths = ('legacy_annotation/hpc_coordination/execution_monitoring/__init__.py', 'legacy_annotation/hpc_coordination/execution_monitoring/binding_identity.py', 'legacy_annotation/hpc_coordination/execution_monitoring/credit.py', 'legacy_annotation/hpc_coordination/execution_monitoring/episode.py', 'legacy_annotation/hpc_coordination/execution_monitoring/execution_configuration.py', 'legacy_annotation/hpc_coordination/execution_monitoring/from_child_execution_monitoring.py', 'legacy_annotation/hpc_coordination/execution_monitoring/from_parent.py', 'legacy_annotation/hpc_coordination/execution_monitoring/goal.py', 'legacy_annotation/hpc_coordination/execution_monitoring/internal_summary.py', 'legacy_annotation/hpc_coordination/execution_monitoring/progress_observation.py', 'legacy_annotation/hpc_coordination/execution_monitoring/task.py', 'legacy_annotation/hpc_coordination/execution_monitoring/task_actions.py', 'legacy_annotation/hpc_coordination/execution_monitoring/task_decision.py', 'legacy_annotation/hpc_coordination/execution_monitoring/task_instructions.py', 'legacy_annotation/hpc_coordination/execution_monitoring/task_protocol.py', 'legacy_annotation/hpc_coordination/execution_monitoring/task_state.py', 'legacy_annotation/hpc_coordination/execution_monitoring/to_child_execution_monitoring.py', 'legacy_annotation/hpc_coordination/execution_monitoring/to_parent.py', 'legacy_annotation/hpc_coordination/execution_monitoring/waiting.py', 'legacy_annotation/hpc_coordination/execution_monitoring/yield_estimator.py', 'progress_observations.py', 'progress_records.py', 'episode_bindings.py', 'numerical.py')
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
    return {'version': 'root_monitor_private_v1', 'binding_id': 'monitor',
        'implementation_sha256': hashlib.sha256(canonical(hashes).encode()).hexdigest(),
        'configuration': {'outcome_page_size': self.outcome_page_size,
            **({'information_unit': self.information_unit, 'yield_settings': deepcopy(self.yield_settings)}
               if self.private_yield_binding else {})}}
