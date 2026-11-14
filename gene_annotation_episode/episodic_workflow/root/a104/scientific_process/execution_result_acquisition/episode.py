"""Private A104 Results episode."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import A104HomologyExecution
from .protected_reference_access import ProtectedReferenceAccess
from .configuration import ResultsConfiguration
from .binding_record import ResultsBindingRecord
from .from_parent import ResultsFromParent
from .saved_commission import ResultsSavedCommission
from .goal import ResultsGoal
from .internal_summary import ResultsInternalSummary
from .resource_information import ResultsResourceInformation
from .target_custody import ResultsTargetCustody
from .selector_contracts import ResultsSelectorContracts
from .scientific_inputs import ResultsScientificInputs
from .result_state import ResultsResultState
from .work_operations import ResultsWorkOperations
from .native_file_acquisition import ResultsNativeFileAcquisition
from .result_publication import ResultsResultPublication
from .receipt_selection import ResultsReceiptSelection
from .to_parent import ResultsToParent
from .received_parent_records import ResultsReceivedParentRecords
from .credit import ResultsCredit
from .closed_credit import ResultsClosedCredit
from .completion import ResultsCompletion
from importlib import import_module
ExecutionEpisodeYield = import_module('.yield', __package__).ExecutionEpisodeYield
from .retained_native_receipts import ResultsRetainedNativeReceipts
from .received_launch_requests import ResultsReceivedLaunchRequests
from .task import ResultsTask
from .presentation import present_execution_context

class ExecutionEpisode(ProtectedReferenceAccess, ResultsConfiguration, ResultsBindingRecord, ResultsFromParent, ResultsSavedCommission, ResultsGoal, ResultsInternalSummary, ResultsResourceInformation, ResultsTargetCustody, ResultsSelectorContracts, ResultsScientificInputs, ResultsResultState, ResultsWorkOperations, ResultsNativeFileAcquisition, ResultsResultPublication, ResultsReceiptSelection, ResultsToParent, ResultsReceivedParentRecords, ResultsCredit, ResultsClosedCredit, ResultsCompletion, ExecutionEpisodeYield, ResultsRetainedNativeReceipts, ResultsReceivedLaunchRequests, A104HomologyExecution):
    binding_path = 'scientific_process/execution_result_acquisition'
    commissioning_parent = 'scientific_process'
    roles = ('results',)
    entry_roles = ('results',)
    replaces_default_instructions = True

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()

    def permitted_common_actions(self, context):
        target = self._target(context)
        if target['resource_kind'] == 'api' and target['assignment']['version'] == 'api_service_assignment_v1':
            return ('tool', 'wait')
        return ('tool',)
    decision_source_type = ResultsTask
    decision_prompt_renderer = staticmethod(present_execution_context)
