"""A107 native atac differential driver."""


from __future__ import annotations
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.atac_execution_contracts import canonical, require, path_value

def _directory(value):
    path = Path(path_value(str(value), absolute=True))
    current = Path('/')
    for part in path.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        require(stat.S_ISDIR(mode), 'invalid_output_path')
    return path

def confined_file(directory, relative_path):
    path = _directory(directory) / str(path_value(relative_path, absolute=False))
    _directory(path.parent)
    try:
        require(stat.S_ISREG(path.lstat().st_mode), 'invalid_output_path')
    except FileNotFoundError:
        pass
    return path

@contextmanager
def _regular(value):
    path = Path(path_value(str(value), absolute=True))
    with ExitStack() as stack:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptor = os.open('/', flags)
        stack.callback(os.close, descriptor)
        for part in path.parts[1:-1]:
            descriptor = os.open(part, flags, dir_fd=descriptor)
            stack.callback(os.close, descriptor)
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=descriptor)
        stack.callback(os.close, descriptor)
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), 'input_unavailable')
        with os.fdopen(os.dup(descriptor), 'rb') as stream:
            yield stream

def stream_identity(stream):
    stream.seek(0)
    hasher, size = (hashlib.sha256(), 0)
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        hasher.update(block)
        size += len(block)
    stream.seek(0)
    return {'sha256': hasher.hexdigest(), 'size_bytes': size}

def file_identity(path):
    with _regular(path) as stream:
        return stream_identity(stream)

def decode_json(raw):

    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'invalid_native_control_json')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('invalid_native_control_json')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('invalid_native_control_json') from error

def _read_control(path):
    with _regular(path) as stream:
        raw = stream.read()
    value = decode_json(raw)
    require(raw in (canonical(value), canonical(value) + b'\n'), 'original_attempt_mismatch')
    return value

def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def _publish(temporary, destination):
    os.chmod(temporary, 292)
    os.link(temporary, destination)
    _sync_directory(destination.parent)
    temporary.unlink()
    _sync_directory(destination.parent)

@contextmanager
def _writing(path):
    path = confined_file(path.parent, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = confined_file(path.parent, '.' + path.name + '.writing')
    with temporary.open('xb') as stream:
        yield stream
        stream.flush()
        os.fsync(stream.fileno())
    _publish(temporary, path)

def _immutable(path, value):
    raw = canonical(value)
    if path.exists():
        with _regular(path) as stream:
            require(stream.read() == raw)
        return
    with _writing(path) as stream:
        stream.write(raw)
