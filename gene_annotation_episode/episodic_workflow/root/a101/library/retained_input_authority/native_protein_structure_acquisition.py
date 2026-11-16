"""Retain one original protein attempt; replay uses only its captured artifacts.

Capture completeness describes byte custody. Native success, scientific parsing,
publication, received authority and episode credit belong to separate consumers.
"""
from __future__ import annotations
import json
from pathlib import Path, PurePosixPath
from typing import Literal, TypedDict
from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a101.execution_contracts import canonical, digest, validate_target
from gene_annotation_episode.episodic_workflow.root.a101.materials import artifact_path
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_protein_structure_contracts import ATTEMPT_DIRECTORY_NAME, BUNDLE_FILENAME, ManifestFile, NativeProteinRunPlan, validate_protein_structure_requested_job, validate_protein_structure_run_plan
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.protein_structure_contracts import Count, FileIdentity, StructuredIssue, same, validate_file_identity

class CapturedManifestFile(TypedDict):
    manifest_index_0based: Count
    declared: ManifestFile
    observed: FileIdentity | None
    outcome: Literal['verified', 'digest_mismatch', 'unavailable', 'declared_absent']
    issue: StructuredIssue | None

class ProteinStructureCapture(TypedDict):
    version: Literal['native_protein_structure_capture_v1']
    original_plan: NativeProteinRunPlan | None
    bundle_file: FileIdentity | None
    bundle_validated: bool
    files: list[CapturedManifestFile]
    failures: list[StructuredIssue]
    capture_complete: bool
BUNDLE_FORMAT = 'native_protein_structure_bundle_v1'

def _require(condition, code='invalid_schema'):
    if not condition:
        raise ValueError(code)

def decode_protein_structure_json(data: bytes, *, canonical_bytes: bool=False):
    """Decode strict UTF-8 JSON; canonical control bytes have no trailing LF."""
    _require(type(data) is bytes and type(canonical_bytes) is bool)

    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result)
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError('invalid_schema')
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=nonfinite)
        encoded = canonical(value).encode('utf-8')
        _require(not canonical_bytes or data == encoded)
        return value
    except (UnicodeError, ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError('invalid_schema') from error

def is_native_protein_structure_target(target: dict) -> bool:
    return type(target) is dict and target.get('resource_kind') == 'local' and (type(target.get('assignment')) is dict) and (type(target['assignment'].get('requested_job')) is dict) and ('native_protein_structure' in target['assignment']['requested_job'])

def _absolute(value):
    _require(type(value) is str and value and (not any((c in value for c in '\x00\n\r\\'))), 'invalid_output_path')
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ('..' not in path.parts) and (value != '/'), 'invalid_output_path')
    return path

def _target(value):
    target = validate_target(value)
    _require(is_native_protein_structure_target(target), 'original_commission_mismatch')
    assignment = target['assignment']
    _require(assignment.get('resource_kind') == 'local' and assignment.get('resource_id') == target['resource_id'], 'original_commission_mismatch')
    _absolute(assignment.get('workspace'))
    _absolute(target['execution_id'])
    request = validate_protein_structure_requested_job(assignment['requested_job'])
    _require(target['request_sha256'] == digest(request), 'original_commission_mismatch')
    return target

def qualify_protein_structure_target_plan(target: dict, plan: NativeProteinRunPlan) -> NativeProteinRunPlan:
    """Qualify the original target/plan relationship without filesystem reads."""
    target = _target(target)
    plan = validate_protein_structure_run_plan(plan)
    owner = plan['identity']
    _require(same(target['assignment']['requested_job'], plan['requested_job']), 'original_commission_mismatch')
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.terminal_scientific_evidence import is_terminal_target, terminal_plan_identity
    if is_terminal_target(target):
        _require(all((target[left] == owner[right] for left, right in (('run_id', 'run_id'), ('origin_episode_id', 'episode_id'), ('resource_id', 'resource_id'), ('request_sha256', 'requested_job_sha256')))) and owner['assignment_sha256'] == digest(target['assignment']) and terminal_plan_identity(owner, attempt_directory=plan['attempt_directory']), 'original_commission_mismatch')
        return plan
    _require(all((target[left] == owner[right] for left, right in (('run_id', 'run_id'), ('origin_episode_id', 'episode_id'), ('resource_id', 'resource_id'), ('execution_id', 'execution_id'), ('request_sha256', 'requested_job_sha256')))), 'original_commission_mismatch')
    root = _absolute(target['assignment']['workspace']) / '.episode-operations' / digest({'run': owner['run_id'], 'episode': owner['episode_id']}) / digest(owner['operation_key'])
    _require(owner['execution_id'] == str(root / 'native.json') and plan['attempt_directory'] == str(root / ATTEMPT_DIRECTORY_NAME), 'original_commission_mismatch')
    return plan

def retained_protein_structure_file(store, identity: FileIdentity) -> Path:
    """Validate an exact Store artifact, never a path from the original plan."""
    identity = validate_file_identity(identity)
    try:
        metadata = store._require(identity['artifact_ref'], {'artifact'})
        _require(type(metadata) is dict and set(metadata) == {'id', 'record_type', 'sha256', 'size', 'media_type'})
        _require(metadata['record_type'] == 'artifact' and type(metadata['media_type']) is str and metadata['media_type'] and ('\x00' not in metadata['media_type']))
        _require(metadata['id'] == identity['artifact_ref'] and metadata['sha256'] == identity['sha256'] and (type(metadata['size']) is int) and (metadata['size'] == identity['byte_length']), 'input_digest_mismatch')
        path = artifact_path(store, identity['artifact_ref'])
        _require(path.stat().st_size == identity['byte_length'], 'input_digest_mismatch')
        return path
    except ContractError as error:
        code = 'input_digest_mismatch' if str(error) == 'artifact_digest_mismatch' else 'retained_artifact_missing' if str(error) in ('unknown_artifact', 'unknown_reference') else 'invalid_schema'
        raise ValueError(code) from error
    except OSError as error:
        raise ValueError('retained_artifact_missing') from error

def _protein_terminal_identity(snapshot, format):
    from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.terminal_scientific_evidence import terminal_file_identity
    identity = terminal_file_identity(snapshot, format)
    identity['byte_length'] = identity.pop('size_bytes')
    return validate_file_identity(identity)

def _validate_terminal_capture_files(capture, command_proof):
    """Original retained protein identities must match the executed snapshots."""
    files = [(capture['bundle_file'], BUNDLE_FILENAME, BUNDLE_FORMAT)]
    files.extend(((row['observed'], row['declared']['relative_path'], row['declared']['format']) for row in capture['files']))
    for identity, relative, format in files:
        if identity is None:
            continue
        path = str(Path(command_proof['original_plan']['attempt_directory']) / relative)
        matches = [row for row in command_proof['output_snapshots'] if row['path'] == path]
        _require(len(matches) == 1 and matches[0]['available'] and same(identity, _protein_terminal_identity(matches[0], format)), 'input_digest_mismatch')
