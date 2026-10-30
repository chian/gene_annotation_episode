"""Run the selected existing suite and retain actual runtime provenance.

Invoked only inside the existing bounded lifecycle. Library inspection is
administrative execution provenance, never scientific credit or a retry rule.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys


attempt = Path(sys.argv[1]).resolve(strict=True)
mode = sys.argv[2]
snapshot = attempt / 'source_snapshot'
test = {'cooler': 'tests/test_native_chromatin_interaction_workflow.py',
        'hic': 'tests/test_native_hic_chromatin_workflow.py'}[mode]


def pin(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while raw := stream.read(1024 * 1024):
            digest.update(raw)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'size_bytes': path.stat().st_size}


def save(name, value):
    (attempt / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def mapped_files():
    paths = set()
    for line in Path('/proc/self/maps').read_text().splitlines():
        parts = line.split(maxsplit=5)
        if len(parts) == 6 and parts[5].startswith('/') and 'x' in parts[1]:
            if parts[5].endswith(' (deleted)'):
                raise ValueError('deleted_executable_mapping')
            paths.add(Path(parts[5]).resolve(strict=True))
    return paths


# ldd resolves the finite binary dependency closure of these already selected,
# copied distributions/stdlib. It runs here inside the selected bounded handle.
selected_binaries = {Path(sys.executable).resolve(strict=True)}
for root in (attempt / 'dependencies', attempt / 'runtime/lib/python3.12'):
    # Resolve extension entry points with their wheel RPATH. Invoking ldd on a
    # bundled internal library as if it were an entry point loses the caller's
    # RPATH and can report a false missing sibling (observed in cooler001).
    selected_binaries.update(p.resolve(strict=True) for p in root.rglob('*.so')
        if p.is_file() and not any(part.endswith('.libs') for part in p.parts))
libraries, resolutions = set(mapped_files()), []
for binary in sorted(selected_binaries):
    if binary.read_bytes()[:4] != b'\x7fELF':
        continue
    result = subprocess.run(['/usr/bin/ldd', str(binary)], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    resolutions.append({'binary': str(binary), 'returncode': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr})
    if result.returncode:
        raise ValueError('selected_binary_dependency_resolution_failed:' + str(binary))
    if 'not found' in result.stdout:
        raise ValueError('selected_binary_dependency_missing:' + str(binary))
    for line in result.stdout.splitlines():
        for word in line.split():
            if word.startswith('/'):
                libraries.add(Path(word).resolve(strict=True))
before = {str(path): pin(path) for path in sorted(libraries | selected_binaries)}
save('native_library_resolution.json', resolutions)
save('native_library_pins_before.json', list(before.values()))
save('runtime_before.json', {'executable': pin(sys.executable), 'version': sys.version,
    'prefix': sys.prefix, 'base_prefix': sys.base_prefix, 'path': sys.path,
    'initial_mapped_files': [str(p) for p in sorted(mapped_files())]})

import pytest

argv = ['-vv', '--tb=short', '-p', 'no:cacheprovider',
    '--basetemp=' + str(attempt / 'temporary/pytest'), '--rootdir=' + str(snapshot),
    '--junitxml=' + str(attempt / 'junit.xml'), str(snapshot / test)]
save('pytest_request.json', {'argv': argv, 'mode': mode})
result = int(pytest.main(argv))
modules, outside = {}, []
allowed = (snapshot, attempt / 'dependencies', attempt / 'runtime')
for name, module in sorted(sys.modules.items()):
    filename = getattr(module, '__file__', None)
    if filename is None or not Path(filename).is_file():
        continue
    path = Path(filename).resolve(strict=True)
    modules[name] = pin(path)
    if not any(path.is_relative_to(root) for root in allowed):
        outside.append({'module': name, 'path': str(path)})
mapped = mapped_files()
unbound = sorted(str(p) for p in mapped if str(p) not in before)
after = {path: pin(path) for path in before}
save('native_library_pins_after.json', list(after.values()))
save('loaded_module_pins.json', modules)
audit = {'pytest_returncode': result, 'native_library_pins_unchanged': before == after,
    'unbound_executable_mappings': unbound, 'modules_outside_frozen_roots': outside,
    'mapped_files': [str(p) for p in sorted(mapped)], 'loaded_module_count': len(modules),
    'installed_distributions': sorted(({'name': d.metadata['Name'], 'version': d.version}
        for d in importlib.metadata.distributions()), key=lambda row: row['name'].lower())}
save('execution_audit.json', audit)
if outside or unbound or before != after:
    raise SystemExit(4)
raise SystemExit(result)
