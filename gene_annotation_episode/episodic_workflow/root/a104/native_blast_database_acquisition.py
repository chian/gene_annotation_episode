"""Original PBS attempt custody, complete bounded transfer and frozen replay.

This adapter never runs a search, selects a resource or follows current.json.
The reader authenticates the actual original ledger before the N validator is
given an attempt witness. A capture is an action receipt, not row authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from .domain import ContractError
from .execution_contracts import canonical, digest, validate_target
from .materials import artifact_file, artifact_path
from .native_blast_database_contracts import validate_native_blast_database_bundle
from .practical_execution_state import _immutable, _read

VERSION = 'native_blast_database_capture_v1'
CHUNK_BYTES = 1024 * 1024
_FAILURES = {'plan_missing', 'plan_identity_mismatch', 'bundle_missing', 'bundle_invalid',
    'attempt_mismatch', 'file_missing', 'file_read_failed', 'file_size_mismatch',
    'file_digest_mismatch', 'file_changed'}


def is_native_blast_database_target(target):
    return (type(target) is dict and target.get('resource_kind') == 'hpc'
        and 'native_blast_database' in target.get('assignment', {}).get('requested_job', {}))


def _decode(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate_json_key:' + key)
            value[key] = item
        return value
    def nonfinite(value):
        raise ValueError('nonfinite_json:' + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def _retained(store, reference, *, sha256=None, size_bytes=None):
    try:
        path = artifact_path(store, reference)
        size = path.stat().st_size
    except OSError as error:
        raise ContractError('native_blast_database_frozen_artifact_unavailable',
            detail={'artifact_ref': reference, 'exception_type': type(error).__module__ + '.' + type(error).__qualname__,
                'message': str(error)}) from error
    record = store.get(reference)
    if (size != record['size'] or sha256 is not None and record['sha256'] != sha256
            or size_bytes is not None and record['size'] != size_bytes):
        raise ContractError('native_blast_database_frozen_artifact_changed')
    return path


def _attempt(target, witness):
    """Check the reader's ledger witness against the immutable original target."""
    validate_target(target)
    if not is_native_blast_database_target(target):
        raise ContractError('native_blast_database_hpc_target_required')
    if isinstance(witness, dict) and witness.get('version') == 'terminal_native_database_attempt_v1':
        from .native_database_terminal_custody import validate_terminal_database_attempt
        return validate_terminal_database_attempt(target, witness)
    if type(witness) is not dict or set(witness) != {'authenticated_attempt', 'plan_path', 'ledger', 'job_request'}:
        raise ContractError('native_blast_database_actual_attempt_witness_required')
    authenticated, ledger, job_request = (witness[k] for k in ('authenticated_attempt', 'ledger', 'job_request'))
    if type(authenticated) is not dict or set(authenticated) != {'identity', 'attempt_directory', 'plan_sha256'}:
        raise ContractError('native_blast_database_actual_attempt_witness_required')
    owner = authenticated['identity']
    expected = {'run_id': target['run_id'], 'episode_id': target['origin_episode_id'],
        'resource_id': target['resource_id'], 'execution_id': target['execution_id'],
        'requested_job_sha256': target['request_sha256'], 'assignment_sha256': digest(target['assignment'])}
    if (type(owner) is not dict or set(owner) != set(expected) | {'operation_key', 'attempt_id', 'submission_token'}
            or any(owner[k] != value for k, value in expected.items())
            or owner['attempt_id'] != digest(owner['operation_key'])
            or owner['submission_token'] != digest({k: owner[k] for k in
                ('run_id', 'episode_id', 'assignment_sha256', 'operation_key')})):
        raise ContractError('native_blast_database_original_attempt_identity_conflict')
    root = (Path(target['assignment']['workspace']) / '.episode-jobs' /
        digest({'run_id': owner['run_id'], 'episode_id': owner['episode_id']}) /
        owner['assignment_sha256'] / 'attempts' / owner['attempt_id'])
    plan_path = str(root / 'native-blast-database-plan.json')
    if (authenticated['attempt_directory'] != str(root) or witness['plan_path'] != plan_path
            or ledger.get('version') != 'practical_pbs_submission_v2'
            or ledger.get('job_id') != owner['execution_id']
            or any(ledger.get(k) != owner[k] for k in ('attempt_id', 'operation_key', 'assignment_sha256', 'submission_token'))
            or ledger.get('selection', {}).get('requested_job_sha256') != owner['requested_job_sha256']
            or job_request.get('job_request_sha256') != owner['requested_job_sha256']
            or job_request.get('submission_token') != owner['submission_token']
            or any(row.get('native_blast_database_plan_path') != plan_path
                or row.get('native_blast_database_plan_sha256') != authenticated['plan_sha256']
                for row in (ledger, job_request))):
        raise ContractError('native_blast_database_original_attempt_identity_conflict')
    return authenticated


class _TransferFailure(ValueError):
    pass


def _transfer(store, reader, target, operation_key, remote, destination, *, sha256=None, size_bytes=None):
    """Stream the original file, verifying any interrupted same-action prefix.

    Existing bytes are never overwritten. A resumed capture rechecks them from
    offset zero against the authenticated original path before appending a
    missing tail. Every transport request remains at most one MiB.
    """
    offset, observed_size, hasher = 0, size_bytes, hashlib.sha256()
    destination = Path(destination)
    try:
        if destination.is_symlink():
            raise OSError('capture_destination_is_symlink')
        stream = destination.open('r+b' if destination.exists() else 'xb')
        retained_size = destination.stat().st_size
    except OSError as error:
        raise _TransferFailure('file_read_failed') from error
    with stream:
        while True:
            try:
                row = reader.read_file(target, path=remote, offset=offset, limit=CHUNK_BYTES, operation_key=operation_key)
            except FileNotFoundError as error:
                raise _TransferFailure('file_missing') from error
            except (ValueError, OSError) as error:
                raise _TransferFailure('file_read_failed') from error
            try:
                data = base64.b64decode(row['bytes_base64'], validate=True)
                if (row['path'] != remote or type(row['offset']) is not int or row['offset'] != offset
                        or type(row['size_bytes']) is not int or row['size_bytes'] < 0
                        or type(row['returned_bytes']) is not int or row['returned_bytes'] != len(data)
                        or len(data) > CHUNK_BYTES):
                    raise ValueError
            except (ValueError, KeyError, TypeError) as error:
                raise _TransferFailure('file_read_failed') from error
            if observed_size is None:
                observed_size = row['size_bytes']
            if retained_size > observed_size:
                raise _TransferFailure('file_size_mismatch')
            if row['size_bytes'] != observed_size:
                raise _TransferFailure('file_changed' if offset else 'file_size_mismatch')
            expected = min(CHUNK_BYTES, max(0, observed_size - offset))
            if len(data) != expected:
                raise _TransferFailure('file_size_mismatch')
            if not data:
                break
            retained = stream.read(min(len(data), max(0, retained_size - offset))) if retained_size > offset else b''
            if retained != data[:len(retained)]:
                raise _TransferFailure('file_changed')
            stream.write(data[len(retained):]); hasher.update(data); offset += len(data)
        stream.flush()
    if offset != observed_size:
        raise _TransferFailure('file_size_mismatch')
    if sha256 is not None and hasher.hexdigest() != sha256:
        raise _TransferFailure('file_digest_mismatch')
    return artifact_file(store, destination)


def _validate_capture(store, capture, *, target=None, operation_key=None, directory=None):
    fields = {'version', 'target', 'operation_key', 'plan_artifact_ref', 'bundle_artifact_ref',
        'artifact_refs', 'status', 'failures'}
    if (type(capture) is not dict or set(capture) != fields or capture['version'] != VERSION
            or capture['status'] not in {'complete', 'partial', 'unsealed', 'invalid'}
            or type(capture['artifact_refs']) is not dict or type(capture['failures']) is not list
            or any(type(row) is not dict or set(row) != {'code', 'artifact_key'} or row['code'] not in _FAILURES
                or row['artifact_key'] is not None and type(row['artifact_key']) is not str for row in capture['failures'])
            or target is not None and capture['target'] != target
            or operation_key is not None and capture['operation_key'] != operation_key
            or (capture['status'] == 'complete') != (not capture['failures'])):
        raise ContractError('native_blast_database_capture_receipt_invalid')
    for reference in [capture['plan_artifact_ref'], capture['bundle_artifact_ref'], *capture['artifact_refs'].values()]:
        if reference is not None:
            _retained(store, reference)
    if directory is None:
        return capture
    directory = Path(directory)
    if _read(directory / 'capture-intent.json') != {'target': capture['target'], 'operation_key': capture['operation_key']}:
        raise ContractError('native_blast_database_capture_intent_conflict')
    if capture['status'] in {'complete', 'partial'}:
        attempt = _attempt(capture['target'], _read(directory / 'authenticated-attempt.json'))
        plan = _decode(_retained(store, capture['plan_artifact_ref']).read_bytes())
        if digest(plan) != attempt['plan_sha256']:
            raise ContractError('native_blast_database_original_plan_identity_conflict')
        bundle = validate_native_blast_database_bundle(
            _decode(_retained(store, capture['bundle_artifact_ref']).read_bytes()),
            original_job=capture['target']['assignment']['requested_job']['native_blast_database'], attempt_identity=attempt)
        if bundle['plan'] != plan:
            raise ContractError('native_blast_database_original_plan_identity_conflict')
        rows = {r['artifact_key']: r for r in bundle['artifacts']}
        if not set(capture['artifact_refs']) <= set(rows) or capture['status'] == 'complete' and set(capture['artifact_refs']) != set(rows):
            raise ContractError('native_blast_database_capture_artifact_association_conflict')
        for key, reference in capture['artifact_refs'].items():
            _retained(store, reference, sha256=rows[key]['sha256'], size_bytes=rows[key]['size_bytes'])
    return capture


def capture_native_blast_database_bundle(store, *, target, reader, operation_key, directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    intent = {'target': target, 'operation_key': operation_key}
    _immutable(directory / 'capture-intent.json', intent)
    receipt = directory / 'capture.json'
    if receipt.exists():
        return _validate_capture(store, _read(receipt), target=target, operation_key=operation_key, directory=directory)
    finalization = directory / 'capture-finalization.json'
    if finalization.exists():
        # Finish only a previously sealed outcome. This is the same selected
        # action's atomic commit state, not another acquisition or row authority.
        saved = _read(finalization)
        result = _validate_capture(store, saved['capture'], target=target, operation_key=operation_key, directory=directory)
        _immutable(directory / 'capture-diagnostics.json', {'errors': saved['errors']})
        _immutable(receipt, result)
        return result
    result = dict(version=VERSION, **intent, plan_artifact_ref=None, bundle_artifact_ref=None,
        artifact_refs={}, status='invalid', failures=[])
    errors = []
    def fail(code, error=None, key=None):
        result['failures'].append({'code': code, 'artifact_key': key})
        if error is not None:
            errors.append({'failure_index': len(result['failures']) - 1,
                'exception_type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error)})
    try:
        witness = reader.authenticate_native_blast_database_attempt(target)
        attempt = _attempt(target, witness)
        _immutable(directory / 'authenticated-attempt.json', witness)
    except (ValueError, KeyError, TypeError, OSError) as error:
        fail('attempt_mismatch', error)
    else:
        try:
            manifest = witness.get('scientific_manifest')
            ref = _transfer(store, reader, target, operation_key, witness['plan_path'], directory / 'plan.capture',
                sha256=manifest['sha256'] if manifest is not None else None,
                size_bytes=manifest['size_bytes'] if manifest is not None else None)
            result['plan_artifact_ref'] = ref
            plan = _decode(_retained(store, ref).read_bytes())
            if (digest(plan) != attempt['plan_sha256'] or plan.get('identity') != {**attempt['identity'], 'execution_id': None}
                    or plan.get('requested_job') != target['assignment']['requested_job']):
                raise ValueError('original_plan_mismatch')
        except (ValueError, KeyError, OSError) as error:
            fail(('plan_missing' if str(error) == 'file_missing' else str(error))
                if isinstance(error, _TransferFailure) else 'plan_identity_mismatch', error)
        else:
            root = Path(attempt['attempt_directory']); result['status'] = 'unsealed'
            try:
                ref = _transfer(store, reader, target, operation_key, str(root / 'bundle.json'), directory / 'bundle.capture')
                result['bundle_artifact_ref'] = ref
                bundle = validate_native_blast_database_bundle(_decode(_retained(store, ref).read_bytes()),
                    original_job=target['assignment']['requested_job']['native_blast_database'], attempt_identity=attempt)
                if bundle['plan'] != plan:
                    raise ValueError('original_plan_mismatch')
            except (ValueError, KeyError, OSError) as error:
                fail(('bundle_missing' if str(error) == 'file_missing' else str(error))
                    if isinstance(error, _TransferFailure) else 'bundle_invalid', error)
                if not isinstance(error, _TransferFailure):
                    result['status'] = 'invalid'
            else:
                result['status'] = 'partial'
                for ordinal, row in enumerate(bundle['artifacts']):
                    try:
                        reference = _transfer(store, reader, target, operation_key, str(root / row['relative_path']),
                            directory / ('artifact-' + str(ordinal) + '.capture'), sha256=row['sha256'], size_bytes=row['size_bytes'])
                        result['artifact_refs'][row['artifact_key']] = reference
                    except (ValueError, OSError) as error:
                        fail(str(error) if isinstance(error, _TransferFailure) else 'file_read_failed', error, row['artifact_key'])
                # Reopen both seals after all transfers, using the same original
                # ledger path. No live reads occur during later replay.
                for label, remote, original in (('plan', witness['plan_path'], result['plan_artifact_ref']),
                        ('bundle', str(root / 'bundle.json'), result['bundle_artifact_ref'])):
                    try:
                        seal = _transfer(store, reader, target, operation_key, remote, directory / (label + '.seal'))
                        if seal != original:
                            raise _TransferFailure('file_changed')
                    except (ValueError, OSError) as error:
                        fail(str(error) if isinstance(error, _TransferFailure) else 'file_read_failed', error)
                        result['status'] = 'invalid'
                if not result['failures']:
                    result['status'] = 'complete'
    _immutable(finalization, {'capture': result, 'errors': errors})
    _immutable(directory / 'capture-diagnostics.json', {'errors': errors})
    _immutable(receipt, result)
    return _validate_capture(store, result, target=target, operation_key=operation_key, directory=directory)


def _source_payload(bundle, capture):
    return {'provider': 'episode.execution_result', 'accession': 'native_blast_database_' + digest(bundle['identity']),
        'uri': None, 'artifact_ref': capture['bundle_artifact_ref'], 'text_ref': None, 'request_ref': None,
        'version': 'native_blast_database_bundle_v1', 'retrieved_at': bundle['sealed_at'],
        'auxiliary_artifact_refs': list(dict.fromkeys(capture['artifact_refs'][row['artifact_key']] for row in bundle['artifacts']
            if row['artifact_key'] in capture['artifact_refs']))}


__all__ = ['capture_native_blast_database_bundle', 'is_native_blast_database_target']
