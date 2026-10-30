"""Verify the combined native parsers before the separate calculator delivery."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE / 'candidate_002'
OUT = HERE / 'parser_checks_001'
OUT.mkdir(exist_ok=False)
LIMIT = 4 * 1024**3


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def snapshot():
    return {str(p.relative_to(CANDIDATE)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(CANDIDATE.rglob('*')) if p.is_file()
        and not {'__pycache__', '.pytest_cache'} & set(p.parts) and p.suffix != '.pyc'}


def usage():
    return sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMIT, LIMIT))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


before = snapshot()
save('source_before.json', before)
names = ['test_bvbrc_fastqutils_sra.py', 'test_bvbrc_fastqutils_samstat_svg.py',
         'test_bvbrc_fastqutils_samstat_contracts.py', 'test_bvbrc_fastqutils_samstat_legacy.py',
         'test_bvbrc_fastqutils_combined_reports.py']
argv = [sys.executable, '-B', '-m', 'pytest', '-q', *['tests/' + n for n in names],
        '--junitxml=' + str(OUT / 'results.xml'), '-p', 'no:cacheprovider',
        '--basetemp=' + str(OUT / 'tmp')]
env = dict(os.environ, PYTHONPATH=str(CANDIDATE), PYTHONDONTWRITEBYTECODE='1',
           PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', TMPDIR=str(OUT))
save('command.json', dict(argv=argv, cwd=str(CANDIDATE), tests=names,
     memory_limit_bytes=20 * 1024**3, scratch_limit_bytes=LIMIT, wall_time_limit=None))
start = time.monotonic()
assert usage() < LIMIT
with (OUT / 'stdout.log').open('wb') as stdout, (OUT / 'stderr.log').open('wb') as stderr:
    process = subprocess.Popen(argv, cwd=CANDIDATE, env=env, stdout=stdout, stderr=stderr, preexec_fn=limits)
    save('started.json', dict(pid=process.pid, at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    while process.poll() is None:
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            if usage() >= LIMIT:
                process.terminate()
                process.wait()
                raise RuntimeError('verification_scratch_budget_exceeded')
after = snapshot()
save('source_after.json', after)
changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
receipt = dict(passed=process.returncode == 0 and not changed, exit_code=process.returncode,
    elapsed_seconds=time.monotonic() - start, source_file_count=len(before), changed_sources=changed,
    scratch_bytes=usage(), child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    live_service=False, native_producer_executed=False, episode_Workflow_verified=False,
    calculator214_included=False, production_changed=False)
save('receipt.json', receipt)
print(json.dumps(receipt, sort_keys=True))
print((OUT / 'stdout.log').read_text())
raise SystemExit(process.returncode or bool(changed))
