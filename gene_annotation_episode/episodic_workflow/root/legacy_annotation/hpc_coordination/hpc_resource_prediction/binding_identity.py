"""Identity of the actual private implementation and its selected dependencies."""
from copy import deepcopy
import hashlib
from pathlib import Path
from gene_annotation_episode.execution_contracts import canonical

def as_record(self):
    root = Path(__file__).resolve().parents[3]
    paths = (
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/child_commissioning.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/credit.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/execution_configuration.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/from_parent.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/goal.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/hpc_operations.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/internal_summary.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/model_records.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/to_parent.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/report_fields.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/report_delivery.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/reference_custody.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/reference_access.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/waiting.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/yield_estimator.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/episode.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/binding_identity.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/task.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/task_state.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/task_protocol.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/task_decision.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/decision_context.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/decision_exchange.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/task_instructions.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/task_actions.py',
        'legacy_annotation/hpc_coordination/hpc_resource_prediction/task_report.py',
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
    return {'version': 'root_hpc_private_v1', 'binding_id': 'root_legacy_annotation_hpc_coordination_hpc_resource_prediction',
        'implementation_sha256': hashlib.sha256(canonical(hashes).encode()).hexdigest(),
        'configuration': {'resources': deepcopy(self.resources), 'commissions': deepcopy(self.commissions),
            **({'shared_execution_memory': self.memory.as_record()} if self.memory else {}),
            **({'require_commission_yield': True} if self.private_yield_binding else {})}}
