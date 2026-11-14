"""Connect this predefined A103 Results task and its original custody/credit/yield responsibilities."""
from __future__ import annotations
from .execution_contracts import A103HomologyExecution, plain
from .configuration import ResultsConfiguration
from .result_completion import ResultsResultCompletion
from .closed_completion import ResultsClosedCompletion
from .initial_input_references import ResultsInitialInputReferences
from .received_report_facts import ResultsReceivedReportFacts
from .received_reference_custody import ResultsReceivedReferenceCustody
from .report_reference_access import ResultsReportReferenceAccess
from .selector_coverage_credit import ResultsSelectorCoverageCredit
from .selected_execution_context import ResultsSelectedExecutionContext
from .action_policy import ResultsActionPolicy
from .binding_record import ResultsBindingRecord
from .child_commissioning import ResultsChildCommissioning
from .from_parent import ResultsFromParent
from .goal import ResultsGoal
from .internal_summary import ResultsInternalSummary
from .resource_information import ResultsResourceInformation
from .parent_input_custody import ResultsParentInputCustody
from .retained_masking_reader import ResultsRetainedMaskingReader
from .retained_utility_reader import ResultsRetainedUtilityReader
from .saved_result_commission import ResultsSavedResultCommission
from .execution_state import ResultsExecutionState
from .acquisition_operations import ResultsAcquisitionOperations
from .result_selection import ResultsResultSelection
from .retained_result_acquisition import ResultsRetainedResultAcquisition
from .retained_result_publication import ResultsRetainedResultPublication
from .received_records import ResultsReceivedRecords
from .to_parent import ResultsToParent
from .credit import ResultsCredit
from .closed_credit import ResultsClosedCredit
from .completion import ResultsCompletion
from importlib import import_module as _import_module
ExecutionEpisodeYield = _import_module('.yield', __package__).ExecutionEpisodeYield
from .task import ResultsTask
from gene_annotation_episode.episodic_workflow.root.a103.scientific_process_prompt import render_selected_execution_prompt

class ExecutionEpisode(ResultsConfiguration, ResultsResultCompletion, ResultsClosedCompletion, ResultsInitialInputReferences, ResultsReceivedReportFacts, ResultsReceivedReferenceCustody, ResultsReportReferenceAccess, ResultsSelectorCoverageCredit, ResultsSelectedExecutionContext, ResultsActionPolicy, ResultsBindingRecord, ResultsChildCommissioning, ResultsFromParent, ResultsGoal, ResultsInternalSummary, ResultsResourceInformation, ResultsParentInputCustody, ResultsRetainedMaskingReader, ResultsRetainedUtilityReader, ResultsSavedResultCommission, ResultsExecutionState, ResultsAcquisitionOperations, ResultsResultSelection, ResultsRetainedResultAcquisition, ResultsRetainedResultPublication, ResultsReceivedRecords, ResultsToParent, ResultsCredit, ResultsClosedCredit, ResultsCompletion, ExecutionEpisodeYield, A103HomologyExecution):
    decision_source_type = ResultsTask
    decision_prompt_renderer = staticmethod(render_selected_execution_prompt)
    binding_path = 'scientific_process/hpc_work_planning/execution_result_acquisition'
    commissioning_parent = 'scientific_process/hpc_work_planning'
    roles = ('results',)
    entry_roles = ()
    replaces_default_instructions = True

