"""Private A110 Results owner"""
from __future__ import annotations
from .presentation import present_results_context
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _constraints
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _delegate
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _flux_balance_reference_access
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _flux_balance_selector
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _practical_context
from .initial_information import initial_information as _private_initial_information
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _read_result
from gene_annotation_episode.episodic_workflow.root.a110.scientific_process.hpc_work_planning.execution_result_acquisition.received_execution_information import received_execution_information as _received_execution_information
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _result_directory
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _retained_flux_balance_target
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _selected_result_action
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _selection
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _selector
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _target
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _validate_request
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _validate_result_body
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _windows
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_resource_information import execution_capabilities
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import fact_sources
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import resolve
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_resource_information import resource_information_for_id
from .configuration import ResultsConfiguration
from .binding_record import ResultsBindingRecord
from .goal import ResultsGoal
from .from_parent import ResultsFromParent
from .input_versions import ResultsInputVersions
from .saved_commission import ResultsSavedCommission
from .result_state import ResultsResultState
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical
import json
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from .native_target_state import ResultsNativeTargetState
from .resource_information import ResultsResourceInformation
from .instructions import ResultsInstructions
from .internal_summary import ResultsInternalSummary
from .work_operations import ResultsWorkOperations
from .native_file_acquisition import ResultsNativeFileAcquisition
from .result_publication import ResultsResultPublication
from .target_custody import ResultsTargetCustody
from .credit import ResultsCredit
from .completion import ResultsCompletion
from .received_launch_requests import ResultsReceivedLaunchRequests
from .receipt_selection import ResultsReceiptSelection
from .to_parent import ResultsToParent
from .closed_credit import ResultsClosedCredit
from importlib import import_module
ExecutionEpisodeYield = import_module('.yield', __package__).ExecutionEpisodeYield
from .task import ResultsTask

class ExecutionEpisode(ResultsConfiguration, ResultsBindingRecord, ResultsGoal, ResultsFromParent, ResultsInputVersions, ResultsSavedCommission, ResultsResultState, ResultsNativeTargetState, ResultsResourceInformation, ResultsInstructions, ResultsInternalSummary, ResultsWorkOperations, ResultsNativeFileAcquisition, ResultsResultPublication, ResultsTargetCustody, ResultsCredit, ResultsCompletion, ResultsReceivedLaunchRequests, ResultsReceiptSelection, ResultsToParent, ResultsClosedCredit, ExecutionEpisodeYield):
    decision_prompt_renderer = staticmethod(present_results_context)
    received_execution_information = staticmethod(_received_execution_information)
    received_execution_requires_authority = True
    initial_information_requires_authority = True
    initial_information_consumer = _private_initial_information
    binding_path = 'scientific_process/hpc_work_planning/execution_result_acquisition'
    commissioning_parent = 'scientific_process/hpc_work_planning'
    roles = ('results',)
    entry_roles = ()
    replaces_default_instructions = True
    _flux_balance_reference_access = _flux_balance_reference_access
    _flux_balance_selector = staticmethod(_flux_balance_selector)
    _retained_flux_balance_target = _retained_flux_balance_target
    _delegate = _delegate
    _practical_context = _practical_context
    _resource_information = resource_information_for_id
    capabilities = execution_capabilities
    _target = _target
    _selector = _selector
    _result_directory = _result_directory
    _windows = _windows
    _selected_result_action = _selected_result_action
    _validate_result_body = _validate_result_body
    _read_result = _read_result
    _selection = _selection
    decision_source_type = ResultsTask
    _validate_request = _validate_request
    _constraints = staticmethod(_constraints)
    fact_sources = fact_sources
    resolve = resolve
