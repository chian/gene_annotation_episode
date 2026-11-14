"""Confined immutable FBA bytes; this module grants no execution authority."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.native_flux_balance_contracts import path_value, require

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

def read_bytes(path):
    with regular(path) as stream:
        before = os.fstat(stream.fileno())
        value = stream.read()
        require(_stable(before, os.fstat(stream.fileno())), 'fba_file_changed_during_read')
        return value

def read_json(path):
    return decode_json(read_bytes(path))
