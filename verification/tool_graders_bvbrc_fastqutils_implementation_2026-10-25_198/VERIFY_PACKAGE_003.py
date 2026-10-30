"""Run the corrected probe on the unchanged package002 wheel and specimen."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE / 'package_verification_002'
OUT = HERE / 'package_verification_003'
FROZEN = HERE / 'combined_unit_001/candidate'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


previous = json.loads((PREVIOUS / 'receipt.json').read_text())
assert previous['build_exit_code'] == 0 and previous['installed_exit_code'] == 1
assert not previous['changed_sources'] and not previous['changed_build_sources']
before = json.loads((PREVIOUS / 'source_after.json').read_text())
assert {name: sha(FROZEN / name) for name in before} == before
specimen = PREVIOUS / 'specimen'
specimen_before = {path.name: sha(path) for path in specimen.iterdir() if path.is_file()}
wheel, = (PREVIOUS / 'wheel').glob('*.whl')
assert sha(wheel) == previous['wheel_sha256']
installed = PREVIOUS / 'extracted_wheel'
with zipfile.ZipFile(wheel) as archive:
    assert set(previous['required_packaged_files']) <= set(archive.namelist())
    for name in archive.namelist():
        if name.startswith(('gene_annotation_episode/', 'method_loop/')) and not name.endswith('/'):
            assert hashlib.sha256(archive.read(name)).hexdigest() == before.get(name) == sha(installed / name), name
OUT.mkdir(exist_ok=False)
save('source_before.json', before)
save('specimen_before.json', specimen_before)
clock = time.monotonic()
receipt = {'started_at': datetime.now(timezone.utc).isoformat(), 'passed': False,
    'source_count': len(before), 'wheel_sha256': sha(wheel),
    'previous_build_receipt_sha256': sha(PREVIOUS / 'receipt.json'),
    'required_packaged_files': previous['required_packaged_files'],
    'provider_pin': previous['provider_pin'], 'harness_sha256': sha(Path(__file__)),
    'probe_sha256': sha(HERE / 'PACKAGE_PROBE_002.py'), 'no_wall_time_limit': True,
    'live_service_execution_verified': False, 'host_custody_verified': False}
try:
    command = [sys.executable, '-I', '-B', str(HERE / 'PACKAGE_PROBE_002.py'), str(installed), str(specimen)]
    save('command.json', {'argv': command, 'cwd': str(OUT)})
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    environment.pop('PYTHONPATH', None)
    with (OUT / 'stdout.log').open('x') as stdout, (OUT / 'stderr.log').open('x') as stderr:
        result = subprocess.run(command, cwd=OUT, env=environment, stdout=stdout, stderr=stderr, preexec_fn=limits)
    receipt['installed_exit_code'] = result.returncode
    assert result.returncode == 0, 'Corrected installed probe failed; see retained stderr'
    answer = json.loads((OUT / 'stdout.log').read_text())
    save('installed_result.json', answer)
    assert answer['provider_pin'] == previous['provider_pin']
    receipt.update(passed=True, installed_result_sha256=sha(OUT / 'installed_result.json'),
        numerical_answers=answer['numbers'], changed_threshold_fractions=answer['changed_threshold_fractions'],
        saved_communication_without_science=answer['saved_communication_without_science'])
except BaseException as error:
    receipt.update(passed=False, error_type=type(error).__name__, error=str(error))
    (OUT / 'error.log').write_text(traceback.format_exc())
finally:
    after = {name: sha(FROZEN / name) for name in before}
    specimen_after = {path.name: sha(path) for path in specimen.iterdir() if path.is_file()}
    save('source_after.json', after)
    save('specimen_after.json', specimen_after)
    changed = [name for name in before if before[name] != after[name]]
    receipt.update(changed_sources=changed, specimen_unchanged=specimen_before == specimen_after,
        wheel_unchanged=sha(wheel) == previous['wheel_sha256'], ended_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=time.monotonic() - clock,
        scratch_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()))
    receipt['passed'] = receipt['passed'] and not changed and receipt['specimen_unchanged'] and receipt['wheel_unchanged']
    save('receipt.json', receipt)
    print(json.dumps({key: value for key, value in receipt.items() if key != 'required_packaged_files'}))
raise SystemExit(0 if receipt['passed'] else 1)
