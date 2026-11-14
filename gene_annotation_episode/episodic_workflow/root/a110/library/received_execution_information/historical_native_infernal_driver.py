"""Produce the retained files from one selected Infernal invocation.

The existing native lifecycle owns process lifetime and the supplied allocation.
This module stages exact inputs, invokes one command, and seals its original
outcome. It does not grade, poll, retry, prepare indexes, or select resources.
An interrupted, unsealed attempt is uncertain and is never invoked again.
"""
from __future__ import annotations
import json
import os
from pathlib import PurePosixPath
import stat
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_infernal_contracts import finite_json_copy

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

def _confined_file(root, relative):
    if type(relative) is not str or not relative or PurePosixPath(relative).is_absolute() or (str(PurePosixPath(relative)) != relative) or (relative == '.') or ('..' in relative.split('/')) or any((c in relative for c in ('\x00', '\n', '\r', '\\'))):
        raise ValueError('native_infernal_artifact_path_escape')
    path = root / relative
    if path.resolve() != path or path.is_symlink() or (not path.is_relative_to(root)):
        raise ValueError('native_infernal_artifact_path_escape')
    if path.exists() and (not stat.S_ISREG(path.lstat().st_mode)):
        raise ValueError('native_infernal_artifact_not_regular_file')
    return path
