"""Predefined private A107 Launch implementation"""
from __future__ import annotations
from .presentation import present_context
from .from_child_api_job_execution import receive_report as receive_api_report
from .from_child_local_job_execution import receive_report as receive_local_report
from .from_child_hpc_job_execution import receive_report as receive_hpc_report
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
from gene_annotation_episode.episodic_workflow.root.a107.scientific_process.execution_job_submission.received_api_reports import received_api_reports as _received_api_reports
from gene_annotation_episode.episodic_workflow.root.a107.scientific_process.execution_job_submission.received_execution_information import received_execution_information as _received_execution_information
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
from .configuration import LaunchConfiguration
from .binding_record import LaunchBindingRecord
from .context_receipts import LaunchContextReceipts
from .input_versions import LaunchInputVersions
from .received_result_records import NATIVE_RESULT_ORIGIN
from .received_result_records import RESULT_PROVIDER
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_state import _immutable
from .action_outcome import _outcome
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_acquisition import is_native_rna_structure_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_acquisition import is_standard_blast_database_target
import json
import math
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
from .launch_state import LaunchLaunchState
from .resource_information import LaunchResourceInformation
from .goal import LaunchGoal
from .completion import LaunchCompletion
from .internal_summary import LaunchInternalSummary
from .work_operations import LaunchWorkOperations
from .handoff_receipts import LaunchHandoffReceipts
from .from_parent import LaunchFromParent
from .to_parent import LaunchToParent
from .credit import LaunchCredit
from importlib import import_module
from .yield_estimator import ExecutionEpisodeYield
from .task import LaunchTask
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import A107BlastExecution
from .binding_roles import KINDS
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain

class ExecutionEpisode(LaunchConfiguration, LaunchBindingRecord, LaunchContextReceipts, LaunchInputVersions, LaunchLaunchState, LaunchResourceInformation, LaunchCompletion, LaunchGoal, LaunchInternalSummary, LaunchWorkOperations, LaunchHandoffReceipts, LaunchFromParent, LaunchToParent, LaunchCredit, ExecutionEpisodeYield, A107BlastExecution):
    decision_prompt_renderer = staticmethod(present_context)
    received_execution_information = staticmethod(_received_execution_information)
    received_execution_requires_authority = True
    received_api_reports = staticmethod(_received_api_reports)
    received_api_requires_authority = True
    initial_information_requires_authority = True
    initial_information_consumer = staticmethod(_private_initial_information)
    binding_path = 'scientific_process/execution_job_submission'
    commissioning_parent = 'scientific_process'
    roles = ('launch',)
    entry_roles = ('launch',)
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
    decision_source_type = LaunchTask

    def child_roles(self, role):
        return tuple(ROLE_KINDS)

    def allowed_children(self, parent, caller_capabilities):
        assignment = self._launch(plain(parent.assignment))
        return tuple((role for role, kind in ROLE_KINDS.items() if any((KINDS[configuration['kind']] == kind and self._permitted(assignment, resource_id) for resource_id, configuration in self.resources.items()))))

    def permitted_common_actions(self, context):
        if any((role == 'hpc' for role, _ in context.path)):
            return ('tool', 'child', 'redeliver_report')
        return ('tool', 'reason', 'child', 'wait', 'redeliver_report')
    _validate_request = _validate_request
    fact_sources = fact_sources
    resolve = resolve
    _infernal_reference_source = staticmethod(_infernal_reference_source)

    def prepare_child_request(self, parent, role, assignment):
        if role == 'launch_api':
            return assignment
        if role == 'launch_local':
            return assignment
        if role == 'launch_hpc':
            return assignment
        return assignment

    def execution_child_report_receiver(self, role):
        if role == 'launch_api':
            return receive_api_report
        if role == 'launch_local':
            return receive_local_report
        if role == 'launch_hpc':
            return receive_hpc_report
        return None

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
