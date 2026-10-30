"""Selected HMMER alignment-map verification, executed inside the saved handle."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import shutil
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
binaries.update(Path(p) for p in json.loads(
    (attempt / 'selected_native_executables.json').read_text()))
existing_file = attempt / 'selected_existing_native_executables.json'
for row in json.loads(existing_file.read_text()) if existing_file.exists() else []:
    if (type(row) is not dict or set(row) != {'path', 'sha256', 'size_bytes'}
            or Path(row['path']) not in binaries or pin(row['path']) != row):
        raise ValueError('selected_existing_native_executable_identity_conflict')
selected_library_file = attempt / 'selected_native_libraries.json'
selected_libraries = json.loads(selected_library_file.read_text()) if selected_library_file.exists() else []
for row in selected_libraries:
    if (type(row) is not dict or set(row) != {'path', 'sha256', 'size_bytes'}
            or not Path(row['path']).is_absolute() or pin(row['path']) != row):
        raise ValueError('selected_native_library_identity_conflict')
    binaries.add(Path(row['path']))
compiler_inputs, compiler_queries = set(), []
if os.environ.get('HMMER_NATIVE_ORACLE_CC'):
    compiler = Path(os.environ['HMMER_NATIVE_ORACLE_CC']).resolve(strict=True)
    binaries.add(compiler)
    def compiler_query(argument):
        value = subprocess.run([str(compiler), argument], text=True,
            capture_output=True, check=False)
        compiler_queries.append({'argv': [str(compiler), argument],
            'returncode': value.returncode, 'stdout': value.stdout, 'stderr': value.stderr})
        if value.returncode:
            raise ValueError('selected_compiler_query_failed:' + argument)
        return value.stdout.strip()
    for program in ('cc1', 'as', 'ld', 'collect2'):
        selected = compiler_query('-print-prog-name=' + program)
        resolved = Path(selected) if Path(selected).is_absolute() else Path(shutil.which(selected) or '')
        if not resolved.is_file():
            raise ValueError('selected_compiler_program_unavailable:' + selected)
        binaries.add(resolved.resolve(strict=True))
    include_roots = [Path('/usr/include')]
    for name in ('include', 'include-fixed'):
        selected = compiler_query('-print-file-name=' + name)
        if Path(selected).is_absolute() and Path(selected).is_dir():
            include_roots.append(Path(selected))
    for root in include_roots:
        compiler_inputs.update(p.resolve(strict=True) for p in root.rglob('*') if p.is_file())
    for name in ('crt1.o', 'Scrt1.o', 'crti.o', 'crtn.o', 'crtbegin.o', 'crtbeginS.o',
                 'crtend.o', 'crtendS.o', 'libgcc.a', 'libgcc_eh.a', 'libgcc_s.so',
                 'liblto_plugin.so', 'libc.so', 'libc_nonshared.a', 'libm.so',
                 'libm.a', 'libpthread.a', 'libpthread.so.0'):
        selected = compiler_query('-print-file-name=' + name)
        if Path(selected).is_absolute() and Path(selected).is_file():
            compiler_inputs.add(Path(selected).resolve(strict=True))
    save('compiler_queries.json', compiler_queries)
    save('compiler_include_roots.json', [str(p) for p in include_roots])
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
before = {str(p): pin(p) for p in sorted(libraries | binaries | compiler_inputs)}
save('native_library_pins_before.json', list(before.values()))
save('native_library_resolution.json', resolutions)
# Historical plans retain their original absolute operand paths. Pin those
# original retained files as well as their snapshot copies; do not rewrite the
# historical plan to disguise where its fixture bytes were read.
request = json.loads((attempt / 'selected_request.json').read_text())
original_repo = Path(request.get('repository_root', str(attempt.parents[2])))
retained_inputs = set()
for relative in request.get('support_trees', []):
    root = original_repo / relative
    if relative.startswith('verification/'):
        retained_inputs.update(p.resolve(strict=True) for p in root.rglob('*')
            if p.is_file() and not p.is_symlink())
retained_before = {str(p): pin(p) for p in sorted(retained_inputs)}
save('original_retained_fixture_pins_before.json', list(retained_before.values()))
# A separate service supplies only its selected application PYTHONPATH. Check
# that exact startup condition before existing selected result workers launch.
probe = subprocess.run([sys.executable, '-B', '-c',
    "import json,sys,site,numpy,Bio; print(json.dumps({'python':sys.executable,"
    "'stdlib':json.__file__,'numpy':numpy.__file__,'numpy_version':numpy.__version__,"
    "'biopython':Bio.__file__,'user_site_enabled':site.ENABLE_USER_SITE}))"],
    env={'PYTHONPATH': str(attempt / 'source_snapshot'), 'PYTHONDONTWRITEBYTECODE': '1'},
    text=True, capture_output=True, check=False)
save('isolated_service_import_probe.json', {'returncode': probe.returncode,
    'stdout': probe.stdout, 'stderr': probe.stderr})
if probe.returncode:
    raise ValueError('frozen_service_import_probe_failed')
probe_values = json.loads(probe.stdout)
if (probe_values['user_site_enabled'] is not False
        or not Path(probe_values['stdlib']).is_relative_to(attempt / 'runtime')
        or any(not Path(probe_values[name]).is_relative_to(attempt / 'dependencies')
               for name in ('numpy', 'biopython'))):
    raise ValueError('frozen_service_import_closure_mismatch')
import pytest

class RetainedTestReports:
    def __init__(self, stream):
        self.stream = stream

    def pytest_runtest_logreport(self, report):
        if report.when == 'call' or report.failed:
            value = {'nodeid': report.nodeid, 'phase': report.when, 'outcome': report.outcome,
                'duration_seconds': report.duration}
            if report.failed:
                value['failure'] = report.longreprtext
            self.stream.write(json.dumps(value, allow_nan=False) + '\n')
            self.stream.flush()

# Some purity tests deliberately replace Path.open until fixture teardown.
# The reporter owns its stream before those patches and never opens a file
# during a test's call-report phase.
with (attempt / 'case_reports.jsonl').open('a') as case_stream:
    result = int(pytest.main(['-q', '--tb=short', '-p', 'no:cacheprovider',
        '--rootdir=' + str(attempt / 'source_snapshot'), '--basetemp=' + str(attempt / 'temporary/pytest'),
        '--junitxml=' + str(attempt / 'junit.xml'),
        *[str(attempt / 'source_snapshot/tests' / name)
          for name in json.loads((attempt / 'selected_tests.json').read_text())]],
        plugins=[RetainedTestReports(case_stream)]))
modules = {name: pin(module.__file__) for name, module in sys.modules.copy().items()
    if getattr(module, '__file__', None) and Path(module.__file__).is_file()}
allowed = (attempt / 'source_snapshot', attempt / 'dependencies', attempt / 'runtime')
outside = [name for name, row in modules.items() if not any(Path(row['path']).is_relative_to(p) for p in allowed)]
after = {p: pin(p) for p in before}
retained_after = {p: pin(p) for p in retained_before}
audit = {'pytest_returncode': result, 'outside_modules': outside,
    'unbound_mappings': [str(p) for p in mapped() if str(p) not in before],
    'native_unchanged': before == after,
    'original_retained_fixtures_unchanged': retained_before == retained_after}
save('execution_audit.json', audit)
save('loaded_module_pins.json', modules)
save('native_library_pins_after.json', list(after.values()))
save('original_retained_fixture_pins_after.json', list(retained_after.values()))
raise SystemExit(4 if outside or audit['unbound_mappings'] or before != after
                 or retained_before != retained_after else result)
