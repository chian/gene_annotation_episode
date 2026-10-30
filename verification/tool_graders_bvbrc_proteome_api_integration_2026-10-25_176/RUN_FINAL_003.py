"""Verify the reviewed fixture correction after frozen run 013 has finished."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import resource
import subprocess
import time

OUT = Path(__file__).resolve().parent
CANDIDATE = OUT / 'candidate'
PYTHON = OUT.parent.parent / '.venv/bin/python'


def snapshot():
    return {str(p.relative_to(CANDIDATE)): {
        'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
        for p in sorted(CANDIDATE.rglob('*')) if p.is_file()
        and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


previous = json.loads((OUT / 'TEST_013_AFTER.json').read_text())
assert previous['returncodes'] == {'core': 1, 'host': 0}, previous['returncodes']
assert previous['source_changes_during_run'] == []
before = snapshot()
changes_from_013 = sorted(p for p in set(before) | set(previous['files'])
    if before.get(p) != previous['files'].get(p))
assert changes_from_013 == ['tests/test_execution_episodes_family.py'], changes_from_013
runner_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
environment = {'PYTHONPATH': str(CANDIDATE) + ':' + str(CANDIDATE / 'tests'),
    'PYTHONDONTWRITEBYTECODE': '1'}
command = [str(PYTHON), '-m', 'pytest', '-q', 'tests/test_execution_episodes_family.py',
    '--junitxml=' + str(OUT / 'TEST_014.xml'), '--basetemp=' + str(OUT / 'final_test_tmp_003'),
    '-o', 'cache_dir=' + str(OUT / 'final_pytest_cache_003')]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
write('TEST_014_BEFORE.json', {'timestamp_utc': started, 'cwd': str(CANDIDATE),
    'command': command, 'environment': environment, 'files': before,
    'runner_sha256': runner_sha256, 'changes_from_013': changes_from_013})
start = time.monotonic()
with (OUT / 'TEST_014.log').open('w') as stream:
    result = subprocess.run(command, cwd=CANDIDATE, env={**os.environ, **environment},
        stdout=stream, stderr=subprocess.STDOUT)
after = snapshot()
changes = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
receipt = {'started_utc': started,
    'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'elapsed_seconds': time.monotonic() - start, 'command': command,
    'environment': environment, 'cwd': str(CANDIDATE), 'returncode': result.returncode,
    'source_changes_during_run': changes, 'files': after,
    'changes_from_013': changes_from_013, 'runner_before_sha256': runner_sha256,
    'runner_after_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'child_maximum_resident_set_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    'test_scratch_bytes': sum(p.stat().st_size for p in (OUT / 'final_test_tmp_003').rglob('*')
        if p.is_file())}
write('TEST_014_AFTER.json', receipt)
print(json.dumps({k:v for k,v in receipt.items() if k != 'files'}))
assert changes == [] and receipt['runner_after_sha256'] == runner_sha256
raise SystemExit(result.returncode)
