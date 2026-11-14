"""Private original A101 worker-source and interpreter custody helpers."""
from __future__ import annotations
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import ast
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import sys
from jsonschema import Draft202012Validator
from .local_jobs import LocalJobPolicy, check_scratch_budget

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

def _obj(**properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}

def _arr(items, **kwargs):
    return {"type": "array", "items": items, **kwargs}

_TEXT = {"type": "string", "minLength": 1, "maxLength": 4096, "pattern": r"^[^\x00-\x1f\x7f]+$"}
_ID = {"type": "string", "minLength": 1, "maxLength": 512, "pattern": r"^[A-Za-z0-9_.:/@+\-]+$"}
_SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_INT = {"type": "integer", "minimum": 0}

_PIN = _obj(path=_TEXT, sha256=_SHA, size_bytes=_INT)
_DRIVER = _obj(python_executable=_TEXT, python_sha256=_SHA, python_version=_ID, module_root=_TEXT,
    implementation_files=_arr(_obj(module=_ID, sha256=_SHA), minItems=1),
    dependencies=_arr(_obj(distribution=_ID, version=_TEXT, package_root=_TEXT, files=_arr(_PIN, minItems=1)), minItems=1))
_SCHEMAS = {"DriverRuntime": _DRIVER}

def _validate_record(kind, value):
    try:
        canonical(value)
        Draft202012Validator(_SCHEMAS[kind]).validate(value)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid_atac_" + kind.lower()) from error
    except Exception as error:
        from jsonschema.exceptions import ValidationError
        if not isinstance(error, ValidationError):
            raise
        raise ValueError("invalid_atac_" + kind.lower()) from error
    return deepcopy(value)

def validate_driver_runtime(value, *, required_modules=(), required_dependencies=()):
    """Validate supplied driver metadata without inspecting current files."""
    driver = _validate_record("DriverRuntime", value)
    for required in (required_modules, required_dependencies):
        require(type(required) in (tuple, list, set, frozenset)
            and all(type(name) is str and bool(name) for name in required), "native_dependency_unavailable")
    path_value(driver["python_executable"], absolute=True)
    path_value(driver["module_root"], absolute=True)
    names = [r["module"] for r in driver["implementation_files"]]
    require(len(names) == len(set(names)) and set(required_modules) <= set(names), "native_dependency_unavailable")
    require(all(re.fullmatch(r"gene_annotation_episode(?:\.[A-Za-z_]\w*)+", n, re.ASCII) for n in names), "native_dependency_unavailable")
    dependencies = driver["dependencies"]
    names = [r["distribution"].lower().replace("_", "-") for r in dependencies]
    required_names = {name.lower().replace("_", "-") for name in required_dependencies}
    require(len(names) == len(set(names)) and required_names <= set(names), "native_dependency_unavailable")
    for row in dependencies:
        path_value(row["package_root"], absolute=True)
    for pins in (r["files"] for r in dependencies):
        paths = [str(path_value(r["path"], absolute=True)) for r in pins]
        require(len(paths) == len(set(paths)), "native_dependency_unavailable")
    return driver

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

def verify_driver_runtime(driver):
    """Verify the selected Python, implementation and dependency file closure."""
    driver = validate_driver_runtime(driver)
    selected = Path(driver["python_executable"]).resolve(strict=True)
    require(os.path.samefile(selected, "/proc/self/exe") and
        file_identity(selected)["sha256"] == driver["python_sha256"] and
        platform.python_version() == driver["python_version"], "native_dependency_unavailable")
    for row in driver["implementation_files"]:
        path = confined_file(driver["module_root"], row["module"].replace(".", "/") + ".py")
        require(file_identity(path)["sha256"] == row["sha256"], "native_dependency_unavailable")
        loaded = sys.modules.get(row["module"])
        if loaded is not None:
            require(Path(loaded.__file__) == path, "native_dependency_unavailable")
    module_names = {"rpds-py": "rpds", "jsonschema-specifications": "jsonschema_specifications", "attrs": "attr", "python-dateutil": "dateutil", "fair-esm": "esm"}
    for dependency in driver["dependencies"]:
        name = dependency["distribution"]
        require(importlib.metadata.version(name) == dependency["version"], "native_dependency_unavailable")
        module = importlib.import_module(module_names.get(name, name.replace("-", "_")))
        require(Path(module.__file__).parent == Path(dependency["package_root"]), "native_dependency_unavailable")
        for pin in dependency["files"]:
            require(file_identity(pin["path"]) == {k: pin[k] for k in ("sha256", "size_bytes")}, "native_dependency_unavailable")
    pinned = {p["path"] for row in driver["dependencies"] for p in row["files"]}
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename and "site-packages" in Path(filename).parts:
            require(str(Path(filename).resolve(strict=True)) in pinned, "native_dependency_unavailable")

_PACKAGES = {"jsonschema": "jsonschema", "attrs": "attr", "referencing": "referencing", "rpds-py": "rpds",
    "jsonschema-specifications": "jsonschema_specifications"}
_OPTIONAL = {"typing-extensions": "typing_extensions", "idna": "idna", "jsonpointer": "jsonpointer", "fqdn": "fqdn",
    "rfc3987": "rfc3987", "rfc3986-validator": "rfc3986_validator", "rfc3987-syntax": "rfc3987_syntax",
    "rfc3339-validator": "rfc3339_validator", "webcolors": "webcolors", "uri-template": "uri_template",
    "isoduration": "isoduration", "lark": "lark", "arrow": "arrow", "python-dateutil": "dateutil", "six": "six"}


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
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split(".")[:len(package.split(".")) - node.level + 1]
                    imported = ".".join([*base, *([node.module] if node.module else [])])
                else:
                    imported = node.module or ""
                if imported == "gene_annotation_episode" or imported.startswith("gene_annotation_episode."):
                    pending.append(imported)
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        member = imported + "." + alias.name
                        member_path = root / member.replace(".", "/")
                        if member_path.with_suffix(".py").is_file() or (member_path / "__init__.py").is_file():
                            pending.append(member)
            elif isinstance(node, ast.Import):
                pending.extend(a.name for a in node.names if a.name.startswith("gene_annotation_episode."))
    return paths

def _copy_exact(source, destination):
    identity = file_identity(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        require(file_identity(destination) == identity and not destination.stat().st_mode & 0o222)
    else:
        with _regular(source) as original, _writing(destination) as target:
            shutil.copyfileobj(original, target, length=1024 * 1024)
    require(file_identity(destination) == identity)
    return {"path": str(destination), **identity}

def _dependency_bindings(*, contained_records=False, exclusions=None):
    selected, result = dict(_PACKAGES), []
    for module in selected.values():
        importlib.import_module(module)
    selected.update({name: module for name, module in _OPTIONAL.items() if module in sys.modules})
    for distribution, module_name in selected.items():
        module = importlib.import_module(module_name)
        installed = importlib.metadata.distribution(distribution)
        if contained_records:
            require(type(contained_records) is bool and (exclusions is None or type(exclusions) is list),
                "native_dependency_unavailable")
            distribution_root = Path(installed.locate_file("")).resolve(strict=True)
        files = []
        for entry in installed.files or ():
            if contained_records:
                # RECORD may name console scripts outside a copied distribution
                # root and bytecode deliberately absent from a -B deployment.
                # Neither is an imported package/runtime operand. Missing or
                # escaping retained files inside the selected root still fail.
                candidate = Path(os.path.abspath(installed.locate_file(entry)))
                reason = ("outside_distribution_root" if not candidate.is_relative_to(distribution_root)
                          else "non_runtime_bytecode" if candidate.suffix in (".pyc", ".pyo") else None)
                if reason is not None:
                    if exclusions is not None:
                        exclusions.append({"distribution": distribution, "record_path": str(entry),
                            "declared_path": str(candidate), "reason": reason})
                    continue
                path = candidate.resolve(strict=True)
                require(path.is_relative_to(distribution_root), "native_dependency_unavailable")
            else:
                path = Path(installed.locate_file(entry)).resolve(strict=True)
            if path.suffix in (".pyc", ".pyo") or not path.is_file():
                continue
            files.append({"path": str(path), **file_identity(path)})
        require(bool(files), "native_dependency_unavailable")
        result.append({"distribution": distribution, "version": installed.version,
            "package_root": str(Path(module.__file__).resolve(strict=True).parent),
            "files": sorted({r["path"]: r for r in files}.values(), key=lambda r: r["path"])})
    return result

def freeze_driver_runtime(*, module_root, snapshot_directory, driver_modules, policy,
        contained_dependency_records=False, dependency_exclusions=None):
    """Copy the selected driver closure during explicit bounded preparation.

    This records the current interpreter and installed driver dependencies. It
    does not import, install or select a native scientific implementation.
    """
    require(type(policy) is LocalJobPolicy, "native_dependency_unavailable")
    require(type(contained_dependency_records) is bool and (dependency_exclusions is None
        or type(dependency_exclusions) is list), "native_dependency_unavailable")
    require(type(driver_modules) in (tuple, list) and bool(driver_modules) and all(type(name) is str
        and name.startswith('gene_annotation_episode.') and all(part.isidentifier() for part in name.split('.'))
        for name in driver_modules), 'native_dependency_unavailable')
    target = _directory(snapshot_directory)
    target.mkdir(parents=True, exist_ok=True)
    modules = _source_closure(module_root, driver_modules)
    implementation = []
    for name, source in sorted(modules.items()):
        check_scratch_budget(target, policy, additional_bytes=source.stat().st_size)
        pin = _copy_exact(source, target / (name.replace(".", "/") + ".py"))
        implementation.append({"module": name, "sha256": pin["sha256"]})
    return validate_driver_runtime(dict(python_executable=sys.executable,
        python_sha256=file_identity(Path(sys.executable).resolve(strict=True))["sha256"],
        python_version=platform.python_version(), module_root=str(target), implementation_files=implementation,
        dependencies=(_dependency_bindings(contained_records=True, exclusions=dependency_exclusions)
            if contained_dependency_records else _dependency_bindings())))

