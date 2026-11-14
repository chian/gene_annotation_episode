from __future__ import annotations
'Bounded HMMER operations inside the shared execution episode.\n\nThis adapter contains no polling, retry, model or episode loop. API targets use\n``digest(original API assignment)`` as request_sha256; the HTTP request, submitted\nFASTA bytes and parsed sequence each retain their own distinct frozen identities.\nNative monitoring has independent observation custody and never changes launch\nreceipts, completion proofs or its closed controller history.\n'
import asyncio
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import uuid
from gene_annotation_episode.episodic_workflow.root.a104.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError, identity, validate_schema
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest, validate_api_assignment, validate_target
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_records import validate_completion_proof
from gene_annotation_episode.episodic_workflow.root.a104.provider_jobs import HMMER_IDENTITY_VERSION, validate_remote_identity
PROVIDER = 'episode.api_hmmer_handoff'
VERSION = 'api_hmmer_execution_v1'
HANDOFF_VERSION = 'api_hmmer_handoff_v1'
RESULT_DESCRIPTION = 'Acquire exactly the assigned HMMER result page from the original API handoff; retain native scores, domain alignments and separately defined numerical correspondence measurements.'

def _now():
    return datetime.now(timezone.utc).isoformat()

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def hmmer_operation_catalog(role):
    """Declared contracts without an invented query, target or service call."""
    if role not in {'launch_api', 'results'}:
        raise ValueError('api_execution_role_required')
    descriptions = {'api.hmmer.result': RESULT_DESCRIPTION} if role == 'results' else {'api.hmmer.databases': 'Read one current served database inventory; no job is selected or submitted.', 'api.hmmer.prepare': 'Freeze the assigned query sequence, submitted FASTA and exact request identities.', 'api.hmmer.submit': 'Commit intent and submit the original assigned search once; uncertain submissions never repeat.', 'api.hmmer.status': 'Read the original submitted search with one status request.', 'api.hmmer.check_handoff': 'Read one status response and validate a usable original monitoring/results handoff.'}
    return [{'name': name, 'description': description, 'input_schema': _object({})} for name, description in descriptions.items()]

def _envelope(key, *, status='completed', result=None, refs=(), feedback=None):
    return {'status': status, 'operation_ref': identity('api_operation', {'key': key}), 'record_refs': list(refs), 'changed_record_refs': list(refs), 'result': result, 'feedback': feedback}

def _native_status(snapshot, request, remote_id):
    try:
        native = json.loads(snapshot.content)
        canonical(native)
        task = native.get('task') if isinstance(native, dict) else None
        if not isinstance(native, dict) or (task is not None and (not isinstance(task, dict) or not isinstance(task.get('status', 'UNKNOWN'), str))):
            raise ValueError('status_object_required')
    except (ValueError, TypeError, UnicodeError) as error:
        raise AcquisitionError('provider_status_response_invalid', snapshot=snapshot, phase='status_response') from error
    try:
        validate_remote_identity(native, request, remote_id)
    except AcquisitionError as error:
        error.snapshot = snapshot
        raise
    status = (task or {}).get('status', 'UNKNOWN')
    states = {'PENDING': 'submitted', 'RECEIVED': 'submitted', 'STARTED': 'running', 'RETRY': 'running', 'SUCCESS': 'completed', 'FAILURE': 'failed', 'REVOKED': 'failed'}
    return (native, status, states.get(status, 'unknown'))
__all__ = ['AcquisitionError', 'ContractError', 'HANDOFF_VERSION', 'HMMER_IDENTITY_VERSION', 'PROVIDER', 'Path', 'RESULT_DESCRIPTION', 'SourceSnapshot', 'VERSION', '_envelope', '_native_status', '_now', '_object', 'asdict', 'asyncio', 'canonical', 'datetime', 'digest', 'hashlib', 'hmmer_operation_catalog', 'identity', 'json', 'math', 'plain', 'replace', 'timezone', 'uuid', 'validate_api_assignment', 'validate_completion_proof', 'validate_form', 'validate_remote_identity', 'validate_schema', 'validate_target']
