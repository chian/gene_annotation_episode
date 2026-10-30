"""Preserve development-test evidence; do not impose a wall-time stop."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE / 'candidate'
EVIDENCE = HERE / 'evidence_root_returns_003'
EVIDENCE.mkdir(exist_ok=False)


def snapshot():
    paths = [p for directory in ('gene_annotation_episode', 'method_loop', 'tests')
        for p in (CANDIDATE / directory).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py', '.json', '.toml')]
    paths.append(CANDIDATE / 'pyproject.toml')
    return {str(p.relative_to(CANDIDATE)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)}


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))


def save(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, indent=2) + '\n')


started = time.monotonic()
before = snapshot()
argv = [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp=' + str(EVIDENCE / 'temporary'), '--junitxml=' + str(EVIDENCE / 'tests.xml'),
    'tests/test_bvbrc_fastqutils_returns.py', 'tests/test_bvbrc_fastqutils_tool_info.py']
command = {'argv': argv, 'cwd': str(CANDIDATE), 'started_at': datetime.now(timezone.utc).isoformat(),
    'no_wall_time_limit': True, 'ram_limit_bytes': 20 * 1024**3,
    'qualification': 'Candidate development run; concurrent B/C changes must be reported, not hidden. No live transport or original host custody proof.'}
save('source_before.json', before)
save('command.json', command)
env = dict(os.environ, PYTHONPATH=str(CANDIDATE), PYTHONDONTWRITEBYTECODE='1')
with (EVIDENCE / 'output.log').open('w') as log:
    result = subprocess.run(argv, cwd=CANDIDATE, env=env, stdout=log, stderr=subprocess.STDOUT, preexec_fn=limits)
after = snapshot()
save('source_after.json', after)
changed = [key for key in before.keys() | after.keys() if before.get(key) != after.get(key)]
receipt = {**command, 'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - started,
    'ended_at': datetime.now(timezone.utc).isoformat(), 'source_count': len(before),
    'changed_sources': sorted(changed), 'frozen': not changed,
    'scratch_bytes': sum(p.stat().st_size for p in EVIDENCE.rglob('*') if p.is_file())}
save('receipt.json', receipt)
print(json.dumps(receipt))
print((EVIDENCE / 'output.log').read_text()[-12000:])
raise SystemExit(result.returncode)
