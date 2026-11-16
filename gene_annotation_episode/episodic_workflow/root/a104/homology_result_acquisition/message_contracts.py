"""Scoped job-role bindings for the existing shared method_loop.

No production score, timing exchange rate, itinerary or private decision loop.
The caller owns resource/scoring configuration; the parent owns commissioning.
"""
from __future__ import annotations
from copy import copy, deepcopy
import json
import math
import sqlite3
import subprocess
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.a104.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.a104.communication import REFERENCE_FORMATS, ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a104.homology_jobs import HANDOFF_SCHEMA, SAMPLE_SCHEMA, STATUS_SCHEMA, HomologyJobs
from gene_annotation_episode.episodic_workflow.root.a104.homology_results import HomologyResults, NativePhmmerInput, recorded_coverage
from gene_annotation_episode.episodic_workflow.root.a104.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.a104.materials import artifact_path
from gene_annotation_episode.episodic_workflow.root.a104.homology_observation_schema import EXECUTION_OBSERVATION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a104.resource_estimation import recorded_estimate, recorded_forecasts, validate_recorded_estimates, report_source as resource_report_source
ROLES = ('job_results',)

def obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}

def reference(namespace, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': namespace}
CHECKED_STATUS_SCHEMA = obj({'checked_at_unix_seconds': {'type': 'number', 'minimum': 0}, **deepcopy(STATUS_SCHEMA['properties'])})
RESULT_PROGRESS_SCHEMA = obj({'snapshot_ref': reference('source'), 'query_ref': reference('subject'), 'execution_source_ref': reference('source'), 'native_source_ref': reference('source'), 'execution_context': {**obj({'job_ref': reference('homology_job'), 'registry_ref': reference('execution_registry')}), 'type': ['object', 'null']}, 'status': {'type': 'string', 'enum': ['available', 'unavailable']}, 'parsed_row_count': {'type': ['integer', 'null'], 'minimum': 0}, 'acquired_row_count': {'type': ['integer', 'null'], 'minimum': 0}, 'acquired_ordinal_intervals': {'type': ['array', 'null'], 'items': {'type': 'array', 'items': {'type': 'integer', 'minimum': 1}, 'minItems': 2, 'maxItems': 2}}, 'all_parsed_rows_acquired': {'type': ['boolean', 'null']}, 'parser_finished': {'type': ['boolean', 'null']}, 'native_error_count': {'type': ['integer', 'null'], 'minimum': 0}, 'parse_execution_failed': {'type': ['boolean', 'null']}, 'native_termination_seen': {'type': ['boolean', 'null']}, 'native_result_complete': {'type': ['boolean', 'null']}})

def _result_progress(value):
    """Project actual coverage facts without passing an unrestricted error body."""
    return {key: value['parse_execution_failure'] is not None if key == 'parse_execution_failed' else deepcopy(value[key]) for key in RESULT_PROGRESS_SCHEMA['properties']}

def _binding(callback):
    implementation = callback if hasattr(callback, '__qualname__') else type(callback)
    return implementation.__module__ + '.' + implementation.__qualname__
