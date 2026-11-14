"""Connect the predefined A102 API job to its own task and message responsibilities."""
from __future__ import annotations
from .execution_contracts import KINDS, ROLE_KINDS, plain
from .configuration import APIConfiguration
from .binding_record import APIBindingRecord
from .from_parent import APIFromParent
from .goal import APIGoal
from .internal_summary import APIInternalSummary
from .resource_information import APIResourceInformation
from .parent_input_custody import APIParentInputCustody
from .retained_protein_reader import APIRetainedProteinReader
from .execution_state import APIExecutionState
from .api_operations import APIApiOperations
from .result_selection import APIResultSelection
from .retained_result_acquisition import APIRetainedResultAcquisition
from .retained_result_publication import APIRetainedResultPublication
from .received_records import APIReceivedRecords
from .to_parent import APIToParent
from .credit import APICredit
from .closed_credit import APIClosedCredit
from .completion import APICompletion
from importlib import import_module as _import_module
ExecutionEpisodeYield = _import_module('.yield', __package__).ExecutionEpisodeYield
from .task import APIJobTask
from gene_annotation_episode.episodic_workflow.root.a102.execution_prompt import render_api_launch_prompt

from .action_policy import APIActionPolicy

from .child_eligibility import APIChildEligibility

class ExecutionEpisode(APIChildEligibility, APIActionPolicy, APIConfiguration, APIBindingRecord, APIFromParent, APIGoal, APIInternalSummary, APIResourceInformation, APIParentInputCustody, APIRetainedProteinReader, APIExecutionState, APIApiOperations, APIResultSelection, APIRetainedResultAcquisition, APIRetainedResultPublication, APIReceivedRecords, APIToParent, APICredit, APIClosedCredit, APICompletion, ExecutionEpisodeYield):
    decision_source_type = APIJobTask
    decision_prompt_renderer = staticmethod(render_api_launch_prompt)
    binding_path = 'hpc_work_planning/execution_job_submission/api_job_execution'
    commissioning_parent = 'hpc_work_planning/execution_job_submission'
    roles = ('launch_api',)
    entry_roles = ()
    replaces_default_instructions = True

