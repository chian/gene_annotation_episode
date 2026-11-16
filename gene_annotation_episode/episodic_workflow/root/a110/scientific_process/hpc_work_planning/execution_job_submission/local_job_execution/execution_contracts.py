"""A110 flux balance launch and result execution.

The binding routes a selected concrete assignment. Resource operations and
result reads contain no model, resource selection or investigation loop.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _constraints, _validate_request
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_result_contract import RESULTS_SCHEMA
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
from gene_annotation_episode.episodic_workflow.root.a110.scientific_process.hpc_work_planning.execution_job_submission.local_job_execution.terminal_execution import TerminalExecutionBehavior
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_operation_information import operation_catalog
from gene_annotation_episode.episodic_workflow.root.a110.resource_records import INPUT_VERSION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import LocalFileSourceResults, SELECTOR_SCHEMA as LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RECEIPT_VERSION as LOCAL_FILE_SOURCE_RECEIPT_VERSION, FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER, is_file_source_selector
VERSION = 'execution_episode_v1'
LAUNCH_VERSION = 'execution_launch_assignment_v1'
RESULTS_VERSION = 'execution_results_assignment_v1'
RESULT_PROVIDER = 'episode.execution_result'
_CLOSED_CREDIT = 'execution_closed_operational_credit_v1'
ROLES = ('launch', 'launch_local', 'launch_hpc', 'results')
KINDS = {'local': 'local', 'pbs_ssh': 'hpc'}
ROLE_KINDS = {'launch_local': 'local', 'launch_hpc': 'hpc'}
TEXT = {'type': 'string', 'minLength': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}
FILE_LIMIT = {**LIMIT, 'maximum': 1024 * 1024}
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified', 'window_consistency': 'separate_reads_no_atomic_file_snapshot', 'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
NATIVE_RESULT_ORIGIN_SCHEMA = obj({key: {'type': 'string', 'enum': [value]} for key, value in NATIVE_RESULT_ORIGIN.items()})
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT}, 'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])

def native_result_operation_catalog():
    """Actual local/PBS acquisition operators; execution still requires a target."""
    return [{'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.', 'input_schema': obj({})}, {'name': 'execution.results.collect', 'description': 'Observe the original attempt and acquire bounded first windows of the requested paths.', 'input_schema': obj({})}, {'name': 'execution.results.read', 'description': 'Acquire one selected bounded byte window within the original requested paths and interval.', 'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': FILE_LIMIT})}]
