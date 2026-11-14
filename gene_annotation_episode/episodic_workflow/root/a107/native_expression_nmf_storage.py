"""Finite native artifact I/O used only by the NMF driver/explicit loader.

File reads reject symlinks in all path components and retain full bytes. These
identities establish byte relationships, never episode ownership.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat

from .expression_nmf_common import canonical, require


def directory(path):
    path = Path(path)
    require(path.is_absolute() and str(path) == str(path.absolute()) and '..' not in path.parts, 'invalid_nmf_path')
    for part in [*reversed(path.parents), path]:
        if part.exists() or part.is_symlink():
            require(not part.is_symlink() and part.is_dir(), 'nmf_non_directory_or_symlink')
    return path


def confined_file(root, relative):
    root = directory(root)
    leaf = Path(relative)
    require(not leaf.is_absolute() and str(leaf) == relative and '..' not in leaf.parts
        and relative not in ('.', '') and '\\' not in relative, 'invalid_nmf_path')
    directory(root / leaf.parent)
    target = root / leaf
    if target.exists() or target.is_symlink():
        require(not target.is_symlink() and target.is_file(), 'nmf_non_regular_or_symlink')
    return target


@contextmanager
def regular(path):
    path = Path(path)
    directory(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    stream = os.fdopen(fd, 'rb')
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'nmf_non_regular_file')
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
    require((before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino),
        'nmf_file_changed_during_read')
    return {'path': str(path), 'sha256': h.hexdigest(), 'size_bytes': before.st_size}


def decode_json(raw):
    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, 'duplicate_nmf_json_key')
            value[key] = item
        return value
    def invalid(_):
        raise ValueError('nonfinite_nmf_json')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read_json(path):
    with regular(path) as stream:
        return decode_json(stream.read())


def immutable_bytes(path, raw):
    path = Path(path)
    directory(path.parent)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def immutable_json(path, value):
    path = Path(path)
    raw = canonical(value) + b'\n'
    if path.exists():
        with regular(path) as stream:
            require(stream.read() == raw, 'nmf_immutable_record_conflict')
    else:
        immutable_bytes(path, raw)
