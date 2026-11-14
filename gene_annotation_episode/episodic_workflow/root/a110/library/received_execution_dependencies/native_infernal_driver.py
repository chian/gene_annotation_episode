from __future__ import annotations
import json
import os
from pathlib import Path, PurePosixPath
import stat
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_infernal_contracts import finite_json_copy, native_infernal_digest
_IDENTITY_FIELDS = {'run_id', 'episode_id', 'resource_id', 'execution_id', 'attempt_id', 'operation_key', 'requested_job_sha256'}

def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2) + '\n').encode('utf-8')

def _regular_reader(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError('native_infernal_regular_file_required')
        return os.fdopen(descriptor, 'rb')
    except BaseException:
        os.close(descriptor)
        raise

def _read_json(path, *, sealed=False):
    with _regular_reader(path) as stream:
        raw = stream.read()
    value = finite_json_copy(json.loads(raw))
    if sealed and raw != _encoded(value):
        raise ValueError('native_infernal_sealed_record_bytes_changed')
    return value

def _absolute_directory(value):
    if type(value) is not str or not Path(value).is_absolute() or str(Path(value)) != value or ('..' in Path(value).parts) or (value == '/') or any((c in value for c in ('\x00', '\n', '\r', '\\'))):
        raise ValueError('native_infernal_absolute_attempt_directory_required')
    root = Path(value)
    if root.resolve() != root or root.is_symlink():
        raise ValueError('native_infernal_attempt_symlink_forbidden')
    if root.exists() and (not root.is_dir()):
        raise ValueError('native_infernal_attempt_directory_required')
    return root

def _validate_identity(identity, request):
    if type(identity) is not dict or set(identity) != _IDENTITY_FIELDS or any((type(v) is not str or not v or '\x00' in v for v in identity.values())):
        raise ValueError('native_infernal_complete_attempt_identity_required')
    if identity['requested_job_sha256'] != native_infernal_digest(request):
        raise ValueError('native_infernal_requested_job_digest_mismatch')
    if identity['attempt_id'] != native_infernal_digest(identity['operation_key']):
        raise ValueError('native_infernal_attempt_operation_identity_conflict')

def _confined_file(root, relative):
    if type(relative) is not str or not relative or PurePosixPath(relative).is_absolute() or (str(PurePosixPath(relative)) != relative) or (relative == '.') or ('..' in relative.split('/')) or any((c in relative for c in ('\x00', '\n', '\r', '\\'))):
        raise ValueError('native_infernal_artifact_path_escape')
    path = root / relative
    if path.resolve() != path or path.is_symlink() or (not path.is_relative_to(root)):
        raise ValueError('native_infernal_artifact_path_escape')
    if path.exists() and (not stat.S_ISREG(path.lstat().st_mode)):
        raise ValueError('native_infernal_artifact_not_regular_file')
    return path
