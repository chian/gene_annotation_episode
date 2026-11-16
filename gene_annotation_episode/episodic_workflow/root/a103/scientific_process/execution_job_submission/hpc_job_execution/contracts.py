"""One explicit launch family for the shared episode loop.

The binding routes a selected concrete assignment. Resource operations and
result reads contain no model, resource selection or investigation loop.
"""
from __future__ import annotations
import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a103.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a103.domain import identity
from gene_annotation_episode.episodic_workflow.root.a103.execution_contracts import canonical, checked, digest, obj
from gene_annotation_episode.episodic_workflow.root.a103.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a103.practical_execution_operations import confined
from gene_annotation_episode.episodic_workflow.root.a103.practical_execution_records import ASSIGNMENT_SCHEMA, validate_assignment, validate_completion_proof, GENERIC_REQUESTED_JOB_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a103.practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a103.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.a103.scientific_process.execution_job_submission.hpc_job_execution.terminal_execution import TerminalExecutionBehavior
from .terminal_contracts import operation_catalog
from gene_annotation_episode.episodic_workflow.root.a103.resource_records import INPUT_VERSION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a103.native_hmmer_acquisition import is_native_hmmer_target
from gene_annotation_episode.episodic_workflow.root.a103.native_blast_acquisition import is_native_blast_target
from gene_annotation_episode.episodic_workflow.root.a103.native_blast_masking_acquisition import is_native_blast_masking_target
from gene_annotation_episode.episodic_workflow.root.a103.native_blast_utility_acquisition import is_native_blast_utility_target
from gene_annotation_episode.episodic_workflow.root.a103.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a103.native_blast_standard_database_acquisition import is_standard_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a103.native_hmmer_preparation_acquisition import is_native_hmmer_preparation_target
from gene_annotation_episode.episodic_workflow.root.a103.local_file_capture_results import LocalFileSourceResults, SELECTOR_SCHEMA as LOCAL_FILE_SOURCE_SELECTOR_SCHEMA, RECEIPT_VERSION as LOCAL_FILE_SOURCE_RECEIPT_VERSION, FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER, is_file_source_selector
from gene_annotation_episode.episodic_workflow.root.a103.a103_homology_execution import A103HomologyExecution, BLAST_GRADED_REQUEST_VERSION, BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_RETURN_SOURCE, BLAST_GRADED_RETURN_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a103.a103_execution_bindings import validate_primary_resource_bindings, validate_preparation_resource_binding, install_primary_result_readers, install_preparation_result_readers, requested_job_schemas, preparation_job_schemas, native_operation_contracts, preparation_operation_contracts, homology_api_contracts, result_selector_conditions, launch_request_schema
VERSION = 'execution_episode_v1'
LAUNCH_VERSION = 'execution_launch_assignment_v1'
RESULTS_VERSION = 'execution_results_assignment_v1'
RESULT_PROVIDER = 'episode.execution_result'
_CLOSED_CREDIT = 'execution_closed_operational_credit_v1'
ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
ROLE_KINDS = {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}
TEXT = {'type': 'string', 'minLength': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}
FILE_LIMIT = {**LIMIT, 'maximum': 1024 * 1024}
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified', 'window_consistency': 'separate_reads_no_atomic_file_snapshot', 'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
NATIVE_RESULT_ORIGIN_SCHEMA = obj({key: {'type': 'string', 'enum': [value]} for key, value in NATIVE_RESULT_ORIGIN.items()})
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT, 'selector': {'type': 'object'}})
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT}, 'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])

def launch_operation_catalog():
    """Declared launch operations, without a target/resource observation."""
    return [{'name': 'execution.capabilities', 'description': 'Read the actual caller-bound resource configuration and already recorded inventory; no discovery or selection.', 'input_schema': obj({})}]

def native_result_operation_catalog():
    """Actual local/PBS acquisition operators; execution still requires a target."""
    return [{'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.', 'input_schema': obj({})}, {'name': 'execution.results.collect', 'description': 'Observe the original attempt and acquire bounded first windows of the requested paths.', 'input_schema': obj({})}, {'name': 'execution.results.read', 'description': 'Acquire one selected bounded byte window within the original requested paths and interval.', 'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': FILE_LIMIT})}]

def _outcome(result=None, *, references=(), code=None):
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references), 'changed_record_refs': list(references), 'result': result, 'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}
