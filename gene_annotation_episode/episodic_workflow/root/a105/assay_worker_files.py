"""Original private stable-byte read and exclusive-file publication primitives."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import uuid

def require(condition, code):
    if not condition:
        raise ValueError(code)

def path_value(value, *, absolute):
    require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"), "fba_invalid_path")
    path = PurePosixPath(value)
    require(path.is_absolute() == absolute and str(path) == value and ".." not in path.parts
            and value not in (".", "/") and not value.startswith("//"), "fba_invalid_path")
    return path

@contextmanager
def _directory_fd(path, *, create=False):
    path = path_value(str(path), absolute=True)
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
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
    stream = os.fdopen(fd, "rb")
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "fba_non_regular_file")
        yield stream
    finally:
        stream.close()

def _stable(before, after):
    return (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)

def file_pin(path):
    h = hashlib.sha256()
    with regular(path) as stream:
        before = os.fstat(stream.fileno())
        while block := stream.read(1024 * 1024):
            h.update(block)
        require(_stable(before, os.fstat(stream.fileno())), "fba_file_changed_during_read")
    return {"path": str(path), "sha256": h.hexdigest(), "size_bytes": before.st_size}

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

def read_bytes(path):
    with regular(path) as stream:
        before = os.fstat(stream.fileno())
        value = stream.read()
        require(_stable(before, os.fstat(stream.fileno())), "fba_file_changed_during_read")
        return value

