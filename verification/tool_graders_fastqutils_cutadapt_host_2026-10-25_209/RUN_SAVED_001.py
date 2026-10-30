"""Verify the original saved host result without any new acquisition."""
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

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE / 'host_run_002'
LIMIT = 4 * 1024**3


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def usage():
    return sum(path.stat().st_size for path in HERE.rglob('*') if path.is_file())


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMIT, LIMIT))


def main():
    run = HERE / ('host_saved_' + sys.argv[1])
    run.mkdir(exist_ok=False)
    started = time.monotonic()
    originals = sorted({path.resolve() for path in (ORIGINAL / 'tmp').glob('*/state/state.sqlite3')})
    assert len(originals) == 1, originals
    host = originals[0].parent.parent
    tracked = {}
    for name in ('incoming_before.json', 'frozen_before.json'):
        tracked.update(json.loads((HERE / name).read_text()))
    for path in sorted(ORIGINAL.rglob('*')):
        if path.is_file():
            tracked[str(path)] = sha(path)
    scripts = ['PYTEST_SAVED_ENTRY_001.py', 'RUN_SAVED_001.py', 'test_native_cutadapt_saved.py',
               'test_native_cutadapt_host.py', 'HARNESS_CORRECTIONS_001.md']
    for name in scripts:
        tracked[str(HERE / name)] = sha(HERE / name)
        (run / (name + '.snapshot')).write_bytes((HERE / name).read_bytes())
    assert all(sha(Path(name)) == expected for name, expected in tracked.items())
    save(run / 'tracked_before.json', tracked)
    assert not any(path.is_symlink() for path in host.rglob('*'))
    shutil.copytree(host, run / 'restored_host')
    restoration = {str(path.relative_to(host)): sha(path) for path in sorted(host.rglob('*')) if path.is_file()}
    assert all(sha(run / 'restored_host' / name) == expected for name, expected in restoration.items())
    save(run / 'restored_host_before.json', restoration)
    argv = [sys.executable, '-I', '-B', str(HERE / 'PYTEST_SAVED_ENTRY_001.py'), str(run)]
    overrides = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'TMPDIR': str(run / 'runtime_tmp'), 'CUTADAPT_HOST_EVIDENCE': str(run / 'evidence'),
        'CUTADAPT_SAVED_RUN': str(run)}
    (run / 'runtime_tmp').mkdir()
    environment = {**os.environ, **overrides}
    environment.pop('PYTHONPATH', None)
    save(run / 'command.json', dict(argv=argv, cwd=str(HERE / 'candidate'),
        environment_overrides={**overrides, 'PYTHONPATH': None}, original_saved_host=str(host),
        memory_limit_bytes=20 * 1024**3, scratch_limit_bytes=LIMIT, wall_seconds=None))
    receipt = dict(started_at=datetime.now(timezone.utc).isoformat(), passed=False,
        verification_kind='saved_evidence_continuation', source_run='host_run_002', source_run_exit_code=1,
        argv=argv, memory_limit_bytes=20 * 1024**3, scratch_limit_bytes=LIMIT, no_wall_time_limit=True,
        expected_new_test_count=1, acquisition_path_repeated=False, native_producers_executed=0,
        live_service_run=False, workflow_run=False)
    save(run / 'started.json', receipt)
    print(json.dumps(dict(started=True, output_directory=str(run), acquisition_path_repeated=False)), flush=True)
    try:
        assert usage() < LIMIT
        with (run / 'stdout.log').open('x') as stdout, (run / 'stderr.log').open('x') as stderr:
            process = subprocess.Popen(argv, cwd=HERE / 'candidate', env=environment, stdout=stdout,
                stderr=stderr, preexec_fn=limits)
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
        save(run / 'tracked_after.json', after)
        changed = [name for name in tracked if tracked[name] != after[name]]
        restored_after = {str(path.relative_to(run / 'restored_host')): sha(path)
                          for path in sorted((run / 'restored_host').rglob('*')) if path.is_file()}
        save(run / 'restored_host_after.json', restored_after)
        restored_changes = [name for name in set(restoration) | set(restored_after)
                            if restoration.get(name) != restored_after.get(name)]
        receipt.update(changed_inputs=changed, tracked_paths=len(tracked), restored_file_changes=restored_changes,
            ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - started,
            scratch_bytes=usage(), child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        receipt['passed'] = receipt['passed'] and not changed and receipt['scratch_bytes'] < LIMIT
        save(run / 'receipt.json', receipt)
        print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    try:
        code = main()
    except Exception as error:
        run = HERE / ('host_saved_' + sys.argv[1])
        run.mkdir(exist_ok=True)
        (run / 'preflight_error.log').write_text(traceback.format_exc())
        if not (run / 'receipt.json').exists():
            save(run / 'receipt.json', dict(passed=False, exit_code=1, phase='runner_preflight',
                error_type=type(error).__name__, error=str(error), acquisition_path_repeated=False,
                recorded_at=datetime.now(timezone.utc).isoformat()))
        raise
    raise SystemExit(code)
