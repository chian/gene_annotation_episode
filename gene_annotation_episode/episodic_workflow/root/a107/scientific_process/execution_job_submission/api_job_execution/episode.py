from __future__ import annotations
from .task import NativeTask
from gene_annotation_episode.episodic_workflow.root.a107.scientific_process.execution_job_submission.api_job_execution.received_execution_information import received_execution_information as _received_execution_information
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _appservice_sources, _comparison_selector, _delegate, _expression_nmf_reference_access, _has_appservice, _has_rfam, _has_uniprot, _masking_reference_access, _practical_context, _read_result, _result_directory, _selection, _selector, _utility_reference_access, _validate_result_body, _windows, resolve_received_execution_reference
from gene_annotation_episode.episodic_workflow.root.a107.scientific_process.execution_job_submission.api_job_execution.received_api_reports import received_api_reports as _received_api_reports
from .initial_information import initial_information as _private_initial_information
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_resource_information import resource_information_for_id, execution_capabilities, execution_capability_information
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import received_execution_target, retained_expression_nmf_target, is_expression_nmf_selector, retained_masking_target, is_masking_selector, retained_utility_target, is_utility_selector, selected_result_action
from .execution_contracts import A107BlastExecution, ASSIGNMENT_SCHEMA, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, GENERIC_REQUESTED_JOB_SCHEMA, KINDS, LOCAL_FILE_SOURCE_RECEIPT_VERSION, LocalFileSourceResults, NATIVE_RESULT_ORIGIN, NATIVE_SELECTOR_SCHEMA, Path, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, VERSION, _immutable, _read, base64, canonical, checked, confined, deepcopy, digest, hashlib, homology_api_contracts, identity, install_preparation_result_readers, install_primary_result_readers, is_file_source_selector, is_native_blast_database_target, is_native_blast_masking_target, is_native_blast_target, is_native_blast_utility_target, is_native_hmmer_preparation_target, is_native_hmmer_target, is_native_infernal_preparation_target, is_native_infernal_target, is_native_rna_structure_target, is_standard_blast_database_target, json, math, native_operation_contracts, native_result_operation_catalog, plain, preparation_job_schemas, preparation_operation_contracts, requested_job_schemas, validate_assignment, validate_preparation_resource_binding, validate_primary_resource_bindings
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_operation_information import operation_catalog
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_result_contract import RESULTS_SCHEMA
from .credit import ExecutionEpisodeCredit
from importlib import import_module as _import_module
from .from_parent import NativeParentRequests
from .to_parent import NativeParentReturns
from .goal import NativeGoal
from .presentation import present_context as _native_present_context
from .science import NativeScienceInputs
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _validate_request
import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a107.domain import identity
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical, checked, digest, obj
from gene_annotation_episode.episodic_workflow.root.a107.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_operations import confined
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_records import ASSIGNMENT_SCHEMA, validate_assignment, validate_completion_proof, GENERIC_REQUESTED_JOB_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a107.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.a107.scientific_process.execution_job_submission.api_job_execution.terminal_execution import TerminalExecutionBehavior
from gene_annotation_episode.episodic_workflow.root.a107.resource_records import INPUT_VERSION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_acquisition import is_native_hmmer_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_acquisition import is_native_blast_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_masking_acquisition import is_native_blast_masking_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_utility_acquisition import is_native_blast_utility_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_acquisition import is_standard_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_preparation_acquisition import is_native_hmmer_preparation_target
from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_acquisition import is_native_infernal_target
from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_acquisition import is_native_infernal_preparation_target
from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_acquisition import is_native_rna_structure_target
from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import LocalFileSourceResults, SELECTOR_SCHEMA as LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RECEIPT_VERSION as LOCAL_FILE_SOURCE_RECEIPT_VERSION, FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER, is_file_source_selector
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import A107BlastExecution, BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_RETURN_SOURCE, BLAST_GRADED_RETURN_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import validate_primary_resource_bindings, validate_preparation_resource_binding, install_primary_result_readers, install_preparation_result_readers, requested_job_schemas, preparation_job_schemas, native_operation_contracts, preparation_operation_contracts, homology_api_contracts, result_selector_conditions, launch_request_schema
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _infernal_reference_source, fact_sources, resolve
from .execution_contracts import BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, LOCAL_FILE_SOURCE_PROVIDER, NATIVE_RESULT_ORIGIN, PracticalReceiptInformation, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, deepcopy, is_native_blast_database_target, is_native_rna_structure_target, is_standard_blast_database_target, obj, plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_resource_information import execution_capability_information
from .execution_contracts import BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, KINDS, ROLE_KINDS, checked, deepcopy, is_native_blast_database_target, is_native_blast_target, is_native_hmmer_preparation_target, is_native_hmmer_target, is_native_infernal_preparation_target, is_native_infernal_target, is_native_rna_structure_target, is_standard_blast_database_target, native_result_operation_catalog, plain
from .execution_contracts import plain
from .execution_contracts import ROLE_KINDS, canonical, digest, json, plain, validate_completion_proof
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import resolve_received_execution_reference
from .execution_contracts import canonical, json, plain
from .execution_contracts import INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RESULTS_SCHEMA, ROLE_KINDS, SELECTION_SCHEMA, checked, deepcopy, is_file_source_selector, is_native_blast_database_target, is_native_rna_structure_target, is_standard_blast_database_target, launch_request_schema, obj, plain, result_selector_conditions
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_request_compatibility import results_assignment_schema as _compat_results_assignment_schema, launch_assignment_schema as _compat_launch_assignment_schema, prepare_launch_assignment as _compat_prepare_launch_assignment, prepare_results_assignment as _compat_prepare_results_assignment
from .execution_contracts import BLAST_GRADED_RETURN_SOURCE
from .execution_contracts import NATIVE_RESULT_ORIGIN
from .execution_contracts import ROLE_KINDS
from .execution_contracts import deepcopy
from .execution_contracts import validate_form
from .execution_contracts import ROLES, ROLE_KINDS, _CLOSED_CREDIT, canonical, digest, json, math, plain, validate_completion_proof
from gene_annotation_episode.episodic_workflow.root.a107.runtime import FACT_MEANINGS, FACT_SOURCES, Mapping, _plain, _references_in, json
from .configuration import NativeConfiguration
from .binding_record import NativeBindingRecord
from .from_parent import NativeParentRequests
from .to_parent import NativeParentReturns
from .science import NativeScienceInputs
from .credit import ExecutionEpisodeCredit
from .goal import NativeGoal
from .completion import NativeCompletion
from .received_records import NativeReceivedRecords
from .resource_information import NativeResourceInformation
from .state import NativeState
from .work_operations import NativeWorkOperations
from .internal_summary import NativeInternalSummary
from .yield_estimator import ExecutionEpisodeYield

class ExecutionEpisode(NativeConfiguration, NativeBindingRecord, NativeScienceInputs, NativeState, NativeWorkOperations, NativeInternalSummary, NativeResourceInformation, NativeReceivedRecords, NativeParentRequests, NativeParentReturns, NativeCompletion, NativeGoal, ExecutionEpisodeCredit, ExecutionEpisodeYield, A107BlastExecution):
    decision_prompt_renderer = staticmethod(_native_present_context)
    decision_source_type = NativeTask
    received_execution_information = staticmethod(_received_execution_information)
    received_execution_requires_authority = True
    received_api_reports = staticmethod(_received_api_reports)
    received_api_requires_authority = True
    initial_information_requires_authority = True
    initial_information_consumer = staticmethod(_private_initial_information)
    binding_path = 'scientific_process/execution_job_submission/api_job_execution'
    commissioning_parent = 'scientific_process/execution_job_submission'
    roles = ('launch_api',)
    entry_roles = ()
    replaces_default_instructions = True

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()

    def permitted_common_actions(self, context):
        assignment = self._validate_request(plain(context.assignment))
        if assignment['version'] == 'api_service_assignment_v1':
            return ('tool', 'wait')
        return ('tool',)
