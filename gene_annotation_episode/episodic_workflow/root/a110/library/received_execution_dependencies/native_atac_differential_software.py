from __future__ import annotations
import ast
import importlib
import importlib.metadata
import os
from pathlib import Path
import platform
import shutil
import sys
from gene_annotation_episode.episodic_workflow.root.a110.local_jobs import LocalJobPolicy, check_scratch_budget
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_atac_differential_contracts import require, validate_driver_runtime
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_atac_differential_driver import _directory, _regular, _writing
_PACKAGES = {'jsonschema': 'jsonschema', 'attrs': 'attr', 'referencing': 'referencing', 'rpds-py': 'rpds', 'jsonschema-specifications': 'jsonschema_specifications'}
_OPTIONAL = {'typing-extensions': 'typing_extensions', 'idna': 'idna', 'jsonpointer': 'jsonpointer', 'fqdn': 'fqdn', 'rfc3987': 'rfc3987', 'rfc3986-validator': 'rfc3986_validator', 'rfc3987-syntax': 'rfc3987_syntax', 'rfc3339-validator': 'rfc3339_validator', 'webcolors': 'webcolors', 'uri-template': 'uri_template', 'isoduration': 'isoduration', 'lark': 'lark', 'arrow': 'arrow', 'python-dateutil': 'dateutil', 'six': 'six'}

def _source_closure(module_root, modules):
    root, paths, pending = (Path(module_root), {}, list(modules) + ['gene_annotation_episode.__init__'])
    while pending:
        name = pending.pop()
        if name in paths:
            continue
        path = root / (name.replace('.', '/') + '.py')
        if not path.is_file() and (root / name.replace('.', '/') / '__init__.py').is_file():
            name += '.__init__'
            path = root / (name.replace('.', '/') + '.py')
        require(path.is_file(), 'native_dependency_unavailable')
        paths[name] = path
        package = name.rsplit('.', 1)[0]
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split('.')[:len(package.split('.')) - node.level + 1]
                    imported = '.'.join([*base, *([node.module] if node.module else [])])
                else:
                    imported = node.module or ''
                if imported.startswith('gene_annotation_episode.'):
                    pending.append(imported)
                elif imported == 'gene_annotation_episode' and node.module is None:
                    pending.extend((imported + '.' + alias.name for alias in node.names))
            elif isinstance(node, ast.Import):
                pending.extend((a.name for a in node.names if a.name.startswith('gene_annotation_episode.')))
    return paths

def _copy_exact(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        with _regular(source) as original, _regular(destination) as existing:
            require(original.read() == existing.read() and (not destination.stat().st_mode & 146))
    else:
        with _regular(source) as original, _writing(destination) as target:
            shutil.copyfileobj(original, target, length=1024 * 1024)
    return {'path': str(destination)}

def _dependency_bindings(*, contained_records=False, exclusions=None):
    selected, result = (dict(_PACKAGES), [])
    for module in selected.values():
        importlib.import_module(module)
    selected.update({name: module for name, module in _OPTIONAL.items() if module in sys.modules})
    for distribution, module_name in selected.items():
        module = importlib.import_module(module_name)
        installed = importlib.metadata.distribution(distribution)
        if contained_records:
            require(type(contained_records) is bool and (exclusions is None or type(exclusions) is list), 'native_dependency_unavailable')
            distribution_root = Path(installed.locate_file('')).resolve(strict=True)
        files = []
        for entry in installed.files or ():
            if contained_records:
                candidate = Path(os.path.abspath(installed.locate_file(entry)))
                reason = 'outside_distribution_root' if not candidate.is_relative_to(distribution_root) else 'non_runtime_bytecode' if candidate.suffix in ('.pyc', '.pyo') else None
                if reason is not None:
                    if exclusions is not None:
                        exclusions.append({'distribution': distribution, 'record_path': str(entry), 'declared_path': str(candidate), 'reason': reason})
                    continue
                path = candidate.resolve(strict=True)
                require(path.is_relative_to(distribution_root), 'native_dependency_unavailable')
            else:
                path = Path(installed.locate_file(entry)).resolve(strict=True)
            if path.suffix in ('.pyc', '.pyo') or not path.is_file():
                continue
            files.append({'path': str(path)})
        require(bool(files), 'native_dependency_unavailable')
        result.append({'distribution': distribution, 'version': installed.version, 'package_root': str(Path(module.__file__).resolve(strict=True).parent), 'files': sorted({r['path']: r for r in files}.values(), key=lambda r: r['path'])})
    return result

def freeze_driver_runtime(*, module_root, snapshot_directory, driver_modules, policy, contained_dependency_records=False, dependency_exclusions=None):
    """Copy the selected driver closure during explicit bounded preparation.

    This records the current interpreter and installed driver dependencies. It
    does not import, install or select a native scientific implementation.
    """
    require(type(policy) is LocalJobPolicy, 'native_dependency_unavailable')
    require(type(contained_dependency_records) is bool and (dependency_exclusions is None or type(dependency_exclusions) is list), 'native_dependency_unavailable')
    require(type(driver_modules) in (tuple, list) and bool(driver_modules) and all((type(name) is str and name.startswith('gene_annotation_episode.') and all((part.isidentifier() for part in name.split('.'))) for name in driver_modules)), 'native_dependency_unavailable')
    target = _directory(snapshot_directory)
    target.mkdir(parents=True, exist_ok=True)
    modules = _source_closure(module_root, driver_modules)
    implementation = []
    for name, source in sorted(modules.items()):
        check_scratch_budget(target, policy, additional_bytes=source.stat().st_size)
        _copy_exact(source, target / (name.replace('.', '/') + '.py'))
        implementation.append({'module': name})
    return validate_driver_runtime(dict(python_executable=sys.executable, python_version=platform.python_version(), module_root=str(target), implementation_files=implementation, dependencies=_dependency_bindings(contained_records=True, exclusions=dependency_exclusions) if contained_dependency_records else _dependency_bindings()))
