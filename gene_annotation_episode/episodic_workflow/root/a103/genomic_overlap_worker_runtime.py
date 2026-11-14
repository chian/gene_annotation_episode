"""A103 original genomic worker dependency and immutable file pins."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib
import importlib.metadata
import os
from pathlib import Path, PurePosixPath
import stat
import sys
from .native_driver_runtime import _DRIVER, _dependency_roots, file_identity

_PACKAGES = {'jsonschema': 'jsonschema', 'attrs': 'attr', 'referencing': 'referencing',
    'rpds-py': 'rpds', 'jsonschema-specifications': 'jsonschema_specifications'}
_OPTIONAL = {'typing-extensions': 'typing_extensions', 'idna': 'idna', 'jsonpointer': 'jsonpointer',
    'fqdn': 'fqdn', 'rfc3987': 'rfc3987', 'rfc3986-validator': 'rfc3986_validator', 'rfc3987-syntax': 'rfc3987_syntax',
    'rfc3339-validator': 'rfc3339_validator', 'webcolors': 'webcolors', 'uri-template': 'uri_template',
    'isoduration': 'isoduration', 'lark': 'lark', 'arrow': 'arrow', 'python-dateutil': 'dateutil', 'six': 'six'}

REQUIRED_DEPENDENCIES = {"jsonschema", "attrs", "referencing", "rpds-py", "jsonschema-specifications"}

def driver_runtime_schema():
    return deepcopy(_DRIVER)

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

def _dependencies():
    selected = dict(_PACKAGES)
    for module in selected.values():
        importlib.import_module(module)
    selected.update({name: module for name, module in _OPTIONAL.items() if module in sys.modules})
    result = []
    for distribution, module_name in selected.items():
        module = importlib.import_module(module_name)
        installed = importlib.metadata.distribution(distribution)
        files = []
        for entry in installed.files or ():
            path = Path(installed.locate_file(entry)).resolve(strict=True)
            if path.suffix not in ('.pyc', '.pyo') and path.is_file():
                files.append(dict(path=str(path), **file_identity(path)))
        require(files, 'native_dependency_unavailable')
        result.append(dict(distribution=distribution, version=installed.version,
            package_root=str(Path(module.__file__).resolve(strict=True).parent), files=sorted({r['path']: r for r in files}.values(), key=lambda r: r['path'])))
    return result
