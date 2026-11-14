"""A104 private immutable controls for exact-file capture receipts."""
from __future__ import annotations
from contextlib import ExitStack, contextmanager
import json
import math
import os
from pathlib import Path, PurePosixPath
import secrets
import stat
from typing import Any
from .execution_contracts import canonical

def _finite_json_copy(value: object) -> Any:
    """Copy JSON without scalar coercion, nonfinite numbers or non-JSON objects."""
    if value is None or type(value) in {str, bool, int}:
        if type(value) is str:
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as error:
                raise ValueError("a104_file_capture_invalid_unicode") from error
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_finite_json_copy(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {_finite_json_copy(key): _finite_json_copy(item) for key, item in value.items()}
    raise ValueError("a104_file_capture_finite_json_required")


def require(condition, code="a104_file_capture_result_authority_conflict"):
    if not condition:
        raise ValueError(code)


def closed(value, fields):
    require(type(value) is dict and set(value) == set(fields), "a104_file_capture_result_invalid_record")


def same(left, right):
    return canonical(left) == canonical(right)


def decode(raw, *, newline=False, canonical_bytes=True):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "a104_file_capture_result_duplicate_key")
            result[key] = value
        return result
    value = _finite_json_copy(json.loads(raw.decode("utf-8"), object_pairs_hook=pairs))
    require(not canonical_bytes or raw == canonical(value).encode("utf-8") + (b"\n" if newline else b""),
            "a104_file_capture_result_noncanonical_control")
    return value


@contextmanager
def directory(path, *, create=False):
    value = str(path)
    pure = PurePosixPath(value)
    require(pure.is_absolute() and str(pure) == value and value != "/" and ".." not in pure.parts
            and not any(c in value for c in "\0\r\n\\"), "a104_file_capture_result_invalid_path")
    with ExitStack() as stack:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        stack.callback(os.close, fd)
        for part in pure.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            stack.callback(os.close, fd)
        require(os.fstat(fd).st_uid == os.geteuid(), "a104_file_capture_result_invalid_path")
        yield fd


@contextmanager
def regular(fd, name, *, flags=os.O_RDONLY):
    require(type(name) is str and name not in ("", ".", "..") and "/" not in name)
    handle = os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        require(stat.S_ISREG(os.fstat(handle).st_mode), "a104_file_capture_result_invalid_path")
        yield handle
    finally:
        os.close(handle)


def read_control(path):
    try:
        with directory(path.parent) as fd, regular(fd, path.name) as handle, os.fdopen(os.dup(handle), "rb") as stream:
            raw = stream.read()
    except FileNotFoundError:
        return None
    return decode(raw, newline=path.name == "assignment.json" and raw.endswith(b"\n"))


def immutable(path, value):
    value = _finite_json_copy(value)
    with directory(path.parent, create=True) as fd:
        previous = read_control(path)
        if previous is not None:
            require(same(previous, value), "a104_file_capture_result_control_conflict")
            return
        temporary = "." + path.name + "." + secrets.token_hex(16) + ".writing"
        try:
            with regular(fd, temporary, flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL) as handle:
                with os.fdopen(os.dup(handle), "wb") as stream:
                    stream.write(canonical(value).encode("utf-8") + (b"\n" if path.name == "assignment.json" else b""))
                    stream.flush()
                os.fchmod(handle, 0o444)
                os.fsync(handle)
            try:
                os.link(temporary, path.name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            except FileExistsError:
                require(same(read_control(path), value), "a104_file_capture_result_control_conflict")
            os.fsync(fd)
        finally:
            os.unlink(temporary, dir_fd=fd)


