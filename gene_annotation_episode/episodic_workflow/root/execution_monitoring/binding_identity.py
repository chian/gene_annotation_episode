from copy import deepcopy
import hashlib
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical

def as_record(self):
    root = Path(__file__).resolve().parents[1]
    paths = ('execution_monitoring/__init__.py', 'execution_monitoring/binding_identity.py', 'execution_monitoring/credit.py', 'execution_monitoring/episode.py', 'execution_monitoring/execution_configuration.py', 'execution_monitoring/from_child_execution_monitoring.py', 'execution_monitoring/from_parent.py', 'execution_monitoring/goal.py', 'execution_monitoring/internal_summary.py', 'execution_monitoring/progress_observation.py', 'execution_monitoring/task.py', 'execution_monitoring/task_actions.py', 'execution_monitoring/task_decision.py', 'execution_monitoring/task_instructions.py', 'execution_monitoring/task_protocol.py', 'execution_monitoring/task_state.py', 'execution_monitoring/to_child_execution_monitoring.py', 'execution_monitoring/to_parent.py', 'execution_monitoring/waiting.py', 'execution_monitoring/yield.py', 'progress_observations.py', 'progress_records.py', 'episode_bindings.py', 'numerical.py')
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
    return {'version': 'root_monitor_private_v1', 'binding_id': 'monitor',
        'implementation_sha256': hashlib.sha256(canonical(hashes).encode()).hexdigest(),
        'configuration': {'outcome_page_size': self.outcome_page_size,
            **({'information_unit': self.information_unit, 'yield_settings': deepcopy(self.yield_settings)}
               if self.private_yield_binding else {})}}
