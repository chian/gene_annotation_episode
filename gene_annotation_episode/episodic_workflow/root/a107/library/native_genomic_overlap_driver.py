"""A107 result worker dependency: native_genomic_overlap_driver."""


from __future__ import annotations
from contextlib import ExitStack, contextmanager
import json
import os
from pathlib import Path, PurePosixPath
import stat
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical

def _require(condition, code='original_attempt_mismatch'):
    if not condition:
        raise ValueError(code)

def _path(value, *, absolute):
    _require(type(value) is str and value and (not any((c in value for c in '\x00\n\r\\'))), 'invalid_output_path')
    path = PurePosixPath(value)
    _require(str(path) == value and '..' not in path.parts and (path.is_absolute() == absolute) and (value not in {'.', '/'}), 'invalid_output_path')
    return Path(value)

def _directory(value):
    path = _path(str(value), absolute=True)
    current = Path('/')
    for part in path.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        _require(stat.S_ISDIR(mode), 'invalid_output_path')
    return path

def confined_file(directory, relative_path):
    directory = _directory(directory)
    path = directory / _path(relative_path, absolute=False)
    _directory(path.parent)
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return path
    _require(stat.S_ISREG(mode), 'invalid_output_path')
    return path

@contextmanager
def _regular(value):
    """Pin every directory and the regular endpoint without following symlinks."""
    path = _path(str(value), absolute=True)
    with ExitStack() as stack:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        fd = os.open('/', flags)
        stack.callback(os.close, fd)
        for part in path.parts[1:-1]:
            fd = os.open(part, flags, dir_fd=fd)
            stack.callback(os.close, fd)
        fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=fd)
        stack.callback(os.close, fd)
        _require(stat.S_ISREG(os.fstat(fd).st_mode), 'invalid_output_path')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            yield stream

def _decode(raw):

    def pairs(rows):
        value = {}
        for key, item in rows:
            _require(key not in value, 'invalid_native_control_json')
            value[key] = item
        return value

    def constant(_):
        raise ValueError('invalid_native_control_json')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('invalid_native_control_json') from error

def _strict_json(path):
    with _regular(path) as stream:
        return _decode(stream.read())

def _read_control(path):
    with _regular(path) as stream:
        raw = stream.read()
    value = _decode(raw)
    _require(raw == (canonical(value) + '\n').encode('utf-8'), 'original_attempt_mismatch')
    return value
