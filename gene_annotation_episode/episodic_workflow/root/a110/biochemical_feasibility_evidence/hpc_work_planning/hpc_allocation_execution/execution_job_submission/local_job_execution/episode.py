from __future__ import annotations
from .task import NativeTask
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.local_job_execution.received_execution_information import received_execution_information as _received_execution_information
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _delegate, _flux_balance_reference_access, _flux_balance_selector, _practical_context, _read_result, _result_directory, _retained_flux_balance_target, _selected_result_action, _selection, _selector, _target, _validate_result_body, _windows, resolve_received_execution_reference
from .initial_information import initial_information as _private_initial_information
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_resource_information import resource_information_for_id, execution_capabilities, execution_capability_information
from .execution_contracts import ASSIGNMENT_SCHEMA, GENERIC_REQUESTED_JOB_SCHEMA, KINDS, LOCAL_FILE_SOURCE_RECEIPT_VERSION, LocalFileSourceResults, NATIVE_RESULT_ORIGIN, NATIVE_SELECTOR_SCHEMA, Path, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, VERSION, _immutable, _read, base64, canonical, checked, confined, deepcopy, digest, identity, is_file_source_selector, json, math, native_result_operation_catalog, plain, validate_assignment
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_operation_information import operation_catalog
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_result_contract import RESULTS_SCHEMA
from .credit import ExecutionEpisodeCredit
from importlib import import_module as _import_module
from .from_parent import NativeParentRequests
from .to_parent import NativeParentReturns
from .goal import NativeGoal
from .presentation import present_context as _native_present_context
from .science import NativeScienceInputs
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _constraints, _validate_request
import base64
from copy import deepcopy
import json
import math
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a110.domain import identity
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, checked, digest, obj
from gene_annotation_episode.episodic_workflow.root.a110.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_operations import confined
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import ASSIGNMENT_SCHEMA, validate_assignment, validate_completion_proof, GENERIC_REQUESTED_JOB_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a110.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.hpc_work_planning.hpc_allocation_execution.execution_job_submission.local_job_execution.terminal_execution import TerminalExecutionBehavior
from gene_annotation_episode.episodic_workflow.root.a110.resource_records import INPUT_VERSION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import LocalFileSourceResults, SELECTOR_SCHEMA as LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RECEIPT_VERSION as LOCAL_FILE_SOURCE_RECEIPT_VERSION, FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER, is_file_source_selector
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import fact_sources, resolve
from .execution_contracts import LOCAL_FILE_SOURCE_PROVIDER, NATIVE_RESULT_ORIGIN, PracticalReceiptInformation, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, deepcopy, obj, plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_resource_information import execution_capability_information
from .execution_contracts import KINDS, ROLE_KINDS, checked, deepcopy, native_result_operation_catalog, plain
from .execution_contracts import ROLE_KINDS, canonical, digest, json, plain, validate_completion_proof
from .execution_contracts import canonical, json, plain
from .execution_contracts import INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RESULTS_SCHEMA, ROLE_KINDS, SELECTION_SCHEMA, checked, deepcopy, is_file_source_selector, obj, plain
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_request_compatibility import results_assignment_schema as _compat_results_assignment_schema, launch_assignment_schema as _compat_launch_assignment_schema, prepare_launch_assignment as _compat_prepare_launch_assignment, prepare_results_assignment as _compat_prepare_results_assignment
from .execution_contracts import NATIVE_RESULT_ORIGIN
from .execution_contracts import ROLE_KINDS
from .execution_contracts import deepcopy
from .execution_contracts import plain
from .execution_contracts import validate_form
from .execution_contracts import ROLES, ROLE_KINDS, _CLOSED_CREDIT, canonical, digest, json, math, plain, validate_completion_proof
from gene_annotation_episode.episodic_workflow.root.a110.runtime import FACT_MEANINGS, FACT_SOURCES, Mapping, _plain, _references_in, json
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

class ExecutionEpisode(NativeConfiguration, NativeBindingRecord, NativeScienceInputs, NativeState, NativeWorkOperations, NativeInternalSummary, NativeResourceInformation, NativeReceivedRecords, NativeParentRequests, NativeParentReturns, NativeCompletion, NativeGoal, ExecutionEpisodeCredit, ExecutionEpisodeYield):
    decision_prompt_renderer = staticmethod(_native_present_context)
    decision_source_type = NativeTask
    received_execution_information = staticmethod(_received_execution_information)
    received_execution_requires_authority = True
    initial_information_requires_authority = True
    initial_information_consumer = staticmethod(_private_initial_information)
    binding_path = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution'
    commissioning_parent = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
    roles = ('launch_local',)
    entry_roles = ()
    replaces_default_instructions = True

    def child_roles(self, role):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()

    def permitted_common_actions(self, context):
        return ('tool',)
