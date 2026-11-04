"""Typed native progress without episode return or acknowledgment identities."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import uuid

from .communication import plain
from .domain import ContractError, canonical, obj, validate_schema
from .homology_jobs import STATUS_SCHEMA


JOB_STATUS_VERSION = 'job_execution_status_v1'
JOB_STATUS_SCHEMA = obj({
    'version': {'const': JOB_STATUS_VERSION},
    'handle': {'type': 'string', 'minLength': 1},
    'observed_at': {'type': 'string', 'minLength': 1},
    'lifecycle_state': {'type': ['string', 'null'],
                        'enum': ['pending', 'executing', 'returned', None]},
    'result_available': {'type': 'boolean'},
    'native': deepcopy(STATUS_SCHEMA),
})
_LIFECYCLE = {'not_submitted': 'pending', 'prepared': 'pending',
              'starting': 'executing', 'running': 'executing', 'returned': 'returned',
              'submission_unconfirmed': None, 'execution_unknown': None}

EXTERNAL_JOB_STATUS_VERSION = 'external_job_execution_status_v1'
_EXTERNAL_STATES = ('PENDING', 'RECEIVED', 'STARTED', 'RETRY',
                    'SUCCESS', 'FAILURE', 'REVOKED')
_TEXT = {'type': 'string', 'minLength': 1}
EXTERNAL_JOB_STATUS_SCHEMA = obj({
    'version': {'const': EXTERNAL_JOB_STATUS_VERSION},
    'handle': _TEXT, 'observed_at': _TEXT,
    'lifecycle_state': {'enum': ['pending', 'executing', 'returned', None]},
    'result_available': {'type': 'boolean'},
    'provider': {'const': 'hmmer'}, 'registry_ref': _TEXT,
    'request_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
    'remote_id': _TEXT, 'native_state': {'enum': list(_EXTERNAL_STATES)},
    'provider_chronology': {'const': 'unknown'},
    'status_receipt_ref': _TEXT, 'status_snapshot_ref': _TEXT,
    'result_cached': {'type': 'boolean'},
    'result_snapshot_refs': {'type': 'array', 'items': _TEXT, 'uniqueItems': True},
    'lifecycle_basis': {'enum': ['provider_status', 'validated_result_capture']},
    'failure_code': {'enum': [None, 'remote_job_failed']},
})


def validate_external_job_status(value):
    """Validate saved external facts, without querying the external service."""
    try:
        value = json.loads(canonical(plain(value)))
        validate_schema(value, EXTERNAL_JOB_STATUS_SCHEMA)
        stamp = datetime.fromisoformat(value['observed_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
            raise ValueError('UTC timestamp required')
        if str(uuid.UUID(value['remote_id'])) != value['remote_id']:
            raise ValueError('canonical UUID required')
    except (ValueError, TypeError, AttributeError) as error:
        raise ContractError('invalid_external_job_progress_status') from error
    state, cached = value['native_state'], value['result_cached']
    lifecycle = ('returned' if cached or state in {'SUCCESS', 'FAILURE', 'REVOKED'}
                 else 'executing' if state == 'STARTED' else 'pending')
    if (value['lifecycle_state'] != lifecycle
            or value['result_available'] != (cached or state == 'SUCCESS')
            or cached != bool(value['result_snapshot_refs'])
            or value['lifecycle_basis'] != ('validated_result_capture' if cached else 'provider_status')
            or value['failure_code'] != ('remote_job_failed' if state in {'FAILURE', 'REVOKED'} else None)):
        raise ContractError('external_job_progress_status_relationship_mismatch')
    return value


def external_job_status(handle, receipt):
    """Project an actual successful status receipt, retaining its original time."""
    receipt = plain(receipt)
    if (receipt.get('version') != 'public_search_operation_v1'
            or receipt.get('operation') != 'status'
            or receipt.get('outcome') != 'completed' or receipt.get('failure') is not None
            or receipt.get('job_ref') != handle):
        raise ContractError('invalid_external_job_progress_receipt')
    state, cached = receipt['state'], receipt['result_cached']
    return validate_external_job_status({
        'version': EXTERNAL_JOB_STATUS_VERSION, 'handle': handle,
        'observed_at': receipt['observed_at'],
        'lifecycle_state': ('returned' if cached or state in {'SUCCESS', 'FAILURE', 'REVOKED'}
                            else 'executing' if state == 'STARTED' else 'pending'),
        'result_available': cached or state == 'SUCCESS',
        'provider': receipt['provider'], 'registry_ref': receipt['registry_ref'],
        'request_sha256': receipt['request_sha256'], 'remote_id': receipt['remote_id'],
        'native_state': state, 'provider_chronology': receipt['provider_chronology'],
        'status_receipt_ref': receipt['receipt_ref'], 'status_snapshot_ref': receipt['snapshot_ref'],
        'result_cached': cached, 'result_snapshot_refs': receipt['result_snapshot_refs'],
        'lifecycle_basis': 'validated_result_capture' if cached else 'provider_status',
        'failure_code': 'remote_job_failed' if state in {'FAILURE', 'REVOKED'} else None})


def validate_job_status(value):
    """Validate a recorded native observation without acquiring any new facts."""
    try:
        value = json.loads(canonical(plain(value)))
        validate_schema(value, JOB_STATUS_SCHEMA)
        stamp = datetime.fromisoformat(value['observed_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
            raise ValueError('UTC timestamp required')
    except (ValueError, TypeError, AttributeError) as error:
        raise ContractError('invalid_job_progress_status') from error
    native = value['native']
    if (value['handle'] != native['job_ref']
            or value['lifecycle_state'] != _LIFECYCLE[native['state']]
            or value['result_available'] != any(row['available'] for row in native['outputs'])
            or native['outcome'] in {'succeeded', 'failed'} and native['state'] != 'returned'):
        raise ContractError('job_progress_status_relationship_mismatch')
    if len({row['role'] for row in native['outputs']}) != len(native['outputs']):
        raise ContractError('job_progress_output_identity_conflict')
    for row in native['outputs']:
        if ((not row['available'] and (row['bytes'] is not None or row['writer_closed']))
                or row['available'] and row['bytes'] is None
                or row['writer_closed'] and native['state'] != 'returned'):
            raise ContractError('job_progress_output_relationship_mismatch')
    return value


def job_status(handle, native_status, *, observed_at):
    """Project only the lifecycle and availability supported by actual status."""
    native = plain(native_status)
    try:
        lifecycle = _LIFECYCLE[native['state']]
        available = any(row['available'] for row in native['outputs'])
    except (TypeError, KeyError) as error:
        raise ContractError('invalid_job_progress_status') from error
    return validate_job_status({'version': JOB_STATUS_VERSION, 'handle': handle,
        'observed_at': observed_at, 'lifecycle_state': lifecycle,
        'result_available': available, 'native': native})


__all__ = ['JOB_STATUS_VERSION', 'JOB_STATUS_SCHEMA', 'job_status', 'validate_job_status',
           'EXTERNAL_JOB_STATUS_VERSION', 'EXTERNAL_JOB_STATUS_SCHEMA',
           'external_job_status', 'validate_external_job_status']
