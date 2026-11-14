"""Original confined native-file publication and strict JSON decoding."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid
from .record_serialization import canonical
from .retained_file_read import path_value, require, _directory_fd, regular, _stable, read_bytes

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
        require(stat.S_ISREG(observed.st_mode), "fba_non_regular_or_symlink")
    return target

@contextmanager
def _exclusive_output(path):
    path = Path(path_value(str(path), absolute=True))
    with _directory_fd(path.parent, create=True) as parent:
        temporary = ".fba-writing-" + uuid.uuid4().hex
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        # On failure the explicitly named unfinished bytes stay in the attempt.
        with os.fdopen(fd, "wb") as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o444)
        os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        os.unlink(temporary, dir_fd=parent)
        os.fsync(parent)

def immutable_bytes(path, raw):
    require(type(raw) is bytes, "fba_bytes_required")
    with _exclusive_output(path) as stream:
        stream.write(raw)

def immutable_json(path, value):
    immutable_bytes(path, canonical(value).encode("utf-8") + b"\n")

def retain_input(source, target, *, max_bytes):
    """One stable streaming read and exclusive publication of the actual bytes."""
    h = hashlib.sha256()
    size = 0
    with regular(source) as original, _exclusive_output(target) as output:
        before = os.fstat(original.fileno())
        require(before.st_size <= max_bytes, "fba_input_exceeds_scratch_limit")
        while block := original.read(1024 * 1024):
            size += len(block)
            require(size <= max_bytes, "fba_input_exceeds_scratch_limit")
            h.update(block)
            output.write(block)
        require(_stable(before, os.fstat(original.fileno())) and size == before.st_size, "fba_file_changed_during_read")
    return {"sha256": h.hexdigest(), "size_bytes": size}

def decode_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "fba_duplicate_json_key")
            result[key] = value
        return result
    def nonfinite(_):
        raise ValueError("fba_nonfinite_json")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)

def read_json(path):
    return decode_json(read_bytes(path))
