"""Connect private A106 launch operational responsibilities."""
from __future__ import annotations
from .task import OperationalTask
from .execution_contracts import KINDS, ROLE_KINDS, plain
from .credit import ExecutionEpisodeCredit
from importlib import import_module as _import_module
from .yield_estimator import ExecutionEpisodeYield
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
from .from_parent_launch import LaunchParentAssignment
from .to_child_api_job_execution import prepare_commission as prepare_api_job_execution
from .from_child_api_job_execution import receive_report as receive_api_job_execution

class ExecutionEpisode(LaunchParentAssignment, OperationalConfiguration, OperationalBindingRecord, OperationalGoal, OperationalAssignment, OperationalReport, ReceivedOperationalEvidence, OperationalSummary, OperationalExecutionState, NativeInputCustody, OperationalOperations, ExecutionEpisodeCredit, ExecutionEpisodeYield):
    decision_source_type = OperationalTask
    binding_path = 'published_evidence_assessment/execution_job_submission'
    commissioning_parent = 'published_evidence_assessment'
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
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')

    def context_hook_applies(self, context):
        """Own role hooks; the original Launch parent admits external delivery."""
        role = getattr(context, 'role', None)
        path = getattr(context, 'path', None)
        if role is None:
            role = path[-1][0] if path else context if isinstance(context, str) else None
        return role == 'launch' if role in ('launch', 'launch_api', 'results') else True

    def child_request_preparer_for_binding(self, role, binding_path):
        return {('launch_api', 'published_evidence_assessment/execution_job_submission/api_job_execution'): prepare_api_job_execution}.get((role, binding_path))

    def child_report_receiver_for_binding(self, role, binding_path):
        return {('launch_api', 'published_evidence_assessment/execution_job_submission/api_job_execution'): receive_api_job_execution}.get((role, binding_path))
