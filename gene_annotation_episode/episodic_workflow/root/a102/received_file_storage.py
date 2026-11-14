"""A102 received-file byte reads with stable regular-file identity."""
from contextlib import contextmanager
import os
from pathlib import Path, PurePosixPath
import stat

def require(condition, code):
    if not condition:
        raise ValueError(code)


def path_value(value, *, absolute):
    require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"), "a102_received_file_invalid_path")
    path = PurePosixPath(value)
    require(path.is_absolute() == absolute and str(path) == value and ".." not in path.parts
            and value not in (".", "/") and not value.startswith("//"), "a102_received_file_invalid_path")
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
        require(stat.S_ISREG(os.fstat(fd).st_mode), "a102_received_file_non_regular_file")
        yield stream
    finally:
        stream.close()


def _stable(before, after):
    return (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)


def read_bytes(path):
    with regular(path) as stream:
        before = os.fstat(stream.fileno())
        value = stream.read()
        require(_stable(before, os.fstat(stream.fileno())), "a102_received_file_file_changed_during_read")
        return value


