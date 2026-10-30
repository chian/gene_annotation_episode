"""Focused runner: 20GiB RAM, 4GiB scratch, no wall-time termination."""
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
HERE = Path(__file__).resolve().parent
LIMIT = 4 * 1024**3
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
def usage():
    return sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMIT, LIMIT))
def main():
    run = HERE / sys.argv[1]; run.mkdir(exist_ok=False)
    start = time.monotonic(); tracked = {}
    for name in ('incoming_before.json', 'frozen_before.json'):
        tracked.update(json.loads((HERE / name).read_text()))
    for source in sorted(HERE.glob('*.py')):
        tracked[str(source)] = sha(source)
        (run / (source.name + '.snapshot')).write_bytes(source.read_bytes())
    write(run / 'tracked_before.json', tracked)
    assert not [n for n, expected in tracked.items() if not Path(n).is_file() or sha(Path(n)) != expected]
    argv = [sys.executable, '-I', '-B', str(HERE / 'PYTEST_ENTRY_002.py'), str(run), *sys.argv[2:]]
    overrides = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'TMPDIR': str(run / 'runtime_tmp'), 'SAMSTAT_EVIDENCE': str(run / 'evidence')}
    (run / 'runtime_tmp').mkdir()
    env = {**os.environ, **overrides}; env.pop('PYTHONPATH', None)
    write(run / 'command.json', dict(argv=argv, cwd=str(HERE / 'candidate'), overrides=overrides,
        resume_checkpoint=env.get('SAMSTAT_RESUME_CHECKPOINT'),
        workflow_replay_input=env.get('SAMSTAT_WORKFLOW_REPLAY_INPUT'), memory_limit_bytes=20*1024**3,
        scratch_limit_bytes=LIMIT, wall_seconds=None))
    receipt = dict(started_at=datetime.now(timezone.utc).isoformat(), passed=False, argv=argv,
        memory_limit_bytes=20*1024**3, scratch_limit_bytes=LIMIT, wall_seconds=None,
        old_suites_run=False, native_producer_run=False, live_service_run=False)
    write(run / 'started.json', receipt)
    print(json.dumps(dict(started=True, run=str(run))), flush=True)
    try:
        assert usage() < LIMIT
        with (run / 'stdout.log').open('x') as stdout, (run / 'stderr.log').open('x') as stderr:
            process = subprocess.Popen(argv, cwd=HERE / 'candidate', env=env,
                stdout=stdout, stderr=stderr, preexec_fn=limits)
            write(run / 'process.json', dict(pid=process.pid, argv=argv))
            while process.poll() is None:
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    if usage() >= LIMIT:
                        process.terminate(); process.wait()
                        raise RuntimeError('218_scratch_budget_exceeded')
        receipt.update(exit_code=process.returncode, passed=process.returncode == 0)
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        (run / 'runner_error.log').write_text(traceback.format_exc())
    finally:
        after = {n: sha(Path(n)) if Path(n).is_file() else None for n in tracked}
        write(run / 'tracked_after.json', after)
        changed = [n for n in tracked if tracked[n] != after[n]]
        receipt.update(changed_inputs=changed, tracked_paths=len(tracked),
            ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-start,
            scratch_bytes=usage(), child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        receipt['passed'] = receipt['passed'] and not changed and receipt['scratch_bytes'] < LIMIT
        write(run / 'receipt.json', receipt)
        print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0 if receipt['passed'] else 1
if __name__ == '__main__':
    raise SystemExit(main())
