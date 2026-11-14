"""Export physical service-exit receipts to the shared durable event ledger.

Bindings preserve the selecting episode and actual caller resource. This bridge
never polls execution, selects work, composes a report or assigns credit.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import TypedDict

from method_loop.durable import (DurableExecutionError, DurableExecutionStore,
    native_target_handle, validate_native_registration)

from ._local_job_worker import atomic_json


class NativeEventDisposition(TypedDict):
    state: str
    code: str | None
    target_handle: str | None
    cursor: int | None
    record_ref: str | None


def _text(value):
    if type(value) is not str or not value.strip() or '\x00' in value:
        raise ValueError('native_event_identity_required')
    return value


def _directory(value):
    if not isinstance(value, (str, Path)) or not Path(value).is_absolute():
        raise ValueError('absolute_native_event_directory_required')
    return Path(value).resolve()


@dataclass(frozen=True, init=False)
class NativeEventBinding:
    execution_directory: Path
    run_id: str
    owner_episode_id: str
    job_ref: str
    registry_ref: str
    resource_id: str

    def __init__(self, execution_directory, *, run_id, owner_episode_id, job_ref, registry_ref, resource_id):
        object.__setattr__(self, 'execution_directory', _directory(execution_directory))
        for key, value in locals().copy().items():
            if key not in {'self', 'execution_directory'}:
                object.__setattr__(self, key, _text(value))

    def as_record(self):
        return {'version': 'native_event_binding_v1', 'execution_directory': str(self.execution_directory),
            **{key: getattr(self, key) for key in ('run_id', 'owner_episode_id', 'job_ref', 'registry_ref', 'resource_id')}}

    @classmethod
    def from_record(cls, value):
        fields = {'version', 'execution_directory', 'run_id', 'owner_episode_id', 'job_ref', 'registry_ref', 'resource_id'}
        if type(value) is not dict or set(value) != fields or value['version'] != 'native_event_binding_v1':
            raise ValueError('invalid_native_event_binding')
        if type(value['execution_directory']) is not str:
            raise ValueError('invalid_native_event_binding')
        return cls(**{key: value[key] for key in fields - {'version'}})


@dataclass(frozen=True, init=False)
class NativeEventProvider:
    execution_directory: Path
    run_id: str
    resource_id: str

    def __init__(self, execution_directory, *, run_id, resource_id):
        object.__setattr__(self, 'execution_directory', _directory(execution_directory))
        object.__setattr__(self, 'run_id', _text(run_id))
        object.__setattr__(self, 'resource_id', _text(resource_id))

    def as_record(self):
        return {'version': 'native_event_provider_v1', 'execution_directory': str(self.execution_directory),
                'run_id': self.run_id, 'resource_id': self.resource_id}

    def for_job(self, *, owner_episode_id, job_ref, registry_ref, original_binding=None):
        selected = NativeEventBinding(self.execution_directory, run_id=self.run_id,
            owner_episode_id=owner_episode_id, job_ref=job_ref, registry_ref=registry_ref, resource_id=self.resource_id)
        if original_binding is None:
            return selected
        if type(original_binding) is not NativeEventBinding:
            raise TypeError('typed_native_event_binding_required')
        if any(getattr(original_binding, key) != getattr(selected, key) for key in
               ('execution_directory', 'run_id', 'job_ref', 'registry_ref', 'resource_id')):
            raise ValueError('native_event_binding_identity_conflict')
        return original_binding


def disposition(state, *, code=None, target_handle=None, cursor=None, record_ref=None):
    return NativeEventDisposition(state=state, code=code, target_handle=target_handle, cursor=cursor, record_ref=record_ref)


def _handle(handle_path):
    from .native_lifecycle import NativeJobHandle
    body = NativeJobHandle(Path(handle_path)).read()
    if body.get('native_events') is None:
        return body, None, None
    binding = NativeEventBinding.from_record(body['native_events'])
    identity = {'kind': 'systemd_user_service', 'unit': _text(body['unit']),
                'request_sha256': body['request_sha256']}
    if type(identity['request_sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', identity['request_sha256']):
        raise ValueError('native_event_identity_conflict')
    raw = Path(body['paths']['request']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != identity['request_sha256']:
        raise ValueError('native_event_identity_conflict')
    request = json.loads(raw)
    if request.get('command') != body['command'] or request.get('cwd') != body['cwd']:
        raise ValueError('native_event_identity_conflict')
    return body, binding, identity


def _registration(binding, identity):
    return validate_native_registration({'version': 'native_event_registration_v1',
        'handle': native_target_handle(identity), **{key: getattr(binding, key) for key in
            ('run_id', 'owner_episode_id', 'job_ref', 'registry_ref', 'resource_id')},
        'native_identity': identity})


def ensure_native_event_target(handle_path):
    body, binding, identity = _handle(handle_path)
    if binding is None:
        return None
    registration = _registration(binding, identity)
    return DurableExecutionStore(binding.execution_directory).register_native_target(registration)


def _validate_receipt(value, identity):
    if (type(value) is not dict or set(value) != {'version', 'native_identity', 'SERVICE_RESULT',
            'EXIT_CODE', 'EXIT_STATUS', 'ended'} or value['version'] != 'native_service_exit_receipt_v1'
            or value['native_identity'] != identity):
        raise ValueError('native_event_receipt_invalid')
    for key in ('SERVICE_RESULT', 'EXIT_CODE', 'EXIT_STATUS'):
        if value[key] is not None and type(value[key]) is not str:
            raise ValueError('native_event_receipt_invalid')
    ended = value['ended']
    if (type(ended) is not dict or set(ended) != {'at', 'monotonic_ns', 'boot_id'}
            or type(ended['monotonic_ns']) is not int or ended['monotonic_ns'] < 0):
        raise ValueError('native_event_receipt_invalid')
    _text(ended['boot_id'])
    instant = datetime.fromisoformat(_text(ended['at']).replace('Z', '+00:00'))
    if instant.tzinfo is None or instant.utcoffset() != timezone.utc.utcoffset(instant):
        raise ValueError('native_event_receipt_invalid')
    return value


def commit_service_exit_receipt(handle_path, status_path, *, service_exit, event_time):
    """Commit once under the status lock; replay keeps the first FILE BYTES."""
    body, binding, identity = _handle(handle_path)
    if binding is None or Path(body['paths']['status']) != Path(status_path):
        raise ValueError('native_event_identity_conflict')
    status_path = Path(status_path)
    with Path(str(status_path)+'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if status_path.exists():
            _validate_receipt(json.loads(status_path.read_bytes()), identity)
            return
        value = {'version': 'native_service_exit_receipt_v1', 'native_identity': identity,
                 **service_exit, 'ended': event_time()}
        _validate_receipt(value, identity)
        atomic_json(status_path, value)


def publish_native_events(handle_path):
    """Retry event export using original bytes; never reenter the exit hook."""
    output, target = None, None
    try:
        body, binding, identity = _handle(handle_path)
        if binding is None:
            return disposition('not_configured')
        output = Path(body['paths']['native_events'])
        registration = _registration(binding, identity)
        target = registration['handle']
        # Serialize the optional disposition writer, independently of the
        # receipt lock. The ledger also enforces atomic, exact idempotence.
        with Path(str(output)+'.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            store = DurableExecutionStore(binding.execution_directory)
            store.register_native_target(registration)
            receipt_path = Path(body['paths']['status'])
            if not receipt_path.exists():
                result = disposition('pending', target_handle=target)
            else:
                raw = receipt_path.read_bytes()
                receipt = _validate_receipt(json.loads(raw), identity)
                sha = hashlib.sha256(raw).hexdigest()
                publication = {'version': 'native_event_publication_v1', 'event': 'state_changed',
                    'cause': 'service_exit_receipt_committed', 'record_ref': 'native_event_record_'+sha[:24],
                    'receipt_sha256': sha, 'occurred_at': receipt['ended']['at']}
                event = store.publish_native_event(target, publication, receipt_bytes=raw)
                result = disposition('recorded', target_handle=event['handle'], cursor=event['cursor'],
                                     record_ref=event['record_ref'])
            atomic_json(output, result)
            return result
    except DurableExecutionError as error:
        result = disposition('unavailable', code=('native_event_identity_conflict'
            if error.failure['code'] == 'identity_conflict' else 'native_event_storage_unavailable'), target_handle=target)
    except (OSError, sqlite3.Error):
        result = disposition('unavailable', code='native_event_storage_unavailable', target_handle=target)
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        result = disposition('unavailable', code=('native_event_identity_conflict'
            if str(error) == 'native_event_identity_conflict' else 'native_event_receipt_invalid'), target_handle=target)
    if output is not None:
        try:
            with Path(str(output)+'.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                atomic_json(output, result)
        except OSError:
            pass
    return result
