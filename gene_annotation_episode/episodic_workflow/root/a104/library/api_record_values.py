from __future__ import annotations
'Selected API operations in the existing episode loop, across real services.\n\nThis module records calls and qualifies their handoffs and acquisitions. Service\nimplementations supply individual native operations; neither layer owns a model\nloop, polling schedule, retry decision or scientific interpretation.\n'
import asyncio
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a104.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.a104.api_error_feedback import api_error_feedback, api_error_response
from gene_annotation_episode.episodic_workflow.root.a104.library.hmmer_record_access import HMMERRecordAccess as HMMERAPIExecution
from gene_annotation_episode.episodic_workflow.root.a104.library.hmmer_record_values import PROVIDER as LEGACY_PROVIDER
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError, identity, validate_schema
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import API_ASSIGNMENT_SCHEMA, canonical, checked, digest, validate_api_assignment, validate_target
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_records import validate_completion_proof
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable, _read
PROVIDER = 'episode.api_service_handoff'
VERSION = 'api_service_execution_v1'
HANDOFF_VERSION = 'api_service_handoff_v1'
EVENT_FIELDS = {'kind', 'state', 'native_handle', 'handoff_ready', 'result_available', 'facts', 'failure_code'}
STATES = {'submitted', 'running', 'completed', 'failed', 'unknown'}

def _now():
    return datetime.now(timezone.utc).isoformat()

def _outcome(key, result=None, *, refs=(), status='completed', code=None, **feedback):
    return {'status': status, 'operation_ref': identity('api_operation', {'key': key}), 'record_refs': list(refs), 'changed_record_refs': list(refs), 'result': result, 'feedback': None if code is None else {'category': 'provider', 'code': code, **feedback}}
__all__ = ['API_ASSIGNMENT_SCHEMA', 'AcquisitionError', 'ContractError', 'EVENT_FIELDS', 'HANDOFF_VERSION', 'HMMERAPIExecution', 'LEGACY_PROVIDER', 'PROVIDER', 'Path', 'STATES', 'SourceSnapshot', 'VERSION', '_immutable', '_now', '_outcome', '_read', 'api_error_feedback', 'api_error_response', 'asdict', 'asyncio', 'canonical', 'checked', 'datetime', 'deepcopy', 'digest', 'fcntl', 'hashlib', 'identity', 'json', 'math', 'plain', 'timezone', 'validate_api_assignment', 'validate_completion_proof', 'validate_schema', 'validate_target']
