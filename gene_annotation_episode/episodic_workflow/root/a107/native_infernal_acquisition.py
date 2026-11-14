"""Retain one selected original Infernal attempt, without execution or grading.

The immutable capture plan is saved before reading the original manifest. Replay
qualifies that saved plan and the retained Store bytes; it never reopens the
native reservation or reacquires an original input or output.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from .domain import ContractError
from .execution_contracts import validate_target
from .local_jobs import LocalJobPolicy
from .materials import artifact_file, artifact_path
from .native_infernal_contracts import (compile_native_infernal_job, finite_json_copy,
    native_infernal_digest, validate_native_infernal_requested_job)
from .native_infernal_driver import _staged_relative
from .native_infernal_local import local_infernal_plan
from .practical_execution_state import _immutable, _read


VERSION = 'native_infernal_capture_v1'
PROVIDER = 'episode.execution_result'
ORIGIN = {'content_location': 'retained_complete_producer_bundle',
    'attempt_output_version': 'original_producer_manifest_and_verified_file_digests',
    'window_consistency': 'complete_files_matched_to_original_manifest',
    'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
_BUNDLE_FIELDS = {'version', 'identity', 'requested_job', 'program', 'table_format',
    'software', 'realized_argv', 'environment', 'inputs', 'operand_bindings',
    'returncode', 'artifacts', 'failures', 'started_at', 'finished_at'}
_CAPTURE_FIELDS = {'version', 'bundle_artifact_ref', 'bundle_validated', 'artifacts',
    'invalid_artifacts', 'failures', 'complete'}
_ROW_FIELDS = {'role', 'format', 'relative_path', 'artifact_ref'}
_HEX = re.compile(r'^[0-9a-f]{64}$')


def is_native_infernal_target(target):
    """Recognize the explicit request branch, without claiming an HPC binding."""
    return (isinstance(target, dict) and target.get('resource_kind') in ('local', 'hpc')
        and isinstance(target.get('assignment'), dict)
        and isinstance(target['assignment'].get('requested_job'), dict)
        and 'native_infernal' in target['assignment']['requested_job'])


def _path(value, *, absolute=False):
    if (type(value) is not str or not value or any(c in value for c in ('\0', '\n', '\r', '\\'))
            or value.startswith('//') or '..' in value.split('/') or value in {'.', '/'}):
        raise ContractError('native_infernal_capture_path_invalid')
    path = PurePosixPath(value)
    if path.is_absolute() != absolute or str(path) != value:
        raise ContractError('native_infernal_capture_path_invalid')
    return path


def _sha(value, *, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or _HEX.fullmatch(value) is None:
        raise ContractError('native_infernal_bundle_digest_invalid')


def _same(left, right):
    # JSON equality must not make True equal to the native integer 1.
    return native_infernal_digest(left) == native_infernal_digest(right)


def _plan(value):
    """Pure qualification; the producer's plan reader also checks live files."""
    plan = finite_json_copy(value)
    if (type(plan) is not dict or set(plan) != {'version', 'identity', 'requested_job',
            'attempt_directory', 'policy'} or plan['version'] != 'native_infernal_run_plan_v1'):
        raise ContractError('native_infernal_run_plan_required')
    request = validate_native_infernal_requested_job(plan['requested_job'])
    identity = plan['identity']
    if (type(identity) is not dict or set(identity) != {'run_id', 'episode_id', 'resource_id',
            'execution_id', 'attempt_id', 'operation_key', 'requested_job_sha256'}
            or any(type(v) is not str or not v or '\0' in v for v in identity.values())
            or identity['requested_job_sha256'] != native_infernal_digest(request)
            or identity['attempt_id'] != native_infernal_digest(identity['operation_key'])):
        raise ContractError('native_infernal_original_plan_identity_conflict')
    attempt = _path(plan['attempt_directory'], absolute=True)
    execution = _path(identity['execution_id'], absolute=True)
    if execution.name != 'native.json' or attempt != execution.parent / 'infernal-attempt':
        raise ContractError('native_infernal_original_plan_directory_conflict')
    policy = plan['policy']
    if type(policy) is not dict or set(policy) != {'memory_bytes', 'scratch_bytes'}:
        raise ContractError('native_infernal_explicit_policy_required')
    LocalJobPolicy(**policy)
    return plan


def _target_plan(target, plan):
    plan = _plan(plan)
    identity, assignment = plan['identity'], target['assignment']
    if (assignment.get('resource_kind') != 'local'
            or assignment.get('resource_id') != target['resource_id']
            or not _same(assignment.get('requested_job'), plan['requested_job'])
            or target['request_sha256'] != identity['requested_job_sha256']
            or any(target[key] != identity[other] for key, other in (
                ('run_id', 'run_id'), ('origin_episode_id', 'episode_id'),
                ('resource_id', 'resource_id'), ('execution_id', 'execution_id')))):
        raise ContractError('native_infernal_original_target_conflict')
    workspace = _path(assignment.get('workspace'), absolute=True)
    expected = workspace / '.episode-operations' / native_infernal_digest({
        'run': identity['run_id'], 'episode': identity['episode_id']}) / identity['attempt_id']
    if PurePosixPath(plan['attempt_directory']) != expected / 'infernal-attempt':
        raise ContractError('native_infernal_original_plan_directory_conflict')
    return plan


def validate_original_bundle(bundle, plan):
    """Return an independent finite manifest after pure association checks."""
    plan, bundle = _plan(plan), finite_json_copy(bundle)
    if (type(bundle) is not dict or set(bundle) != _BUNDLE_FIELDS
            or bundle['version'] != 'native_infernal_bundle_v1'
            or not _same(bundle['identity'], plan['identity'])
            or not _same(bundle['requested_job'], plan['requested_job'])):
        raise ContractError('native_infernal_original_bundle_identity_conflict')
    job, root = plan['requested_job']['native_infernal'], PurePosixPath(plan['attempt_directory'])
    if any(not _same(bundle[key], job[key]) for key in ('program', 'table_format', 'operand_bindings')):
        raise ContractError('native_infernal_original_bundle_request_conflict')
    software = bundle['software']
    if (type(software) is not dict or set(software) != {'executable', 'expected_sha256',
            'actual_sha256', 'declared_engine_version'}
            or software['executable'] != job['software']['executable']
            or software['expected_sha256'] != job['software']['sha256']
            or software['declared_engine_version'] != job['software']['engine_version']):
        raise ContractError('native_infernal_original_bundle_software_conflict')
    _sha(software['actual_sha256'], nullable=True)
    rc = bundle['returncode']
    if rc is not None and type(rc) is not int:
        raise ContractError('native_infernal_bundle_returncode_invalid')
    try:
        times = [datetime.fromisoformat(bundle[key]) for key in ('started_at', 'finished_at')]
        if any(t.utcoffset() is None for t in times) or times[1] < times[0]:
            raise ValueError
    except (TypeError, ValueError, OverflowError) as error:
        raise ContractError('native_infernal_bundle_timestamp_conflict') from error
    operands = {row['role']: row for row in job['operands']}
    outputs = {row['role']: row for row in job['outputs']}
    failures = bundle['failures']
    if type(failures) is not list:
        raise ContractError('native_infernal_bundle_failures_invalid')
    for failure in failures:
        if (type(failure) is not dict or set(failure) != {'stage', 'code', 'role', 'detail'}
                or type(failure['stage']) is not str
                or failure['stage'] not in {'software', 'inputs', 'staging', 'execution', 'outputs'}
                or type(failure['code']) is not str or not failure['code']
                or type(failure['detail']) is not dict
                or failure['role'] is not None and type(failure['role']) is not str):
            raise ContractError('native_infernal_bundle_failures_invalid')
        stage, role, detail = failure['stage'], failure['role'], failure['detail']
        if ((stage in {'software', 'execution'} and role is not None)
                or stage in {'inputs', 'staging'} and role not in operands
                or stage == 'outputs' and role not in outputs):
            raise ContractError('native_infernal_bundle_failure_role_conflict')
        if stage == 'outputs' and detail.get('relative_path') != outputs[role]['relative_path']:
            raise ContractError('native_infernal_bundle_failure_path_conflict')
        if failure['code'] == 'native_infernal_nonzero_returncode' and (
                stage != 'execution' or rc in (None, 0) or not _same(detail, {'returncode': rc})):
            raise ContractError('native_infernal_bundle_execution_failure_conflict')
    if (rc is None and not any(f['stage'] != 'outputs' for f in failures)
            or rc not in (None, 0) and not any(f['code'] == 'native_infernal_nonzero_returncode'
                for f in failures)):
        raise ContractError('native_infernal_bundle_execution_failure_missing')
    if software['actual_sha256'] != software['expected_sha256'] and (
            rc is not None or not any(f['stage'] == 'software' for f in failures)):
        raise ContractError('native_infernal_bundle_software_measurement_conflict')
    inputs = bundle['inputs']
    if type(inputs) is not list or len(inputs) != len(operands):
        raise ContractError('native_infernal_original_bundle_inputs_conflict')
    staged, seen = {}, set()
    for row in inputs:
        if (type(row) is not dict or set(row) != {'role', 'format', 'original_path', 'relative_path',
                'artifact_ref', 'expected_sha256', 'actual_sha256', 'expected_size_bytes', 'size_bytes'}
                or type(row['role']) is not str or row['role'] not in operands or row['role'] in seen):
            raise ContractError('native_infernal_original_bundle_input_conflict')
        operand = operands[row['role']]
        for actual, expected in (('format', 'format'), ('original_path', 'path'),
                ('artifact_ref', 'artifact_ref'), ('expected_sha256', 'sha256'),
                ('expected_size_bytes', 'size_bytes')):
            if not _same(row[actual], operand[expected]):
                raise ContractError('native_infernal_original_bundle_input_conflict')
        if row['relative_path'] != _staged_relative(operand):
            raise ContractError('native_infernal_original_bundle_input_path_conflict')
        _sha(row['actual_sha256'], nullable=True)
        size = row['size_bytes']
        if size is not None and (type(size) is not int or size < 0):
            raise ContractError('native_infernal_bundle_size_invalid')
        failed = any(f['role'] == row['role'] and f['stage'] in {'inputs', 'staging'} for f in failures)
        if ((row['actual_sha256'] is None) != (size is None)
                or (row['actual_sha256'], size) != (operand['sha256'], operand['size_bytes'])
                    and (rc is not None or not failed)):
            raise ContractError('native_infernal_bundle_input_measurement_conflict')
        staged[row['role']] = str(root / _path(row['relative_path']))
        seen.add(row['role'])
    compiled = compile_native_infernal_job(job, input_paths=staged, output_directory=str(root))
    environment = {**compiled['environment'], **{key: str(root / 'tmp') for key in ('TMPDIR', 'TMP', 'TEMP')},
        'XDG_CACHE_HOME': str(root / 'cache')}
    if not _same(bundle['realized_argv'], compiled['argv']) or not _same(bundle['environment'], environment):
        raise ContractError('native_infernal_original_realized_command_conflict')
    if type(bundle['artifacts']) is not list:
        raise ContractError('native_infernal_bundle_artifacts_invalid')
    seen = set()
    for row in bundle['artifacts']:
        if (type(row) is not dict or set(row) != {'role', 'format', 'relative_path', 'size_bytes', 'sha256'}
                or type(row['role']) is not str or row['role'] not in outputs or row['role'] in seen
                or type(row['size_bytes']) is not int or row['size_bytes'] < 0
                or any(row[key] != outputs[row['role']][key] for key in ('format', 'relative_path'))):
            raise ContractError('native_infernal_original_bundle_output_conflict')
        _path(row['relative_path'])
        _sha(row['sha256'])
        seen.add(row['role'])
    missing = outputs.keys() - seen
    if missing and rc == 0 and not failures:
        raise ContractError('native_infernal_successful_bundle_missing_outputs:' + ','.join(sorted(missing)))
    if any(not any(f['stage'] == 'outputs' and f['role'] == role for f in failures) for role in missing):
        raise ContractError('native_infernal_bundle_missing_output_failure_required')
    return bundle


def _selected_files(bundle):
    """Include absent selected files so later stray bytes cannot be validated."""
    result = []
    for row in bundle['inputs']:
        result.append({**{key: row[key] for key in ('role', 'format', 'relative_path')},
            'sha256': row['actual_sha256'], 'size_bytes': row['size_bytes']})
    produced = {row['role']: row for row in bundle['artifacts']}
    for row in bundle['requested_job']['native_infernal']['outputs']:
        actual = produced.get(row['role'], {'sha256': None, 'size_bytes': None})
        result.append({**row, 'sha256': actual['sha256'], 'size_bytes': actual['size_bytes']})
    return result


def _directory(value):
    directory = Path(value).absolute()
    _path(str(directory), absolute=True)
    if directory.resolve() != directory:
        raise ContractError('native_infernal_capture_directory_escape')
    return directory


@contextmanager
def _confined_reader(root, relative):
    """Open only a regular file through confined, non-symlink path components."""
    relative = _path(relative)
    root = _directory(root)
    descriptors = []
    try:
        descriptors.append(os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
        for part in relative.parts[:-1]:
            descriptors.append(os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptors[-1]))
        descriptor = os.open(relative.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
            dir_fd=descriptors[-1])
        descriptors.append(descriptor)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ContractError('native_infernal_capture_regular_file_required')
        yield Path('/proc/self/fd') / str(descriptor)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _capture_file(store, root, relative, media_type='application/octet-stream'):
    with _confined_reader(root, relative) as path:
        return artifact_file(store, path, media_type)


def _retained(store, reference):
    if type(reference) is not str:
        raise ContractError('native_infernal_capture_artifact_reference_invalid')
    metadata = store._require(reference, {'artifact'})
    _sha(metadata['sha256'])
    if (reference != 'artifact_' + metadata['sha256'] or type(metadata['size']) is not int
            or metadata['size'] < 0):
        raise ContractError('native_infernal_capture_artifact_identity_conflict')
    relative = metadata['sha256'][:2] + '/' + metadata['sha256']
    with _confined_reader(store.path / 'artifacts', relative) as path:
        if path.stat().st_size != metadata['size']:
            raise ContractError('native_infernal_capture_artifact_size_conflict')
        artifact_path(store, reference)
    return metadata


def _decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ContractError('native_infernal_manifest_duplicate_key')
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ContractError('native_infernal_manifest_json_invalid') from error


def _shape(capture):
    capture = finite_json_copy(capture)
    if (type(capture) is not dict or set(capture) != _CAPTURE_FIELDS or capture['version'] != VERSION
            or type(capture['bundle_validated']) is not bool or type(capture['complete']) is not bool
            or capture['bundle_artifact_ref'] is not None and type(capture['bundle_artifact_ref']) is not str
            or any(type(capture[key]) is not list for key in ('artifacts', 'invalid_artifacts', 'failures'))):
        raise ContractError('native_infernal_capture_receipt_invalid')
    for row in capture['artifacts'] + capture['invalid_artifacts']:
        if type(row) is not dict or set(row) != _ROW_FIELDS or any(type(v) is not str or not v for v in row.values()):
            raise ContractError('native_infernal_capture_artifact_row_invalid')
        _path(row['relative_path'])
    for row in capture['failures']:
        if (type(row) is not dict or set(row) != {'stage', 'code', 'record_key'}
                or row['stage'] != 'capture' or type(row['code']) is not str or not row['code']
                or row['record_key'] is not None):
            raise ContractError('native_infernal_capture_failure_invalid')
    return capture


def _validate_rows(store, capture, bundle):
    selected = {row['relative_path']: row for row in _selected_files(bundle)}
    seen, failures = set(), []
    for category in ('artifacts', 'invalid_artifacts'):
        for row in capture[category]:
            path = row['relative_path']
            expected = selected.get(path)
            if (expected is None or path in seen
                    or any(row[key] != expected[key] for key in ('role', 'format'))):
                raise ContractError('native_infernal_capture_artifact_association_conflict')
            seen.add(path)
            metadata = _retained(store, row['artifact_ref'])
            matches = (metadata['sha256'], metadata['size']) == (expected['sha256'], expected['size_bytes'])
            if (category == 'artifacts') != matches:
                raise ContractError('native_infernal_capture_artifact_measurement_conflict')
            if not matches:
                failures.append(('native_infernal_sealed_artifact_digest_mismatch:'
                    if expected['sha256'] is not None else 'native_infernal_unlisted_file_present:') + path)
    recorded = [row['code'] for row in capture['failures']]
    # Missing files have an immutable acquisition failure, not a new read of
    # their former path during replay. Every actual manifest file is accounted.
    for path, row in selected.items():
        if path not in seen:
            code = 'native_infernal_bundle_file_unavailable_or_escaped:' + path
            if row['sha256'] is not None or code in recorded:
                failures.append(code)
    if sorted(recorded) != sorted(failures):
        raise ContractError('native_infernal_capture_failure_association_conflict')
    if capture['complete'] != (not failures):
        raise ContractError('native_infernal_capture_completion_conflict')


def _saved_capture(store, *, target, directory):
    plan = _target_plan(target, _read(directory / 'capture-plan.json'))
    saved = _shape(_read(directory / 'capture.json'))
    reference = saved['bundle_artifact_ref']
    bundle = None
    if reference is not None:
        _retained(store, reference)
        try:
            bundle = validate_original_bundle(_decode(store.get_artifact(reference)), plan)
        except ValueError as error:
            if saved['bundle_validated'] or saved['failures'] != [_failure(str(error))]:
                raise ContractError('native_infernal_capture_manifest_validation_conflict') from error
    if bundle is None:
        if (saved['bundle_validated'] or saved['complete'] or saved['artifacts'] or saved['invalid_artifacts']
                or not saved['failures'] or reference is None and saved['failures'] != [
                    _failure('native_infernal_sealed_bundle_unavailable')]):
            raise ContractError('native_infernal_capture_unvalidated_manifest_conflict')
    else:
        if not saved['bundle_validated']:
            raise ContractError('native_infernal_capture_manifest_validation_conflict')
        _validate_rows(store, saved, bundle)
    return saved


def _failure(code):
    return {'stage': 'capture', 'code': code, 'record_key': None}


def capture_local_bundle(store, *, target, directory):
    """Capture original manifest/files once; complete describes custody only."""
    if not is_native_infernal_target(target) or target['resource_kind'] != 'local':
        raise ContractError('native_infernal_local_capture_binding_required')
    target = validate_target(finite_json_copy(target))
    directory = _directory(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in ('capture-intent.json', 'capture-plan.json', 'capture.json'):
        path = directory / name
        if path.is_symlink() or path.exists() and not path.is_file():
            raise ContractError('native_infernal_capture_record_path_invalid')
    _immutable(directory / 'capture-intent.json', {'target': target})
    if (directory / 'capture.json').exists():
        return _saved_capture(store, target=target, directory=directory)
    plan = _target_plan(target, local_infernal_plan(target['assignment'], target['execution_id']))
    _immutable(directory / 'capture-plan.json', plan)
    root = Path(plan['attempt_directory'])
    result = {'version': VERSION, 'bundle_artifact_ref': None, 'bundle_validated': False,
        'artifacts': [], 'invalid_artifacts': [], 'failures': [], 'complete': False}
    try:
        reference = _capture_file(store, root, 'bundle.json', 'application/json')
        result['bundle_artifact_ref'] = reference
        _retained(store, reference)
        bundle = validate_original_bundle(_decode(store.get_artifact(reference)), plan)
        result['bundle_validated'] = True
    except (ValueError, OSError) as error:
        code = str(error) if isinstance(error, ValueError) and result['bundle_artifact_ref'] else (
            'native_infernal_sealed_bundle_unavailable')
        result['failures'].append(_failure(code))
        _immutable(directory / 'capture.json', result)
        return result
    for row in _selected_files(bundle):
        item = {key: row[key] for key in ('role', 'format', 'relative_path')}
        reference = None
        try:
            reference = _capture_file(store, root, row['relative_path'])
            metadata = _retained(store, reference)
            if (metadata['sha256'], metadata['size']) != (row['sha256'], row['size_bytes']):
                result['invalid_artifacts'].append({**item, 'artifact_ref': reference})
                code = ('native_infernal_sealed_artifact_digest_mismatch:' if row['sha256'] is not None
                    else 'native_infernal_unlisted_file_present:') + row['relative_path']
                result['failures'].append(_failure(code))
            else:
                result['artifacts'].append({**item, 'artifact_ref': reference})
        except FileNotFoundError:
            if row['sha256'] is not None:
                result['failures'].append(_failure('native_infernal_bundle_file_unavailable_or_escaped:'
                    + row['relative_path']))
        except (ValueError, OSError):
            # A failed Store-integrity check must not make an unusable artifact
            # appear to be retained valid data. Other siblings still survive.
            if reference is not None:
                raise
            result['failures'].append(_failure('native_infernal_bundle_file_unavailable_or_escaped:'
                + row['relative_path']))
    result['complete'] = not result['failures']
    _validate_rows(store, result, bundle)
    _immutable(directory / 'capture.json', result)
    return result


def original_source_payload(*, bundle, capture, prepared):
    """Stable original-attempt source; projection/page selection is not identity."""
    bundle, capture = finite_json_copy(bundle), _shape(capture)
    if (not capture['bundle_validated'] or capture['bundle_artifact_ref'] is None
            or type(bundle) is not dict or bundle.get('version') != 'native_infernal_bundle_v1'):
        raise ContractError('native_infernal_source_validated_manifest_required')
    auxiliary = [row['artifact_ref'] for row in capture['artifacts'] + capture['invalid_artifacts']]
    if prepared is not None and prepared.get('source_grading_artifact_ref') is not None:
        auxiliary.append(prepared['source_grading_artifact_ref'])
    if any(type(ref) is not str or not ref for ref in auxiliary):
        raise ContractError('native_infernal_source_artifact_reference_invalid')
    return {'provider': PROVIDER, 'accession': 'native_infernal_' + native_infernal_digest(bundle['identity']),
        'uri': None, 'artifact_ref': capture['bundle_artifact_ref'], 'text_ref': None, 'request_ref': None,
        'version': 'native_infernal_bundle_v1', 'retrieved_at': bundle['finished_at'],
        'auxiliary_artifact_refs': sorted(set(auxiliary))}


def publish_original_source(store, *, bundle, capture, prepared):
    payload = original_source_payload(bundle=bundle, capture=capture, prepared=prepared)
    _retained(store, payload['artifact_ref'])
    if not _same(_decode(store.get_artifact(payload['artifact_ref'])), bundle):
        raise ContractError('native_infernal_source_bundle_association_conflict')
    _validate_rows(store, capture, bundle)
    for reference in payload['auxiliary_artifact_refs']:
        _retained(store, reference)
    return store.put('source', payload, origin='tool')['id']


__all__ = ['capture_local_bundle', 'validate_original_bundle', 'publish_original_source',
    'original_source_payload', 'is_native_infernal_target', 'ORIGIN', 'VERSION']
