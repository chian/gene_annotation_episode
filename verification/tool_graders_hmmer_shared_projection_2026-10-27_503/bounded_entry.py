"""HMMER publication and requested-return checks inside the saved handle."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys

attempt = Path(sys.argv[1])
mode = sys.argv[2]


def pin(path):
    path = Path(path).resolve(strict=True)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            h.update(block)
    return {'path': str(path), 'sha256': h.hexdigest(), 'size_bytes': path.stat().st_size}


def save(name, data):
    (attempt / name).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def mapped():
    return {Path(line.split(maxsplit=5)[5]).resolve(strict=True)
        for line in Path('/proc/self/maps').read_text().splitlines()
        if len(line.split(maxsplit=5)) == 6 and line.split(maxsplit=5)[5].startswith('/')
        and 'x' in line.split()[1]}

binaries = {Path(sys.executable)}
native_program = attempt / 'source_snapshot/resources/software/infernal-1.1.5/hmmer/src/phmmer'
if native_program.is_file():
    binaries.add(native_program)
for root in (attempt / 'dependencies', attempt / 'runtime/lib/python3.12'):
    binaries.update(p for p in root.rglob('*.so') if not any(part.endswith('.libs') for part in p.parts))
libraries, resolutions = mapped(), []
for binary in sorted(binaries):
    if binary.read_bytes()[:4] != b'\x7fELF':
        continue
    result = subprocess.run(['/usr/bin/ldd', str(binary)], text=True, capture_output=True, check=False)
    resolutions.append({'path': str(binary), 'returncode': result.returncode, 'stdout': result.stdout})
    if result.returncode or 'not found' in result.stdout:
        raise ValueError('native_dependency_unavailable:' + str(binary))
    libraries.update(Path(word).resolve(strict=True) for word in result.stdout.split() if word.startswith('/'))
before = {str(p): pin(p) for p in sorted(libraries | binaries)}
save('native_library_pins_before.json', list(before.values()))
save('native_library_resolution.json', resolutions)
import pytest
test_filter = json.loads((attempt / 'selected_filter.json').read_text())
result = int(pytest.main(['-q', '--tb=short', '-p', 'no:cacheprovider',
    '--rootdir=' + str(attempt / 'source_snapshot'), '--basetemp=' + str(attempt / 'temporary/pytest'),
    '--junitxml=' + str(attempt / 'junit.xml'),
    *(['-k', test_filter] if test_filter else []),
    *[str(attempt / 'source_snapshot/tests' / name)
      for name in json.loads((attempt / 'selected_tests.json').read_text())]]))
modules = {name: pin(module.__file__) for name, module in sys.modules.copy().items()
    if getattr(module, '__file__', None) and Path(module.__file__).is_file()}
allowed = (attempt / 'source_snapshot', attempt / 'dependencies', attempt / 'runtime')
outside = [name for name, row in modules.items() if not any(Path(row['path']).is_relative_to(p) for p in allowed)]
after = {p: pin(p) for p in before}
audit = {'pytest_returncode': result, 'outside_modules': outside,
    'unbound_mappings': [str(p) for p in mapped() if str(p) not in before], 'native_unchanged': before == after}
save('execution_audit.json', audit)
save('loaded_module_pins.json', modules)
save('native_library_pins_after.json', list(after.values()))
raise SystemExit(4 if outside or audit['unbound_mappings'] or before != after else result)
