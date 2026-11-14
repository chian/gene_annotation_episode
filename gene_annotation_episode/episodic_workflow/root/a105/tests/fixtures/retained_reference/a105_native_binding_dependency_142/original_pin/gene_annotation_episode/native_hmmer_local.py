"""Bind one selected HMMER producer to the existing local native lifecycle.

This module chooses no operation, retry, resource or next turn. The practical
episode owns those choices. All native inputs and outputs are captured inside
the attempt directory monitored by the existing caller-owned allocation.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys

from . import native_lifecycle as native
from .native_hmmer_contracts import validate_native_hmmer_requested_job
from .practical_execution_records import digest
from .practical_execution_state import _immutable, _read


def prepare_local_hmmer(state, operation_key, *, root, policy):
    request = validate_native_hmmer_requested_job(state.assignment['requested_job'])
    root = Path(root)
    handle = native.NativeJobHandle(root/'native.json')
    attempt = root/'hmmer-attempt'
    resource_id = state.assignment.get('resource_id')
    if not isinstance(resource_id, str) or not resource_id:
        raise ValueError('native_hmmer_resource_identity_required')
    plan = {'version': 'native_hmmer_run_plan_v1', 'identity': {
        'run_id': state.run_id, 'episode_id': state.episode_id, 'resource_id': resource_id,
        'execution_id': str(handle.path), 'attempt_id': digest(operation_key),
        'operation_key': operation_key, 'requested_job_sha256': digest(request)},
        'requested_job': request, 'attempt_directory': str(attempt),
        'policy': policy.to_dict()}
    _immutable(root/'hmmer-plan.json', plan)
    # Preserve the original selected argv/environment in the ordinary identity
    # port. The producer manifest separately records realized staged operands.
    _immutable(root/'invoke.json', {'cwd': str(attempt), 'argv': request['argv'],
        'environment': request['environment'], 'native_hmmer_plan': 'hmmer-plan.json'})
    command = [sys.executable, '-m', 'gene_annotation_episode.native_hmmer_driver',
               str(root/'hmmer-plan.json')]
    if not handle.path.exists():
        native.prepare_job(command, cwd=root, policy=policy, handle_path=handle.path,
            env={'PYTHONPATH': str(Path(__file__).resolve().parents[1]),
                 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(root),
                 'XDG_CACHE_HOME': str(root/'cache')})
    return handle


def local_hmmer_plan(assignment, execution_id):
    """Qualify the original selected plan without reading or grading results."""
    request = validate_native_hmmer_requested_job(assignment['requested_job'])
    handle = Path(execution_id)
    plan = _read(handle.parent/'hmmer-plan.json')
    owner = plan.get('identity', {})
    native_request = native.NativeJobHandle(handle).read()
    if (plan.get('version') != 'native_hmmer_run_plan_v1'
            or plan.get('requested_job') != request
            or owner.get('requested_job_sha256') != digest(request)
            or owner.get('execution_id') != str(handle)
            or owner.get('resource_id') != assignment.get('resource_id')
            or handle.parent.name != digest(owner.get('operation_key'))
            or owner.get('attempt_id') != digest(owner.get('operation_key'))
            or handle.parent.parent.name != digest({'run': owner.get('run_id'),
                                                    'episode': owner.get('episode_id')})
            or native_request.get('command') != [sys.executable, '-m',
                'gene_annotation_episode.native_hmmer_driver', str(handle.parent/'hmmer-plan.json')]
            or native_request.get('cwd') != str(handle.parent)
            or native_request.get('metadata', {}).get('policy') != plan.get('policy')
            or plan.get('attempt_directory') != str(handle.parent/'hmmer-attempt')):
        raise ValueError('native_hmmer_original_attempt_conflict')
    attempt_owner = Path(plan['attempt_directory'])/'.native-hmmer-owner.json'
    if attempt_owner.exists() and json.loads(attempt_owner.read_bytes()) != plan:
        raise ValueError('native_hmmer_original_attempt_owner_conflict')
    return plan


__all__ = ['prepare_local_hmmer', 'local_hmmer_plan']
