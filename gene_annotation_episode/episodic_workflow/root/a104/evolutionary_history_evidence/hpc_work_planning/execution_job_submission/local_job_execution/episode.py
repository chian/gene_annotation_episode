"""Private A104 LocalExecution episode."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import A104HomologyExecution
from .protected_reference_access import ProtectedReferenceAccess
from .configuration import LocalExecutionConfiguration
from .binding_record import LocalExecutionBindingRecord
from .from_parent import LocalExecutionFromParent
from .goal import LocalExecutionGoal
from .internal_summary import LocalExecutionInternalSummary
from .resource_information import LocalExecutionResourceInformation
from .target_custody import LocalExecutionTargetCustody
from .selector_contracts import LocalExecutionSelectorContracts
from .scientific_inputs import LocalExecutionScientificInputs
from .receipt_selection import LocalExecutionReceiptSelection
from .to_parent import LocalExecutionToParent
from .received_parent_records import LocalExecutionReceivedParentRecords
from .credit import LocalExecutionCredit
from .closed_credit import LocalExecutionClosedCredit
from .completion import LocalExecutionCompletion
from importlib import import_module
from .yield_estimator import ExecutionEpisodeYield
from .retained_native_receipts import LocalExecutionRetainedNativeReceipts
from .native_state import LocalExecutionNativeState
from .received_result_custody import LocalExecutionReceivedResultCustody
from .received_action_identity import LocalExecutionReceivedActionIdentity
from .parent_request_contracts import LocalExecutionParentRequestContracts
from .native_actions import LocalExecutionNativeActions
from .task import LocalExecutionTask
from .presentation import present_execution_context

class ExecutionEpisode(ProtectedReferenceAccess, LocalExecutionConfiguration, LocalExecutionBindingRecord, LocalExecutionFromParent, LocalExecutionGoal, LocalExecutionInternalSummary, LocalExecutionResourceInformation, LocalExecutionTargetCustody, LocalExecutionSelectorContracts, LocalExecutionScientificInputs, LocalExecutionReceiptSelection, LocalExecutionToParent, LocalExecutionReceivedParentRecords, LocalExecutionCredit, LocalExecutionClosedCredit, LocalExecutionCompletion, ExecutionEpisodeYield, LocalExecutionRetainedNativeReceipts, LocalExecutionNativeState, LocalExecutionReceivedResultCustody, LocalExecutionReceivedActionIdentity, LocalExecutionParentRequestContracts, LocalExecutionNativeActions, A104HomologyExecution):
    binding_path = 'evolutionary_history_evidence/hpc_work_planning/execution_job_submission/local_job_execution'
    commissioning_parent = 'evolutionary_history_evidence/hpc_work_planning/execution_job_submission'
    roles = ('launch_local',)
    entry_roles = ()
    replaces_default_instructions = True

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()

    def permitted_common_actions(self, context):
        return ('tool',)
    decision_source_type = LocalExecutionTask
    decision_prompt_renderer = staticmethod(present_execution_context)
