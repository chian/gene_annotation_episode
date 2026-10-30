"""Bounded practical execution regression checks at the initial ATAC routing snapshot."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys


PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
operation, attempt_name = sys.argv[1:3]
attempt = PACKET / attempt_name


def pin(path):
    path = Path(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'size_bytes': path.stat().st_size}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


if operation == 'launch':
    attempt.mkdir(exist_ok=False)
    snapshot = attempt / 'source_snapshot'
    for package in ('gene_annotation_episode', 'method_loop', 'tests'):
        shutil.copytree(REPO / package, snapshot / package,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    files = ['pyproject.toml', str(Path(__file__).resolve().relative_to(REPO))]
    for filename in files:
        target = snapshot / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / filename, target)
    for path in snapshot.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
    for path in sorted((p for p in snapshot.rglob('*') if p.is_dir()),
                       key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    snapshot.chmod(0o555)
    for name in ('temporary', 'cache'):
        (attempt / name).mkdir()
    python = REPO / '.venv/bin/python'
    rootsite = REPO / '.venv/lib/python3.12/site-packages'
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, rootsite))),
           'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONSAFEPATH': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
           'TMPDIR': str(attempt / 'temporary'), 'TMP': str(attempt / 'temporary'),
           'TEMP': str(attempt / 'temporary'), 'XDG_CACHE_HOME': str(attempt / 'cache'),
           'ATAC463_NATIVE_EXAMPLE_PATH': str(attempt / 'FILLED_NATIVE_EXAMPLE.json')}
    argv = [str(python), '-B', '-S', '-m', 'pytest', '-q', '--tb=short',
            '-p', 'no:cacheprovider', '--basetemp=' + str(attempt / 'temporary/pytest'),
            '--rootdir=' + str(snapshot),
            str(snapshot / 'tests/test_practical_execution_state.py'),
            str(snapshot / 'tests/test_practical_operations_loop.py'),
            str(snapshot / 'tests/test_execution_progress.py'),
            str(snapshot / 'tests/test_practical_yield.py'),
            '--junitxml=' + str(attempt / 'junit.xml'), *sys.argv[3:]]
    save(attempt / 'source_pins_before.json', [pin(p) for p in sorted(snapshot.rglob('*')) if p.is_file()])
    save(attempt / 'input_pins_before.json', [pin(snapshot / filename) for filename in files
                                            if '/native001/' in filename])
    save(attempt / 'binary_pins_before.json', [pin(python), pin(__file__)])
    sys.path.insert(0, str(snapshot))
else:
    sys.path.insert(0, str(attempt / 'source_snapshot'))

from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect

handle = NativeJobHandle(attempt / 'handle.json')
if operation == 'launch':
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env,
                                           'policy': policy.to_dict(), 'cwd': str(attempt)})
    prepare_job(argv, cwd=attempt, policy=policy, handle_path=handle.path,
                stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=env)
    resume_start(handle)
    print(json.dumps({'handle': str(handle.path), 'unit': handle.read()['unit'], 'state': status(handle)['state']}))
elif operation == 'collect':
    view = status(handle)
    if not view['terminal'] or not view['quiescent']:
        print(json.dumps(view))
        raise SystemExit(3)
    result = collect(handle)
    sources = json.loads((attempt / 'source_pins_before.json').read_text())
    after = [pin(row['path']) for row in sources]
    inputs = json.loads((attempt / 'input_pins_before.json').read_text())
    input_after = [pin(row['path']) for row in inputs]
    binaries = json.loads((attempt / 'binary_pins_before.json').read_text())
    binary_after = [pin(row['path']) for row in binaries]
    save(attempt / 'source_pins_after.json', after)
    save(attempt / 'input_pins_after.json', input_after)
    save(attempt / 'binary_pins_after.json', binary_after)
    drift = []
    for row in sources:
        path = REPO / Path(row['path']).relative_to(attempt / 'source_snapshot')
        if not path.exists():
            drift.append({'path': str(path), 'state': 'absent'})
        elif pin(path)['sha256'] != row['sha256']:
            drift.append({'path': str(path), 'state': 'changed'})
    receipt = {'returncode': result.returncode, 'terminal': view['terminal'],
               'quiescent': view['quiescent'], 'metadata': result.metadata,
               'source_pins_unchanged': sources == after, 'input_pins_unchanged': inputs == input_after,
               'binary_pins_unchanged': binaries == binary_after, 'checkout_drift': drift,
               'handle': str(handle.path), 'unit': handle.read()['unit']}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({k: receipt[k] for k in ('returncode', 'source_pins_unchanged',
                    'input_pins_unchanged', 'binary_pins_unchanged', 'unit')}))
    raise SystemExit(result.returncode)
else:
    raise ValueError('unsupported_operation')
