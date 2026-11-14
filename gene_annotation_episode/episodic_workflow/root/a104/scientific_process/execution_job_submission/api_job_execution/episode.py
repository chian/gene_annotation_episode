"""Private A104 API episode."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import A104HomologyExecution
from .binding_roles import KINDS
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from .protected_reference_access import ProtectedReferenceAccess
from .configuration import APIConfiguration
from .binding_record import APIBindingRecord
from .from_parent import APIFromParent
from .parent_request_contracts import APIParentRequestContracts
from .goal import APIGoal
from .instructions import APIInstructions
from .internal_summary import APIInternalSummary
from .resource_information import APIResourceInformation
from .api_actions import APIApiActions
from .api_state import APIApiState
from .to_parent import APIToParent
from .received_execution_records import APIReceivedExecutionRecords
from .scientific_inputs import APIScientificInputs
from .received_target_custody import APIReceivedTargetCustody
from .received_selector_contracts import APIReceivedSelectorContracts
from .received_result_records import APIReceivedResultRecords
from .received_practical_state import APIReceivedPracticalState
from .credit import APICredit
from .closed_credit import APIClosedCredit
from .completion import APICompletion
from importlib import import_module
ExecutionEpisodeYield = import_module('.yield', __package__).ExecutionEpisodeYield
from .task import APIJobTask
from .presentation import present_api_context

class ExecutionEpisode(ProtectedReferenceAccess, APIConfiguration, APIBindingRecord, APIFromParent, APIParentRequestContracts, APIGoal, APIInstructions, APIInternalSummary, APIResourceInformation, APIApiActions, APIApiState, APIToParent, APIReceivedExecutionRecords, APIScientificInputs, APIReceivedTargetCustody, APIReceivedSelectorContracts, APIReceivedResultRecords, APIReceivedPracticalState, APICredit, APIClosedCredit, APICompletion, ExecutionEpisodeYield, A104HomologyExecution):
    binding_path = 'scientific_process/execution_job_submission/api_job_execution'
    commissioning_parent = 'scientific_process/execution_job_submission'
    roles = ('launch_api',)
    entry_roles = ()
    replaces_default_instructions = True

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        parent.role
        return ()

    def permitted_common_actions(self, context):
        assignment = self._validate_request(plain(context.assignment))
        if assignment['version'] == 'api_service_assignment_v1':
            return ('tool', 'wait')
        return ('tool',)
    decision_source_type = APIJobTask
    decision_prompt_renderer = staticmethod(present_api_context)
