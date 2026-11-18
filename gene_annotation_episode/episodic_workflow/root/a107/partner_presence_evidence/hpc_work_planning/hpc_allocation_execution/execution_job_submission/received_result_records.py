"""Private A107 received result records"""
from __future__ import annotations
from .schema_fields import FILE_LIMIT
from .schema_fields import LIMIT
from .schema_fields import OFFSET
from .schema_fields import TEXT
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import obj
RESULTS_VERSION = 'execution_results_assignment_v1'
RESULT_PROVIDER = 'episode.execution_result'
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified', 'window_consistency': 'separate_reads_no_atomic_file_snapshot', 'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
NATIVE_RESULT_ORIGIN_SCHEMA = obj({key: {'type': 'string', 'enum': [value]} for key, value in NATIVE_RESULT_ORIGIN.items()})
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT}, 'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])

def native_result_operation_catalog():
    """Actual local/PBS acquisition operators; execution still requires a target."""
    return [{'name': 'execution.results.status', 'description': 'Observe the exact handed-off physical attempt once.', 'input_schema': obj({})}, {'name': 'execution.results.collect', 'description': 'Observe the original attempt and acquire bounded first windows of the requested paths.', 'input_schema': obj({})}, {'name': 'execution.results.read', 'description': 'Acquire one selected bounded byte window within the original requested paths and interval.', 'input_schema': obj({'path': TEXT, 'offset': OFFSET, 'limit': FILE_LIMIT})}]
