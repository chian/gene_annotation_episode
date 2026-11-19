"""A104 native file receipt custody for masking and utility attempts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import PurePosixPath
import stat

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_contracts import finite_json_copy

def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
        allow_nan=False, indent=2) + "\n").encode("utf-8")

def _regular_reader(path):
    # O_NONBLOCK prevents a FIFO supplied as a file from hanging validation.
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("native_file_regular_file_required")
        return os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise

def _read_json(path, *, sealed=False):
    with _regular_reader(path) as stream:
        raw = stream.read()
    value = finite_json_copy(json.loads(raw))
    if sealed and raw != _encoded(value):
        raise ValueError("native_file_sealed_record_bytes_changed")
    return value

def _digest_file(path):
    hasher, size = hashlib.sha256(), 0
    with _regular_reader(path) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            hasher.update(block)
    return size, hasher.hexdigest()

def _confined_file(root, relative):
    if (type(relative) is not str or not relative or PurePosixPath(relative).is_absolute()
            or str(PurePosixPath(relative)) != relative or relative == "."
            or ".." in relative.split("/") or any(c in relative for c in ("\0", "\n", "\r", "\\"))):
        raise ValueError("native_file_artifact_path_escape")
    path = root / relative
    if path.resolve() != path or path.is_symlink() or not path.is_relative_to(root):
        raise ValueError("native_file_artifact_path_escape")
    if path.exists() and not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("native_file_artifact_not_regular_file")
    return path
