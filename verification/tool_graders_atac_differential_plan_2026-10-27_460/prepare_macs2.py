"""Explicit, bounded prerequisite preparation; no scientific dataset run."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import urllib.request

ATTEMPT = Path(os.environ['ATAC_PREP_ATTEMPT'])
PYTHON = Path(sys.executable)
manifest = []


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def command(name, argv, *, extra_env=None):
    environment = dict(os.environ)
    environment.update(extra_env or {})
    out, err = ATTEMPT / (name + '.stdout.txt'), ATTEMPT / (name + '.stderr.txt')
    selected = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(ATTEMPT),
                'environment_overrides': extra_env or {}, 'stdout': str(out), 'stderr': str(err)}
    with out.open('wb') as stdout, err.open('wb') as stderr:
        result = subprocess.run(selected['argv'], cwd=ATTEMPT, env=environment,
                                stdout=stdout, stderr=stderr, check=False)
    selected['returncode'] = result.returncode
    manifest.append(selected)
    save(ATTEMPT / 'commands.json', manifest)
    if result.returncode:
        raise SystemExit(result.returncode)
    return out.read_text()


bootstrap = ATTEMPT / 'bootstrap'
command('bootstrap_uv', [PYTHON, '-m', 'pip', '--isolated', '--disable-pip-version-check',
    'install', '--no-input', '--no-deps', '--target', bootstrap,
    '--cache-dir', ATTEMPT / 'cache/pip', 'uv==0.8.22'])
uv = [PYTHON, '-m', 'uv']
uv_env = {'PYTHONPATH': str(bootstrap), 'UV_CACHE_DIR': str(ATTEMPT / 'cache/uv'),
    'UV_PYTHON_INSTALL_DIR': str(ATTEMPT / 'python'), 'UV_PYTHON_BIN_DIR': str(ATTEMPT / 'python-bin'),
    'UV_HTTP_RETRIES': '0'}
command('python_install', [*uv, 'python', 'install', '3.11.13'], extra_env=uv_env)
selected_python = command('python_find', [*uv, 'python', 'find', '--managed-python', '3.11.13'],
                          extra_env=uv_env).strip()
assert Path(selected_python).is_file()
command('create_environment', [*uv, 'venv', '--python', selected_python, ATTEMPT / 'environment'],
        extra_env=uv_env)
worker_python = ATTEMPT / 'environment/bin/python'
command('build_dependencies', [*uv, 'pip', 'install', '--python', worker_python,
    'numpy==1.26.4', 'Cython==0.29.37', 'setuptools==80.9.0', 'wheel==0.45.1'], extra_env=uv_env)
command('macs2_install', [*uv, 'pip', 'install', '--python', worker_python,
    '--no-build-isolation', 'MACS2==2.2.9.1', 'pysam==0.23.3'], extra_env=uv_env)
command('installed_packages', [*uv, 'pip', 'freeze', '--python', worker_python], extra_env=uv_env)

with urllib.request.urlopen('https://pypi.org/pypi/MACS2/2.2.9.1/json') as response:
    metadata_bytes = response.read()
(ATTEMPT / 'macs2_pypi_metadata.json').write_bytes(metadata_bytes)
metadata = json.loads(metadata_bytes)
sources = [row for row in metadata['urls'] if row['packagetype'] == 'sdist']
assert len(sources) == 1
source = sources[0]
expected = '8d56bc37fb823fc6387d78138ce968405c54a0a8cd9776682705fd0983252d16'
assert source['digests']['sha256'] == expected
with urllib.request.urlopen(source['url']) as response:
    data = response.read()
assert hashlib.sha256(data).hexdigest() == expected
archive = ATTEMPT / source['filename']
archive.write_bytes(data)
destination = ATTEMPT / 'native_source'
destination.mkdir()
with tarfile.open(archive) as tar:
    for member in tar.getmembers():
        assert member.isdir() or member.isfile()
        target = (destination / member.name).resolve()
        assert target.is_relative_to(destination.resolve())
    tar.extractall(destination, filter='data')
command('macs2_version', [ATTEMPT / 'environment/bin/macs2', '--version'])
command('macs2_callpeak_help', [ATTEMPT / 'environment/bin/macs2', 'callpeak', '--help'])
command('macs2_bdgdiff_help', [ATTEMPT / 'environment/bin/macs2', 'bdgdiff', '--help'])
paths = [Path(selected_python).resolve(), worker_python.resolve(), ATTEMPT / 'environment/bin/macs2', archive]
paths.extend(sorted((ATTEMPT / 'environment/lib/python3.11/site-packages/MACS2').rglob('*.so')))
save(ATTEMPT / 'prepared_software.json', {'scientific_execution': False,
    'python': str(worker_python), 'macs2': str(ATTEMPT / 'environment/bin/macs2'),
    'source_url': source['url'], 'source_sha256': expected,
    'files': [{'path': str(p), 'size_bytes': p.stat().st_size,
               'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]})
