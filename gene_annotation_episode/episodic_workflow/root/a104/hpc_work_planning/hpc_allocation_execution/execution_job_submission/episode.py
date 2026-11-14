"""Private A104 Launch episode."""
from __future__ import annotations
from .contracts import KINDS, ROLE_KINDS, plain
from .protected_reference_access import ProtectedReferenceAccess
from .configuration import LaunchConfiguration
from .binding_record import LaunchBindingRecord
from .from_parent import LaunchAssignment
from .request_validation import LaunchRequestValidation
from .scientific_inputs import LaunchScientificInputs
from .retained_result_receipts import LaunchRetainedResults
from .native_receipt_support import LaunchNativeReceiptSupport
from .launch_state import LaunchState
from .resource_information import LaunchResourceInformation
from .goal import LaunchGoal
from .internal_summary import LaunchSummary
from .capability_operations import LaunchCapabilities
from .received_records import LaunchReceivedRecords
from .resource_return_support import LaunchResourceReturns
from .received_reports import LaunchReceivedReports
from .to_parent import LaunchReport
from .credit import ExecutionEpisodeCredit
from importlib import import_module
ExecutionEpisodeYield = import_module('.yield', __package__).ExecutionEpisodeYield
from .contracts import A104HomologyExecution
from .task import LaunchTask
from .presentation import present_execution_context

class ExecutionEpisode(ProtectedReferenceAccess, LaunchConfiguration, LaunchBindingRecord, LaunchAssignment, LaunchRequestValidation, LaunchScientificInputs, LaunchRetainedResults, LaunchNativeReceiptSupport, LaunchState, LaunchResourceInformation, LaunchGoal, LaunchSummary, LaunchCapabilities, LaunchReceivedRecords, LaunchResourceReturns, LaunchReceivedReports, LaunchReport, ExecutionEpisodeCredit, ExecutionEpisodeYield, A104HomologyExecution):
    binding_path = 'hpc_work_planning/hpc_allocation_execution/execution_job_submission'
    commissioning_parent = 'hpc_work_planning/hpc_allocation_execution'
    roles = ('launch',)
    entry_roles = ()
    replaces_default_instructions = True

    def child_roles(self, role):
        return tuple(ROLE_KINDS) if role == 'launch' else ()

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific return."""
        if parent is not None and parent.path[-1][0] == 'scientific_process' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_handoff_refs',)
        return ()

    def allowed_children(self, parent, caller_capabilities):
        if parent.role != 'launch':
            return ()
        assignment = self._launch(plain(parent.assignment))
        return tuple((role for role, kind in ROLE_KINDS.items() if any((KINDS[configuration['kind']] == kind and self._permitted(assignment, resource_id) for resource_id, configuration in self.resources.items()))))

    def permitted_common_actions(self, context):
        if any((role == 'hpc' for role, _ in context.path)):
            return ('tool', 'child', 'redeliver_report')
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')
    decision_source_type = LaunchTask
    decision_prompt_renderer = staticmethod(present_execution_context)

    def child_request_assembler(self, role):
        if role == 'launch_api':
            from .to_child_api_job_execution import assemble_request
            return assemble_request
        if role == 'launch_local':
            from .to_child_local_job_execution import assemble_request
            return assemble_request
        if role == 'launch_hpc':
            from .to_child_hpc_job_execution import assemble_request
            return assemble_request
        return None

    def child_report_receiver(self, role):
        if role == 'launch_api':
            from .from_child_api_job_execution import receive_report
            return receive_report
        if role == 'launch_local':
            from .from_child_local_job_execution import receive_report
            return receive_report
        if role == 'launch_hpc':
            from .from_child_hpc_job_execution import receive_report
            return receive_report
        return None
