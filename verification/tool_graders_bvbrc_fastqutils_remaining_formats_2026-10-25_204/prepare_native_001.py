"""Prepare a private pinned Cutadapt executable for small synthetic format cases."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / 'native_environment_001'
OUT.mkdir(exist_ok=False)
OUT.joinpath('tmp').mkdir()


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


started = time.monotonic()
receipt = {'started_at': datetime.now(timezone.utc).isoformat(), 'passed': False,
    'requested_version': 'cutadapt==4.9', 'no_wall_time_limit': True,
    'BV_BRC_deployed_version_verified': False}
environment = dict(os.environ, TMPDIR=str(OUT / 'tmp'), PIP_CACHE_DIR=str(OUT / 'cache'),
    PIP_DISABLE_PIP_VERSION_CHECK='1', PYTHONDONTWRITEBYTECODE='1')
environment.pop('PYTHONPATH', None)
commands = [
    [sys.executable, '-m', 'venv', '--without-pip', str(OUT / 'venv')],
    [sys.executable, '-m', 'pip', '--python', str(OUT / 'venv/bin/python'), 'install',
        '--report', str(OUT / 'install_report.json'), 'cutadapt==4.9'],
    [str(OUT / 'venv/bin/python'), '-m', 'cutadapt', '--version'],
]
with (OUT / 'commands.json').open('x') as stream:
    json.dump(commands, stream, indent=2)
try:
    for index, command in enumerate(commands):
        with (OUT / f'command{index}_stdout.log').open('x') as stdout, (OUT / f'command{index}_stderr.log').open('x') as stderr:
            result = subprocess.run(command, cwd=OUT, env=environment, stdout=stdout, stderr=stderr, preexec_fn=limits)
        receipt[f'command{index}_exit_code'] = result.returncode
        assert result.returncode == 0, str(index)
    assert (OUT / 'command2_stdout.log').read_text().strip() == '4.9'
    native, = (OUT / 'venv/lib').glob('python*/site-packages/cutadapt/report.py')
    assert sha(native) == sha(HERE / 'sources/cutadapt_v4_9/src/cutadapt/report.py')
    receipt.update(passed=True, report_source_sha256=sha(native),
        install_report_sha256=sha(OUT / 'install_report.json'))
except Exception as error:
    receipt.update(error_type=type(error).__name__, error=str(error))
finally:
    receipt.update(ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - started,
        scratch_bytes=sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file()))
    receipt['passed'] = receipt['passed'] and receipt['scratch_bytes'] < 4 * 1024**3
    with (OUT / 'receipt.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt))
raise SystemExit(0 if receipt['passed'] else 1)
