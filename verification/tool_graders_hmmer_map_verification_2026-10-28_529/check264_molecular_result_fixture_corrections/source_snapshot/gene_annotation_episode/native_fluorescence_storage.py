"""Store-independent finite I/O for the selected fluorescence producer.

No decoder, scientific calculation or application authority is imported here.
Final artifacts are published atomically without replacing an existing result.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

from .fluorescence_execution_common import canonical, require


def directory(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and not str(path).startswith('//')
        and not any(c in str(path) for c in '\0\r\n\\'), 'invalid_fluorescence_path')
    for part in [*reversed(path.parents), path]:
        if part.exists() or part.is_symlink():
            require(not part.is_symlink() and part.is_dir(), 'fluorescence_non_directory_or_symlink')
    return path


def confined_file(root, relative):
    root = directory(root)
    require(type(relative) is str and relative and not any(c in relative for c in '\0\r\n\\'), 'invalid_fluorescence_path')
    leaf = Path(relative)
    require(not leaf.is_absolute() and str(leaf) == relative and '..' not in leaf.parts
        and relative != '.', 'invalid_fluorescence_path')
    directory(root / leaf.parent)
    target = root / leaf
    if target.exists() or target.is_symlink():
        require(not target.is_symlink() and target.is_file(), 'fluorescence_non_regular_or_symlink')
    return target


@contextmanager
def regular(path):
    path = Path(path)
    directory(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stream = os.fdopen(fd, 'rb')
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'fluorescence_non_regular_file')
        yield stream
    finally:
        stream.close()


def file_pin(path):
    h = hashlib.sha256()
    with regular(path) as stream:
        before = os.fstat(stream.fileno())
        while block := stream.read(1024 * 1024):
            h.update(block)
        after = os.fstat(stream.fileno())
    require((before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_ino)
        == (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino),
        'fluorescence_file_changed_during_read')
    return {'path': str(path), 'sha256': h.hexdigest(), 'size_bytes': before.st_size}


def decode_json(raw):
    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, 'duplicate_fluorescence_json_key')
            value[key] = item
        return value
    def invalid(_):
        raise ValueError('nonfinite_fluorescence_json')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read_json(path):
    with regular(path) as stream:
        return decode_json(stream.read())


def immutable_bytes(path, raw):
    require(type(raw) is bytes, 'fluorescence_bytes_required')
    path = Path(path)
    directory(path.parent)
    confined_file(path.parent, path.name)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.writing')
    try:
        with temporary.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


def immutable_json(path, value):
    """Persist a control record; numerical artifacts use immutable_bytes."""
    path = Path(path)
    raw = canonical(value) + b'\n'
    if path.exists():
        with regular(path) as stream:
            require(stream.read() == raw, 'fluorescence_immutable_record_conflict')
    else:
        immutable_bytes(path, raw)
