"""Identity of the actual private implementation and its selected dependencies."""
from copy import deepcopy
import hashlib
from pathlib import Path
from gene_annotation_episode.execution_contracts import canonical

def as_record(self):
    root = Path(__file__).resolve().parents[2]
    paths = (
        'hpc_coordination/hpc_resource_prediction/child_commissioning.py',
        'hpc_coordination/hpc_resource_prediction/credit.py',
        'hpc_coordination/hpc_resource_prediction/execution_configuration.py',
        'hpc_coordination/hpc_resource_prediction/from_parent.py',
        'hpc_coordination/hpc_resource_prediction/goal.py',
        'hpc_coordination/hpc_resource_prediction/hpc_operations.py',
        'hpc_coordination/hpc_resource_prediction/internal_summary.py',
        'hpc_coordination/hpc_resource_prediction/model_records.py',
        'hpc_coordination/hpc_resource_prediction/to_parent.py',
        'hpc_coordination/hpc_resource_prediction/report_fields.py',
        'hpc_coordination/hpc_resource_prediction/report_delivery.py',
        'hpc_coordination/hpc_resource_prediction/reference_custody.py',
        'hpc_coordination/hpc_resource_prediction/reference_access.py',
        'hpc_coordination/hpc_resource_prediction/waiting.py',
        'hpc_coordination/hpc_resource_prediction/yield.py',
        'hpc_coordination/hpc_resource_prediction/episode.py',
        'hpc_coordination/hpc_resource_prediction/binding_identity.py',
        'hpc_coordination/hpc_resource_prediction/task.py',
        'hpc_coordination/hpc_resource_prediction/task_state.py',
        'hpc_coordination/hpc_resource_prediction/task_protocol.py',
        'hpc_coordination/hpc_resource_prediction/task_decision.py',
        'hpc_coordination/hpc_resource_prediction/decision_context.py',
        'hpc_coordination/hpc_resource_prediction/decision_exchange.py',
        'hpc_coordination/hpc_resource_prediction/task_instructions.py',
        'hpc_coordination/hpc_resource_prediction/task_actions.py',
        'hpc_coordination/hpc_resource_prediction/task_report.py',
        'library/hpc_campaign.py',
        'library/hpc_ledger.py',
        'library/hpc_prediction.py',
        'library/hpc_queue.py',
        'library/hpc_resource_prediction.py',
        'library/hpc_monitoring.py',
        'library/hpc_history.py',
        'library/hpc_allocation.py',
        'library/hpc_launch_authentication.py',
        'library/hpc_launch_context.py',
        'episode_bindings.py',
        'numerical.py',
        'episode_return_records.py',
        'completion_evidence.py',
        'library/execution_progress.py',
        'library/execution_resource_identity.py',
    )
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
    return {'version': 'root_hpc_private_v1', 'binding_id': 'hpc_prediction',
        'implementation_sha256': hashlib.sha256(canonical(hashes).encode()).hexdigest(),
        'configuration': {'resources': deepcopy(self.resources), 'commissions': deepcopy(self.commissions),
            **({'shared_execution_memory': self.memory.as_record()} if self.memory else {}),
            **({'require_commission_yield': True} if self.private_yield_binding else {})}}
