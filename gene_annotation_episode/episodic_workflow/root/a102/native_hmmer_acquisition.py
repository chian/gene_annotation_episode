"""Capture the sealed outputs of one original, explicitly selected attempt.

These functions acquire bytes only. They choose no job, resource, parser,
retry or continuation. Complete immutable captures feed the separate graders.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from .domain import ContractError
from .execution_contracts import digest
from .materials import artifact_file, artifact_path
from .native_hmmer_contracts import CHECKPOINT_ROLES, finite_json_copy
from .native_hmmer_local import local_hmmer_plan
from .practical_execution_state import _immutable, _read


VERSION = 'native_hmmer_capture_v1'
PROVIDER = 'episode.execution_result'
ORIGIN = {'content_location': 'retained_complete_producer_bundle',
    'attempt_output_version': 'original_producer_manifest_and_verified_file_digests',
    'window_consistency': 'complete_files_matched_to_original_manifest',
    'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
_HEX = re.compile(r'^[0-9a-f]{64}$')


def is_native_hmmer_target(target):
    return (target.get('resource_kind') in {'local', 'hpc'} and
        'native_hmmer' in target.get('assignment', {}).get('requested_job', {}))


def _relative(value):
    if (not isinstance(value, str) or not value or Path(value).is_absolute()
            or str(Path(value)) != value or '..' in Path(value).parts
            or any(char in value for char in ('\0', '\n', '\r'))):
        raise ContractError('native_hmmer_bundle_relative_path_invalid')
    return value


def _sha(value, *, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str) or not _HEX.fullmatch(value.lower()):
        raise ContractError('native_hmmer_bundle_digest_invalid')


def validate_original_bundle(bundle, plan):
    """Validate manifest associations against the frozen producer plan."""
    bundle = finite_json_copy(bundle)
    fields = {'version', 'identity', 'requested_job', 'program', 'mode', 'software',
        'realized_argv', 'environment', 'inputs', 'operand_bindings', 'returncode',
        'artifacts', 'failures', 'started_at', 'finished_at'}
    if (not isinstance(bundle, dict) or set(bundle) != fields
            or bundle['version'] != 'native_hmmer_bundle_v1'
            or bundle['identity'] != plan['identity']
            or bundle['requested_job'] != plan['requested_job']):
        raise ContractError('native_hmmer_original_bundle_identity_conflict')
    job = plan['requested_job']['native_hmmer']
    software = bundle['software']
    if (bundle['program'] != job['program'] or bundle['mode'] != job['mode']
            or bundle['operand_bindings'] != job['operand_bindings']
            or not isinstance(software, dict) or set(software) != {
                'executable', 'expected_sha256', 'actual_sha256', 'declared_engine_version'}
            or software['executable'] != job['software']['executable']
            or software['expected_sha256'] != job['software']['sha256']
            or software['declared_engine_version'] != job['software']['engine_version']):
        raise ContractError('native_hmmer_original_bundle_request_conflict')
    _sha(software['actual_sha256'], nullable=True)
    if bundle['returncode'] is not None and type(bundle['returncode']) is not int:
        raise ContractError('native_hmmer_bundle_returncode_invalid')
    if (not isinstance(bundle['failures'], list) or any(not isinstance(row, dict)
            or set(row) != {'stage', 'code', 'role', 'detail'}
            or not isinstance(row['detail'], dict)
            or any(not isinstance(row[key], str) or not row[key] for key in ('stage', 'code'))
            or row['role'] is not None and not isinstance(row['role'], str)
            for row in bundle['failures'])):
        raise ContractError('native_hmmer_bundle_failures_invalid')
    for field in ('started_at', 'finished_at'):
        if not isinstance(bundle[field], str) or not bundle[field]:
            raise ContractError('native_hmmer_bundle_not_sealed')
    operands = {row['role']: row for row in job['operands']}
    if not isinstance(bundle['inputs'], list) or len(bundle['inputs']) != len(operands):
        raise ContractError('native_hmmer_original_bundle_inputs_conflict')
    seen, staged = set(), {}
    for row in bundle['inputs']:
        if (not isinstance(row, dict) or set(row) != {'role', 'format', 'original_path',
                'relative_path', 'artifact_ref', 'expected_sha256', 'actual_sha256',
                'expected_size_bytes', 'size_bytes'} or row['role'] not in operands
                or row['role'] in seen):
            raise ContractError('native_hmmer_original_bundle_input_conflict')
        original = operands[row['role']]
        for actual, expected in (('format', 'format'), ('original_path', 'path'),
                ('artifact_ref', 'artifact_ref'), ('expected_sha256', 'sha256'),
                ('expected_size_bytes', 'size_bytes')):
            if row[actual] != original[expected]:
                raise ContractError('native_hmmer_original_bundle_input_conflict')
        _sha(row['actual_sha256'], nullable=True)
        if row['size_bytes'] is not None and (type(row['size_bytes']) is not int or row['size_bytes'] < 0):
            raise ContractError('native_hmmer_bundle_size_invalid')
        seen.add(row['role'])
        staged[row['role']] = str(Path(plan['attempt_directory']) / _relative(row['relative_path']))
    from .native_hmmer_contracts import compile_native_hmmer_job
    compiled = compile_native_hmmer_job(job, input_paths=staged, output_directory=plan['attempt_directory'])
    expected_environment = {**compiled['environment'],
        **{key: str(Path(plan['attempt_directory'])/'tmp') for key in ('TMPDIR', 'TMP', 'TEMP')},
        'XDG_CACHE_HOME': str(Path(plan['attempt_directory'])/'cache')}
    if bundle['realized_argv'] != compiled['argv'] or bundle['environment'] != expected_environment:
        raise ContractError('native_hmmer_original_realized_command_conflict')
    outputs = {row['role']: row for row in job['outputs']}
    if not isinstance(bundle['artifacts'], list):
        raise ContractError('native_hmmer_bundle_artifacts_invalid')
    seen_paths, seen_roles = set(), set()
    for row in bundle['artifacts']:
        if (not isinstance(row, dict) or set(row) != {'role', 'format', 'relative_path', 'size_bytes', 'sha256'}
                or row['role'] not in outputs or row['format'] != outputs[row['role']]['format']
                or type(row['size_bytes']) is not int or row['size_bytes'] < 0):
            raise ContractError('native_hmmer_original_bundle_output_conflict')
        name = _relative(row['relative_path'])
        selected = outputs[row['role']]['relative_path']
        if row['role'] in CHECKPOINT_ROLES:
            valid_path = re.fullmatch(re.escape(selected)+r'-[1-9][0-9]*'+
                re.escape(CHECKPOINT_ROLES[row['role']]), name) is not None
        else:
            valid_path = name == selected
        if not valid_path or name in seen_paths:
            raise ContractError('native_hmmer_original_bundle_output_path_conflict')
        seen_paths.add(name)
        seen_roles.add(row['role'])
        _sha(row['sha256'])
    # Every selected output, including an optional output explicitly requested
    # by the parent, belongs to a successful complete attempt. Failed attempts
    # may truthfully retain only the files they actually produced.
    if bundle['returncode'] == 0 and not bundle['failures']:
        missing = outputs.keys() - seen_roles
        if missing:
            raise ContractError('native_hmmer_successful_bundle_missing_outputs:' + ','.join(sorted(missing)))
    return bundle


def capture_local_bundle(store, *, target, directory):
    """Stream complete sealed files, retaining mismatched bytes as failed custody."""
    if target['resource_kind'] != 'local' or not is_native_hmmer_target(target):
        raise ContractError('native_hmmer_local_capture_binding_required')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory/'capture.json'
    _immutable(directory/'capture-intent.json', {'target': target})
    if receipt.exists():
        saved = _read(receipt)
        for reference in [saved['bundle_artifact_ref'], *[row['artifact_ref']
                for row in saved['artifacts'] + saved['invalid_artifacts']]]:
            if reference is not None:
                artifact_path(store, reference)
        return saved
    plan = local_hmmer_plan(target['assignment'], target['execution_id'])
    if plan['identity']['run_id'] != target['run_id']:
        raise ContractError('native_hmmer_original_run_conflict')
    root = Path(plan['attempt_directory'])
    result = {'version': VERSION, 'bundle_artifact_ref': None, 'bundle_validated': False, 'artifacts': [],
        'invalid_artifacts': [], 'failures': [], 'complete': False}
    try:
        path = root/'bundle.json'
        if root.resolve() != root or path.resolve() != path:
            raise ContractError('native_hmmer_bundle_path_escape')
        reference = artifact_file(store, path, 'application/json')
        result['bundle_artifact_ref'] = reference
        bundle = validate_original_bundle(json.loads(store.get_artifact(reference)), plan)
        result['bundle_validated'] = True
    except (ValueError, OSError) as error:
        result['failures'].append({'stage': 'capture', 'code': str(error) if isinstance(error, ValueError)
            else 'native_hmmer_sealed_bundle_unavailable', 'record_key': None})
        _immutable(receipt, result)
        return result
    for category, rows in (('input', bundle['inputs']), ('output', bundle['artifacts'])):
        for row in rows:
            item = {key: row[key] for key in ('role', 'format', 'relative_path')}
            reference = None
            try:
                path = root/_relative(row['relative_path'])
                if path.resolve() != path or not path.is_relative_to(root) or not path.is_file():
                    raise ContractError('native_hmmer_bundle_file_unavailable_or_escaped')
                reference = artifact_file(store, path)
                captured = store.get(reference)
                expected = row['actual_sha256'] if category == 'input' else row['sha256']
                if captured['sha256'] != expected or captured['size'] != row['size_bytes']:
                    raise ContractError('native_hmmer_sealed_artifact_digest_mismatch:'+row['relative_path'])
                result['artifacts'].append({**item, 'artifact_ref': reference})
            except (ValueError, OSError) as error:
                if reference is not None:
                    result['invalid_artifacts'].append({**item, 'artifact_ref': reference})
                result['failures'].append({'stage': 'capture', 'code': str(error) if isinstance(error, ValueError)
                    else 'native_hmmer_bundle_file_unavailable:'+row['relative_path'], 'record_key': None})
    result['complete'] = not result['failures']
    _immutable(receipt, result)
    return result


def original_source_payload(*, bundle, capture, prepared):
    """Stable source content independent of acquisition page/metric selection."""
    reference = capture['bundle_artifact_ref']
    auxiliary = [row['artifact_ref'] for row in capture['artifacts']]
    auxiliary += [row['artifact_ref'] for row in capture['invalid_artifacts']]
    if prepared is not None and prepared.get('source_grading_artifact_ref') is not None:
        auxiliary.append(prepared['source_grading_artifact_ref'])
    return {'provider': PROVIDER, 'accession': 'native_hmmer_'+digest(bundle['identity']),
        'uri': None, 'artifact_ref': reference, 'text_ref': None, 'request_ref': None,
        'version': 'native_hmmer_bundle_v1', 'retrieved_at': bundle['finished_at'],
        'auxiliary_artifact_refs': sorted(set(auxiliary))}


def publish_original_source(store, *, bundle, capture, prepared):
    payload = original_source_payload(bundle=bundle, capture=capture, prepared=prepared)
    return store.put('source', payload, origin='tool')['id']


__all__ = ['capture_local_bundle', 'validate_original_bundle', 'publish_original_source',
           'original_source_payload', 'is_native_hmmer_target', 'ORIGIN', 'VERSION']
