"""Private A104 Launch episode."""
from __future__ import annotations
from .child_messages import LaunchChildMessages
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import A104HomologyExecution
from .binding_roles import KINDS
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from .protected_reference_access import ProtectedReferenceAccess
from .configuration import LaunchConfiguration
from .binding_record import LaunchBindingRecord
from .from_parent import LaunchFromParent
from .goal import LaunchGoal
from .internal_summary import LaunchInternalSummary
from .resource_information import LaunchResourceInformation
from .target_custody import LaunchTargetCustody
from .selector_contracts import LaunchSelectorContracts
from .scientific_inputs import LaunchScientificInputs
from .work_operations import LaunchWorkOperations
from .receipt_selection import LaunchReceiptSelection
from .to_parent import LaunchToParent
from .received_parent_records import LaunchReceivedParentRecords
from .credit import LaunchCredit
from .closed_credit import LaunchClosedCredit
from .completion import LaunchCompletion
from importlib import import_module
ExecutionEpisodeYield = import_module('.yield', __package__).ExecutionEpisodeYield
from .retained_native_receipts import LaunchRetainedNativeReceipts
from .launch_state import LaunchLaunchState
from .received_result_custody import LaunchReceivedResultCustody
from .received_action_identity import LaunchReceivedActionIdentity
from .launch_requests import LaunchLaunchRequests
from .task import LaunchTask
from .presentation import present_execution_context

class ExecutionEpisode(ProtectedReferenceAccess, LaunchChildMessages, LaunchConfiguration, LaunchBindingRecord, LaunchFromParent, LaunchGoal, LaunchInternalSummary, LaunchResourceInformation, LaunchTargetCustody, LaunchSelectorContracts, LaunchScientificInputs, LaunchWorkOperations, LaunchReceiptSelection, LaunchToParent, LaunchReceivedParentRecords, LaunchCredit, LaunchClosedCredit, LaunchCompletion, ExecutionEpisodeYield, LaunchRetainedNativeReceipts, LaunchLaunchState, LaunchReceivedResultCustody, LaunchReceivedActionIdentity, LaunchLaunchRequests, A104HomologyExecution):
    binding_path = 'execution_job_submission'
    commissioning_parent = 'legacy_annotation'
    roles = ('launch',)
    entry_roles = ('launch',)
    replaces_default_instructions = True

    def child_roles(self, role):
        return tuple(ROLE_KINDS)

    def allowed_children(self, parent, caller_capabilities):
        assignment = self._launch(plain(parent.assignment))
        return tuple((role for role, kind in ROLE_KINDS.items() if any((KINDS[configuration['kind']] == kind and self._permitted(assignment, resource_id) for resource_id, configuration in self.resources.items()))))

    def permitted_common_actions(self, context):
        if any((role == 'hpc' for role, _ in context.path)):
            return ('tool', 'child', 'redeliver_report')
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')
    decision_source_type = LaunchTask
    decision_prompt_renderer = staticmethod(present_execution_context)
