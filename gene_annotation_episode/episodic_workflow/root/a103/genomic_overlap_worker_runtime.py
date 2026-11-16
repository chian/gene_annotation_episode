"""A103 original genomic worker dependency records."""
from copy import deepcopy
import importlib
import importlib.metadata
from pathlib import Path
import sys
from .native_driver_runtime import _DRIVER, _dependency_roots

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
                files.append(dict(path=str(path)))
        require(files, 'native_dependency_unavailable')
        result.append(dict(distribution=distribution, version=installed.version,
            package_root=str(Path(module.__file__).resolve(strict=True).parent), files=sorted({r['path']: r for r in files}.values(), key=lambda r: r['path'])))
    return result
