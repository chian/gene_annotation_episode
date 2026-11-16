"""Exact source-closure and immutable file-copy infrastructure for native workers.

These utilities preserve the original source and file custody checks. They do
not import a scientific driver, calculator, episode policy, or provider.
"""
from contextlib import ExitStack, contextmanager
import ast
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat


def _file_require(condition, code="original_attempt_mismatch"):
    if not condition:
        raise ValueError(code)


def path_value(value, *, absolute):
    _file_require(type(value) is str and value and not any(c in value for c in "\0\r\n\\"), "invalid_output_path")
    path = PurePosixPath(value)
    _file_require(path.is_absolute() == absolute and str(path) == value and ".." not in path.parts
        and value not in (".", "/") and not value.startswith("//"), "invalid_output_path")
    return path


def _source_require(condition, code='atac_result_record_mismatch'):
    if not condition:
        raise ValueError(code)


def _directory(value):
    path = Path(path_value(str(value), absolute=True))
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        _file_require(stat.S_ISDIR(mode), "invalid_output_path")
    return path


def confined_file(directory, relative_path):
    path = _directory(directory) / str(path_value(relative_path, absolute=False))
    _directory(path.parent)
    try:
        _file_require(stat.S_ISREG(path.lstat().st_mode), "invalid_output_path")
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
        _file_require(stat.S_ISREG(os.fstat(descriptor).st_mode), "input_unavailable")
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
    root, paths, pending = Path(module_root), {}, [*modules, 'gene_annotation_episode.__init__']
    while pending:
        name = pending.pop()
        if name in paths:
            continue
        path = root / (name.replace('.', '/') + '.py')
        if not path.is_file() and (root / name.replace('.', '/') / '__init__.py').is_file():
            name += '.__init__'
            path = root / (name.replace('.', '/') + '.py')
        _source_require(path.is_file(), 'native_dependency_unavailable')
        paths[name] = path
        package = name.rsplit('.', 1)[0]
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if isinstance(node, ast.ImportFrom):
                base = package.split('.')[:len(package.split('.')) - node.level + 1] if node.level else []
                imported = '.'.join([*base, *([node.module] if node.module else [])])
                if imported.startswith('gene_annotation_episode.'):
                    pending.append(imported)
                elif imported == 'gene_annotation_episode' and node.module is None:
                    pending.extend(imported + '.' + alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                pending.extend(alias.name for alias in node.names if alias.name.startswith('gene_annotation_episode.'))
    return paths


def _copy_exact(source, destination, *, executable=False):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        with _regular(source) as original, _regular(destination) as existing:
            _source_require(original.read() == existing.read() and not destination.stat().st_mode & 0o222, 'native_dependency_unavailable')
    else:
        with _regular(source) as original, _writing(destination) as output:
            shutil.copyfileobj(original, output, length=1024 * 1024)
        if executable:
            destination.chmod(0o555)
    return dict(path=str(destination))


