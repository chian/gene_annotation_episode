"""Private A104 HPCExecution episode."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import A104HomologyExecution
from .protected_reference_access import ProtectedReferenceAccess
from .configuration import HPCExecutionConfiguration
from .binding_record import HPCExecutionBindingRecord
from .from_parent import HPCExecutionFromParent
from .goal import HPCExecutionGoal
from .internal_summary import HPCExecutionInternalSummary
from .resource_information import HPCExecutionResourceInformation
from .target_custody import HPCExecutionTargetCustody
from .selector_contracts import HPCExecutionSelectorContracts
from .scientific_inputs import HPCExecutionScientificInputs
from .receipt_selection import HPCExecutionReceiptSelection
from .to_parent import HPCExecutionToParent
from .received_parent_records import HPCExecutionReceivedParentRecords
from .credit import HPCExecutionCredit
from .closed_credit import HPCExecutionClosedCredit
from .completion import HPCExecutionCompletion
from importlib import import_module
from .yield_estimator import ExecutionEpisodeYield
from .retained_native_receipts import HPCExecutionRetainedNativeReceipts
from .native_state import HPCExecutionNativeState
from .received_result_custody import HPCExecutionReceivedResultCustody
from .received_action_identity import HPCExecutionReceivedActionIdentity
from .parent_request_contracts import HPCExecutionParentRequestContracts
from .native_actions import HPCExecutionNativeActions
from .task import HPCExecutionTask
from .presentation import present_execution_context

class ExecutionEpisode(ProtectedReferenceAccess, HPCExecutionConfiguration, HPCExecutionBindingRecord, HPCExecutionFromParent, HPCExecutionGoal, HPCExecutionInternalSummary, HPCExecutionResourceInformation, HPCExecutionTargetCustody, HPCExecutionSelectorContracts, HPCExecutionScientificInputs, HPCExecutionReceiptSelection, HPCExecutionToParent, HPCExecutionReceivedParentRecords, HPCExecutionCredit, HPCExecutionClosedCredit, HPCExecutionCompletion, ExecutionEpisodeYield, HPCExecutionRetainedNativeReceipts, HPCExecutionNativeState, HPCExecutionReceivedResultCustody, HPCExecutionReceivedActionIdentity, HPCExecutionParentRequestContracts, HPCExecutionNativeActions, A104HomologyExecution):
    binding_path = 'scientific_process/execution_job_submission/hpc_job_execution'
    commissioning_parent = 'scientific_process/execution_job_submission'
    roles = ('launch_hpc',)
    entry_roles = ()
    replaces_default_instructions = True

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()

    def permitted_common_actions(self, context):
        return ('tool',)
    decision_source_type = HPCExecutionTask
    decision_prompt_renderer = staticmethod(present_execution_context)
