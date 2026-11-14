"""A107 NMF worker source snapshots and immutable runtime dependencies."""

import ast
from contextlib import contextmanager, ExitStack
import hashlib
import importlib
import importlib.metadata
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys

from .expression_nmf_common import require

_PACKAGES = {'jsonschema': 'jsonschema', 'attrs': 'attr', 'referencing': 'referencing',
    'rpds-py': 'rpds', 'jsonschema-specifications': 'jsonschema_specifications'}
_OPTIONAL = {'typing-extensions': 'typing_extensions', 'idna': 'idna', 'jsonpointer': 'jsonpointer',
    'fqdn': 'fqdn', 'rfc3987': 'rfc3987', 'rfc3986-validator': 'rfc3986_validator', 'rfc3987-syntax': 'rfc3987_syntax',
    'rfc3339-validator': 'rfc3339_validator', 'webcolors': 'webcolors', 'uri-template': 'uri_template',
    'isoduration': 'isoduration', 'lark': 'lark', 'arrow': 'arrow', 'python-dateutil': 'dateutil', 'six': 'six'}

def path_value(value, *, absolute):
    require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"), "invalid_output_path")
    path = PurePosixPath(value)
    require(path.is_absolute() == absolute and str(path) == value and ".." not in path.parts
        and value not in (".", "/") and not value.startswith("//"), "invalid_output_path")
    return path


def _dependency_roots(driver):
    roots = []
    for row in driver["dependencies"]:
        path = PurePosixPath(row["package_root"])
        is_package = any(p["path"] == str(path / "__init__.py") for p in row["files"])
        roots.append(str(path.parent if is_package else path))
    return list(dict.fromkeys(roots))

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

def stream_identity(stream):
    stream.seek(0)
    hasher, size = hashlib.sha256(), 0
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        hasher.update(block)
        size += len(block)
    stream.seek(0)
    return {"sha256": hasher.hexdigest(), "size_bytes": size}

def file_identity(path):
    with _regular(path) as stream:
        return stream_identity(stream)

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

def _source_closure(module_root, modules):
    root, paths, pending = Path(module_root), {}, list(modules) + ["gene_annotation_episode.__init__"]
    while pending:
        name = pending.pop()
        if name in paths:
            continue
        path = root / (name.replace(".", "/") + ".py")
        if not path.is_file() and (root / name.replace(".", "/") / "__init__.py").is_file():
            name += ".__init__"
            path = root / (name.replace(".", "/") + ".py")
        require(path.is_file(), "native_dependency_unavailable")
        paths[name] = path
        package = name.rsplit(".", 1)[0]
        parts = package.split(".")
        for length in range(1, len(parts) + 1):
            parent = ".".join(parts[:length]) + ".__init__"
            if (root / (parent.replace(".", "/") + ".py")).is_file():
                pending.append(parent)
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split(".")[:len(package.split(".")) - node.level + 1]
                    imported = ".".join([*base, *([node.module] if node.module else [])])
                else:
                    imported = node.module or ""
                if imported.startswith("gene_annotation_episode."):
                    pending.append(imported)
                    if node.module is None:
                        for alias in node.names:
                            child = imported + "." + alias.name
                            child_path = root / child.replace(".", "/")
                            if child_path.with_suffix(".py").is_file() or (child_path / "__init__.py").is_file():
                                pending.append(child)
                elif imported == "gene_annotation_episode" and node.module is None:
                    pending.extend(imported + "." + alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                pending.extend(a.name for a in node.names if a.name.startswith("gene_annotation_episode."))
    return paths

def _copy_exact(source, destination, *, executable=False):
    identity = file_identity(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        require(file_identity(destination) == identity and not destination.stat().st_mode & 0o222, 'native_dependency_unavailable')
    else:
        with _regular(source) as original, _writing(destination) as output:
            shutil.copyfileobj(original, output, length=1024 * 1024)
        if executable:
            destination.chmod(0o555)
    require(file_identity(destination) == identity, 'native_dependency_unavailable')
    return dict(path=str(destination), **identity)

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

