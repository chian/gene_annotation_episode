"""Private A107 Results owner"""
from __future__ import annotations
from .presentation import present_results_context
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _appservice_sources
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _comparison_selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _delegate
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _expression_nmf_reference_access
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _has_appservice
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _has_rfam
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _has_uniprot
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _infernal_reference_source
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _masking_reference_access
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _practical_context
from .initial_information import initial_information as _private_initial_information
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _read_result
from gene_annotation_episode.episodic_workflow.root.a107.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.received_api_reports import received_api_reports as _received_api_reports
from gene_annotation_episode.episodic_workflow.root.a107.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.received_execution_information import received_execution_information as _received_execution_information
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _result_directory
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _selection
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _utility_reference_access
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _validate_request
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _validate_result_body
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _windows
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_resource_information import execution_capabilities
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import fact_sources
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import is_expression_nmf_selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import is_masking_selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import is_utility_selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import received_execution_target
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import resolve
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_resource_information import resource_information_for_id
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import retained_expression_nmf_target
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import retained_masking_target
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import retained_utility_target
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import selected_result_action
from .configuration import ResultsConfiguration
from .binding_record import ResultsBindingRecord
from .goal import ResultsGoal
from .from_parent import ResultsFromParent
from .input_versions import ResultsInputVersions
from .saved_commission import ResultsSavedCommission
from .result_state import ResultsResultState
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical
import json
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
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
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import A107BlastExecution
from .task import ResultsTask

class ExecutionEpisode(ResultsConfiguration, ResultsBindingRecord, ResultsGoal, ResultsFromParent, ResultsInputVersions, ResultsSavedCommission, ResultsResultState, ResultsNativeTargetState, ResultsResourceInformation, ResultsInstructions, ResultsInternalSummary, ResultsWorkOperations, ResultsNativeFileAcquisition, ResultsResultPublication, ResultsTargetCustody, ResultsCredit, ResultsCompletion, ResultsReceivedLaunchRequests, ResultsReceiptSelection, ResultsToParent, ResultsClosedCredit, ExecutionEpisodeYield, A107BlastExecution):
    decision_prompt_renderer = staticmethod(present_results_context)
    received_execution_information = staticmethod(_received_execution_information)
    received_execution_requires_authority = True
    received_api_reports = staticmethod(_received_api_reports)
    received_api_requires_authority = True
    initial_information_requires_authority = True
    initial_information_consumer = _private_initial_information
    binding_path = 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition'
    commissioning_parent = 'scientific_process/hpc_work_planning/hpc_allocation_execution'
    roles = ('results',)
    entry_roles = ()
    replaces_default_instructions = True
    _masking_selector = staticmethod(is_masking_selector)
    _retained_masking_target = retained_masking_target
    _masking_reference_access = _masking_reference_access
    _utility_selector = staticmethod(is_utility_selector)
    _retained_utility_target = retained_utility_target
    _utility_reference_access = _utility_reference_access
    _expression_nmf_reference_access = _expression_nmf_reference_access
    _expression_nmf_selector = staticmethod(is_expression_nmf_selector)
    _retained_expression_nmf_target = retained_expression_nmf_target
    _delegate = _delegate
    _practical_context = _practical_context
    _resource_information = resource_information_for_id
    capabilities = execution_capabilities
    _target = received_execution_target
    _comparison_selector = staticmethod(_comparison_selector)
    _selector = _selector
    _result_directory = _result_directory
    _windows = _windows
    _selected_result_action = selected_result_action
    _validate_result_body = _validate_result_body
    _read_result = _read_result
    _selection = _selection
    _has_rfam = _has_rfam
    _has_appservice = _has_appservice
    _has_uniprot = _has_uniprot
    _appservice_sources = staticmethod(_appservice_sources)
    decision_source_type = ResultsTask
    _validate_request = _validate_request
    fact_sources = fact_sources
    resolve = resolve
    _infernal_reference_source = staticmethod(_infernal_reference_source)
