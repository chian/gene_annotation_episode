"""Confined immutable FBA bytes; this module grants no execution authority."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import stat
from .library.received_execution_information.historical_flux_balance_paths import path_value, require

@contextmanager
def _directory_fd(path, *, create=False):
    path = path_value(str(path), absolute=True)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, mode=448, dir_fd=fd)
                except FileExistsError:
                    pass
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)

@contextmanager
def regular(path):
    path = Path(path_value(str(path), absolute=True))
    with _directory_fd(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    stream = os.fdopen(fd, 'rb')
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'fba_non_regular_file')
        yield stream
    finally:
        stream.close()

def _stable(before, after):
    return (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)

def file_pin(path):
    h = hashlib.sha256()
    with regular(path) as stream:
        before = os.fstat(stream.fileno())
        while (block := stream.read(1024 * 1024)):
            h.update(block)
        require(_stable(before, os.fstat(stream.fileno())), 'fba_file_changed_during_read')
    return {'path': str(path), 'sha256': h.hexdigest(), 'size_bytes': before.st_size}

def read_bytes(path):
    with regular(path) as stream:
        before = os.fstat(stream.fileno())
        value = stream.read()
        require(_stable(before, os.fstat(stream.fileno())), 'fba_file_changed_during_read')
        return value


import json

def decode_json(raw):

    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'fba_duplicate_json_key')
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError('fba_nonfinite_json')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


import uuid

def directory(path, *, create=False):
    with _directory_fd(path, create=create):
        pass
    return Path(path)

def confined_file(root, relative, *, create_parents=False):
    root = path_value(str(root), absolute=True)
    relative = path_value(relative, absolute=False)
    target = Path(root / relative)
    with _directory_fd(target.parent, create=create_parents) as fd:
        try:
            observed = os.stat(target.name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return target
        require(stat.S_ISREG(observed.st_mode), 'fba_non_regular_or_symlink')
    return target

@contextmanager
def _exclusive_output(path):
    path = Path(path_value(str(path), absolute=True))
    with _directory_fd(path.parent, create=True) as parent:
        temporary = '.fba-writing-' + uuid.uuid4().hex
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 384, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 292)
        os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        os.unlink(temporary, dir_fd=parent)
        os.fsync(parent)

def immutable_bytes(path, raw):
    require(type(raw) is bytes, 'fba_bytes_required')
    with _exclusive_output(path) as stream:
        stream.write(raw)

def read_json(path):
    return decode_json(read_bytes(path))


from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical

def immutable_json(path, value):
    immutable_bytes(path, canonical(value).encode('utf-8') + b'\n')
