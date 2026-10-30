"""Build an immutable-source FastqUtils wheel and check its actual imports/results."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = HERE / 'combined_unit_001/candidate'
OUT = HERE / 'package_verification_002'
PIN = 'e25e6accdeb551f989701d50b2bfed8a6f9393da31848cbc62a0fb2f5856e135'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


def run(name, argv):
    save(name + '_command.json', {'argv': argv, 'cwd': str(OUT)})
    with (OUT / (name + '_stdout.log')).open('x') as stdout, (OUT / (name + '_stderr.log')).open('x') as stderr:
        result = subprocess.run(argv, cwd=OUT, env=environment, stdout=stdout, stderr=stderr, preexec_fn=limits)
    receipt[name + '_exit_code'] = result.returncode
    assert result.returncode == 0, name + ' failed; see retained logs'


before = json.loads((HERE / 'combined_unit_001/source_before.json').read_text())
assert len(before) == 1095
assert {name: sha(FROZEN / name) for name in before} == before
OUT.mkdir(exist_ok=False)
save('source_before.json', before)
clock = time.monotonic()
receipt = {'started_at': datetime.now(timezone.utc).isoformat(), 'passed': False,
    'provider_pin': PIN, 'source_count': len(before), 'live_service_execution_verified': False,
    'host_custody_verified': False, 'no_wall_time_limit': True,
    'qualification': 'Frozen synthetic numerical fixture, built wheel, recalculation and pure saved-return validation.'}
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
environment.pop('PYTHONPATH', None)
(OUT / 'build_tmp').mkdir()
environment.update(TMPDIR=str(OUT / 'build_tmp'), PIP_CACHE_DIR=str(OUT / 'pip_cache'))
previous = HERE / 'package_verification_001/receipt.json'
previous_receipt = json.loads(previous.read_text())
assert previous_receipt['build_exit_code'] == 2 and not previous_receipt['changed_sources']
receipt['previous_build_receipt_sha256'] = sha(previous)
receipt['build_correction'] = 'Use declared isolated build dependencies because setuptools is absent from the runtime environment.'
try:
    specimen = OUT / 'specimen'
    specimen.mkdir()
    run('fixture', [sys.executable, '-I', '-B', str(HERE / 'PACKAGE_FIXTURE_001.py'), str(FROZEN), str(specimen)])
    fixture = json.loads((OUT / 'fixture_stdout.log').read_text())
    assert fixture['provider_pin'] == PIN
    save('fixture_result.json', fixture)
    build_source = OUT / 'build_source'
    for name, digest in before.items():
        destination = build_source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FROZEN / name, destination)
        assert sha(destination) == digest, name
    run('build', [sys.executable, '-m', 'pip', 'wheel', '--no-deps',
        '--wheel-dir', str(OUT / 'wheel'), str(build_source)])
    wheels = list((OUT / 'wheel').glob('*.whl'))
    assert len(wheels) == 1
    wheel = wheels[0]
    installed = OUT / 'extracted_wheel'
    required = [name for name in before if name.startswith('gene_annotation_episode/bvbrc_fastqutils_')]
    assert len(required) == 26, len(required)
    with zipfile.ZipFile(wheel) as archive:
        assert set(required) <= set(archive.namelist())
        for name in archive.namelist():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            if name.startswith(('gene_annotation_episode/', 'method_loop/')) and not name.endswith('/'):
                assert hashlib.sha256(archive.read(name)).hexdigest() == before.get(name), name
        archive.extractall(installed)
    receipt.update(wheel_sha256=sha(wheel), required_packaged_files=required)
    run('installed', [sys.executable, '-I', '-B', str(HERE / 'PACKAGE_PROBE_001.py'), str(installed), str(specimen)])
    answer = json.loads((OUT / 'installed_stdout.log').read_text())
    save('installed_result.json', answer)
    assert answer['provider_pin'] == PIN
    receipt.update(passed=True, numerical_answers=answer['numbers'],
        changed_threshold_fractions=answer['changed_threshold_fractions'],
        installed_result_sha256=sha(OUT / 'installed_result.json'))
except BaseException as error:
    receipt.update(passed=False, error_type=type(error).__name__, error=str(error))
    (OUT / 'error.log').write_text(traceback.format_exc())
finally:
    after = {name: sha(FROZEN / name) for name in before}
    save('source_after.json', after)
    changed = [name for name in before if before[name] != after[name]]
    build_source = OUT / 'build_source'
    build_changed = ([name for name in before if sha(build_source / name) != before[name]]
        if build_source.is_dir() and all((build_source / name).is_file() for name in before) else [])
    receipt.update(changed_sources=changed, changed_build_sources=build_changed,
        source_manifest_sha256=sha(HERE / 'combined_unit_001/source_before.json'),
        harness_sha256=sha(Path(__file__)), fixture_script_sha256=sha(HERE / 'PACKAGE_FIXTURE_001.py'),
        probe_sha256=sha(HERE / 'PACKAGE_PROBE_001.py'), ended_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=time.monotonic() - clock,
        scratch_bytes=sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file()))
    receipt['passed'] = receipt['passed'] and not changed and not build_changed and receipt['scratch_bytes'] < 4 * 1024**3
    save('receipt.json', receipt)
    print(json.dumps(receipt))
raise SystemExit(0 if receipt['passed'] else 1)
