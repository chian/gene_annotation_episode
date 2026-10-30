"""Resource-bounded one-test runner; each invocation keeps a separate receipt."""
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
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def usage():
    return sum(path.stat().st_size for path in HERE.rglob('*') if path.is_file())


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMIT, LIMIT))


def main():
    run = HERE / ('host_run_' + sys.argv[1])
    run.mkdir(exist_ok=False)
    start = time.monotonic()
    tracked = {}
    for name in ('incoming_before.json', 'frozen_before.json'):
        tracked.update(json.loads((HERE / name).read_text()))
    for name in ('FREEZE_INPUTS_001.py', 'PYTEST_ENTRY_001.py', 'RUN_HOST_001.py', 'test_native_sra_host.py'):
        tracked[str(HERE / name)] = sha(HERE / name)
        (run / (name + '.snapshot')).write_bytes((HERE / name).read_bytes())
    missing = [name for name, expected in tracked.items() if not Path(name).is_file() or sha(Path(name)) != expected]
    write(run / 'tracked_before.json', tracked)
    assert not missing, missing
    argv = [sys.executable, '-I', '-B', str(HERE / 'PYTEST_ENTRY_001.py'), str(run)]
    overrides = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                 'TMPDIR': str(run / 'runtime_tmp'), 'SRA_HOST_EVIDENCE': str(run / 'evidence')}
    (run / 'runtime_tmp').mkdir()
    environment = {**os.environ, **overrides}
    environment.pop('PYTHONPATH', None)
    if len(sys.argv) > 2:
        overrides['SRA_HOST_RESUME_CHECKPOINT'] = str(Path(sys.argv[2]).resolve())
        environment['SRA_HOST_RESUME_CHECKPOINT'] = overrides['SRA_HOST_RESUME_CHECKPOINT']
    write(run / 'command.json', dict(argv=argv, cwd=str(HERE / 'candidate'),
        environment_overrides={**overrides, 'PYTHONPATH': None},
        memory_limit_bytes=20 * 1024**3, scratch_limit_bytes=LIMIT, wall_seconds=None))
    receipt = dict(started_at=datetime.now(timezone.utc).isoformat(), passed=False, argv=argv,
        memory_limit_bytes=20 * 1024**3, scratch_limit_bytes=LIMIT, no_wall_time_limit=True,
        expected_new_test_count=1, old_suites_run=False, workflow_run=False,
        native_producers_executed=0, live_service_run=False)
    write(run / 'started.json', receipt)
    print(json.dumps(dict(started=True, output_directory=str(run)), sort_keys=True), flush=True)
    try:
        assert usage() < LIMIT
        with (run / 'stdout.log').open('x') as stdout, (run / 'stderr.log').open('x') as stderr:
            process = subprocess.Popen(argv, cwd=HERE / 'candidate', env=environment,
                stdout=stdout, stderr=stderr, preexec_fn=limits)
            while process.poll() is None:
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    if usage() >= LIMIT:
                        process.terminate()
                        process.wait()
                        raise RuntimeError('verification_scratch_budget_exceeded')
        receipt.update(exit_code=process.returncode, passed=process.returncode == 0)
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error), passed=False)
        (run / 'runner_error.log').write_text(traceback.format_exc())
    finally:
        after = {name: sha(Path(name)) if Path(name).is_file() else None for name in tracked}
        write(run / 'tracked_after.json', after)
        changed = [name for name in tracked if tracked[name] != after[name]]
        receipt.update(changed_inputs=changed, tracked_paths=len(tracked),
            ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - start,
            scratch_bytes=usage(), child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        receipt['passed'] = receipt['passed'] and not changed and receipt['scratch_bytes'] < LIMIT
        write(run / 'receipt.json', receipt)
        print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
