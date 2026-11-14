"""Private launch_local episode behavior for A102."""
from __future__ import annotations
from .contracts import ASSIGNMENT_SCHEMA, FILE_LIMIT, GENERIC_REQUESTED_JOB_SCHEMA, INPUT_VERSION_SCHEMA, KINDS, LAUNCH_VERSION, LIMIT, LOCAL_FILE_SOURCE_PROVIDER, LOCAL_FILE_SOURCE_RECEIPT_VERSION, LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, LocalFileSourceResults, NATIVE_RESULT_ORIGIN, NATIVE_RESULT_ORIGIN_SCHEMA, NATIVE_SELECTOR_SCHEMA, OFFSET, Path, PracticalReceiptInformation, RESULTS_SCHEMA, RESULTS_VERSION, RESULT_PROVIDER, ROLES, ROLE_KINDS, SELECTION_SCHEMA, TEXT, TerminalExecutionBehavior, VERSION, _AXIS_DIRECTORY, _CLOSED_CREDIT, _binding_source_bytes, _immutable, _outcome, _read, base64, canonical, checked, confined, deepcopy, digest, hashlib, identity, is_file_source_selector, is_native_protein_structure_target, json, launch_operation_catalog, math, native_operation_contracts, native_result_operation_catalog, obj, operation_catalog, plain, requested_job_schemas, validate_assignment, validate_completion_proof, validate_form, validate_primary_resource_bindings
from .decision_presentation import present_native_task
from .task import NativeTask
from .goal import NativeGoal
from .result_records import ExecutionResultRecords
from .child_eligibility import NativeChildEligibility
from .operations import NativeOperations
from .internal_summary import NativeSummary
from .to_parent import NativeReport
from .received_information import ReceivedExecutionInformation
from .from_parent import NativeAssignment
from .credit import ExecutionEpisodeCredit
from importlib import import_module as _import_module
ExecutionEpisodeYield = _import_module('.yield', __package__).ExecutionEpisodeYield

from .configuration import NativeConfiguration

from .binding_record import NativeBindingRecord

from .retained_protein_reader import NativeRetainedProteinReader

from .action_policy import NativeActionPolicy

class ExecutionEpisode(NativeActionPolicy, NativeRetainedProteinReader, NativeBindingRecord, NativeConfiguration, NativeAssignment, ReceivedExecutionInformation, NativeReport, ExecutionEpisodeCredit, ExecutionEpisodeYield, NativeSummary, NativeOperations, NativeChildEligibility, ExecutionResultRecords, NativeGoal):
    binding_path = 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution'
    commissioning_parent = 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission'
    roles = ('launch_local',)
    decision_source_type = NativeTask
    decision_prompt_renderer = staticmethod(present_native_task)
    entry_roles = ()
    replaces_default_instructions = True

