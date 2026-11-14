"""Connect private A101 launch operational responsibilities."""
from __future__ import annotations
from .task import OperationalTask
from .execution_contracts import KINDS, ROLE_KINDS, plain
from .blast_request_custody import BlastRequestCustody
from .blast_received_context import BlastReceivedContext
from .blast_pending_work import BlastPendingWork
from gene_annotation_episode.episodic_workflow.root.a101.library.blast_return_contracts import _blast_reference_source
from .credit import ExecutionEpisodeCredit
from importlib import import_module as _import_module
ExecutionEpisodeYield = _import_module('.yield', __package__).ExecutionEpisodeYield
from .configuration import OperationalConfiguration
from .binding_record import OperationalBindingRecord
from .goal import OperationalGoal
from .from_parent import OperationalAssignment
from .to_parent import OperationalReport
from .received_evidence import ReceivedOperationalEvidence
from .internal_summary import OperationalSummary
from .execution_state import OperationalExecutionState
from .native_input_custody import NativeInputCustody
from .execution_operations import OperationalOperations
from .result_acquisition import OperationalResultAcquisition
from .from_parent_launch import LaunchParentAssignment
from .to_child_api_job_execution import prepare_commission as prepare_api_job_execution
from .from_child_api_job_execution import receive_report as receive_api_job_execution
from .to_child_hpc_job_execution import prepare_commission as prepare_hpc_job_execution
from .from_child_hpc_job_execution import receive_report as receive_hpc_job_execution
from .to_child_local_job_execution import prepare_commission as prepare_local_job_execution
from .from_child_local_job_execution import receive_report as receive_local_job_execution

class ExecutionEpisode(LaunchParentAssignment, OperationalConfiguration, OperationalBindingRecord, OperationalGoal, OperationalAssignment, OperationalReport, ReceivedOperationalEvidence, OperationalSummary, OperationalExecutionState, NativeInputCustody, OperationalOperations, OperationalResultAcquisition, ExecutionEpisodeCredit, ExecutionEpisodeYield, BlastRequestCustody, BlastReceivedContext, BlastPendingWork):
    _blast_reference_source = staticmethod(_blast_reference_source)
    decision_source_type = OperationalTask
    _private_practical_estimator_owner = ('launch', ExecutionEpisodeYield.practical_estimator, ExecutionEpisodeYield._private_practical_estimator)
    binding_path = 'scientific_process/execution_job_submission'
    commissioning_parent = 'scientific_process'
    roles = ('launch',)
    entry_roles = ('launch',)
    replaces_default_instructions = True

    def child_roles(self, role):
        self.credit_kind(role)
        return tuple(ROLE_KINDS)

    def allowed_children(self, parent, caller_capabilities):
        self.credit_kind(parent.role)
        assignment = self._launch(plain(parent.assignment))
        return tuple((role for role, kind in ROLE_KINDS.items() if any((KINDS[configuration['kind']] == kind and self._permitted(assignment, resource_id) for resource_id, configuration in self.resources.items()))))

    def permitted_common_actions(self, context):
        self.credit_kind(context.role)
        if any((role == 'hpc' for role, _ in context.path)):
            return ('tool', 'child', 'redeliver_report')
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')

    def context_hook_applies(self, context):
        """Own role hooks; the original Launch parent admits external delivery."""
        role = getattr(context, 'role', None)
        path = getattr(context, 'path', None)
        if role is None:
            role = path[-1][0] if path else context if isinstance(context, str) else None
        return role == 'launch' if role in ('launch', 'launch_local', 'launch_hpc', 'launch_api', 'results') else True

    def child_request_preparer_for_binding(self, role, binding_path):
        return {('launch_api', 'scientific_process/execution_job_submission/api_job_execution'): prepare_api_job_execution, ('launch_hpc', 'scientific_process/execution_job_submission/hpc_job_execution'): prepare_hpc_job_execution, ('launch_local', 'scientific_process/execution_job_submission/local_job_execution'): prepare_local_job_execution}.get((role, binding_path))

    def child_report_receiver_for_binding(self, role, binding_path):
        return {('launch_api', 'scientific_process/execution_job_submission/api_job_execution'): receive_api_job_execution, ('launch_hpc', 'scientific_process/execution_job_submission/hpc_job_execution'): receive_hpc_job_execution, ('launch_local', 'scientific_process/execution_job_submission/local_job_execution'): receive_local_job_execution}.get((role, binding_path))
