"""Private original assay file/attempt controls, without a native assay dispatcher."""
from contextlib import ExitStack, contextmanager, asynccontextmanager
import asyncio
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat

def require(condition, code="original_attempt_mismatch"):
    if not condition:
        raise ValueError(code)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def path_value(value, *, absolute):
    require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"), "invalid_output_path")
    path = PurePosixPath(value)
    require(path.is_absolute() == absolute and str(path) == value and ".." not in path.parts
        and value not in (".", "/") and not value.startswith("//"), "invalid_output_path")
    return path

def _directory(value):
    path = Path(path_value(str(value), absolute=True))
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        require(stat.S_ISDIR(mode), "invalid_output_path")
    return path

def confined_file(directory, relative_path):
    path = _directory(directory) / str(path_value(relative_path, absolute=False))
    _directory(path.parent)
    try:
        require(stat.S_ISREG(path.lstat().st_mode), "invalid_output_path")
    except FileNotFoundError:
        pass
    return path

@contextmanager
def _regular(value):
    path = Path(path_value(str(value), absolute=True))
    with ExitStack() as stack:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptor = os.open("/", flags)
        stack.callback(os.close, descriptor)
        for part in path.parts[1:-1]:
            descriptor = os.open(part, flags, dir_fd=descriptor)
            stack.callback(os.close, descriptor)
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=descriptor)
        stack.callback(os.close, descriptor)
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), "input_unavailable")
        with os.fdopen(os.dup(descriptor), "rb") as stream:
            yield stream

def decode_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "invalid_native_control_json")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("invalid_native_control_json")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid_native_control_json") from error

def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def _publish(temporary, destination):
    os.chmod(temporary, 0o444)
    os.link(temporary, destination)
    _sync_directory(destination.parent)
    temporary.unlink()
    _sync_directory(destination.parent)

@contextmanager
def _writing(path):
    path = confined_file(path.parent, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = confined_file(path.parent, "." + path.name + ".writing")
    with temporary.open("xb") as stream:
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

@asynccontextmanager
async def _action_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(root / ".action.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    task = asyncio.create_task(asyncio.to_thread(fcntl.flock, descriptor, fcntl.LOCK_EX))
    acquired = False
    try:
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    pass
            task.result()
            acquired = True
            raise
        acquired = True
        yield
    finally:
        if acquired:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

