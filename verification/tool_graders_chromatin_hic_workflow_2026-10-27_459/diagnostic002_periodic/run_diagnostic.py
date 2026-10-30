"""Administrative paired diagnosis using check002 frozen application sources."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
operation, name = sys.argv[1:3]
attempt = PACKET / name
snapshot = PACKET / 'check002/source_snapshot'


def pin(path):
    return {'path': str(path), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(), 'size_bytes': Path(path).stat().st_size}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


if operation == 'launch':
    mode = sys.argv[3]
    iterations = int(sys.argv[4]) if len(sys.argv) > 4 else 16
    assert mode in ('periodic', 'no_periodic')
    attempt.mkdir(exist_ok=False)
    for filename in ('diagnostic_schema.py', 'DIAGNOSTIC_INPUT.json', 'run_diagnostic.py'):
        shutil.copyfile(PACKET / filename, attempt / filename)
        (attempt / filename).chmod(0o444)
    (attempt / 'temporary').mkdir()
    (attempt / 'cache').mkdir()
    original = json.loads((PACKET / 'check002/source_pins_before.json').read_text())
    assert original == [pin(Path(row['path'])) for row in original]
    python = REPO / '.venv/bin/python'
    refsite = REPO / 'reference/episode_tools/.venv/lib/python3.12/site-packages'
    rootsite = REPO / '.venv/lib/python3.12/site-packages'
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, refsite, rootsite))), 'PYTHONNOUSERSITE': '1',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONSAFEPATH': '1', 'TMPDIR': str(attempt / 'temporary'),
        'TMP': str(attempt / 'temporary'), 'TEMP': str(attempt / 'temporary'),
        'XDG_CACHE_HOME': str(attempt / 'cache'), 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
    argv = [str(python), '-B', '-S', str(attempt / 'diagnostic_schema.py'), str(attempt), str(attempt / 'DIAGNOSTIC_INPUT.json'), mode, str(iterations)]
    pins = original + [pin(attempt / filename) for filename in ('diagnostic_schema.py', 'DIAGNOSTIC_INPUT.json', 'run_diagnostic.py')] + [pin(python)]
    save(attempt / 'pins_before.json', pins)
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect

handle = NativeJobHandle(attempt / 'handle.json')
if operation == 'launch':
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'policy': policy.to_dict(), 'cwd': str(attempt)})
    prepare_job(argv, cwd=attempt, policy=policy, handle_path=handle.path,
        stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=env)
    resume_start(handle)
    print(json.dumps({'handle': str(handle.path), 'unit': handle.read()['unit'], 'state': status(handle)['state'], 'mode': mode}))
elif operation == 'collect':
    view = status(handle)
    if not view['terminal'] or not view['quiescent']:
        print(json.dumps({key: view[key] for key in ('state', 'terminal', 'quiescent')}))
        raise SystemExit(3)
    result = collect(handle)
    before = json.loads((attempt / 'pins_before.json').read_text())
    after = [pin(Path(row['path'])) for row in before]
    save(attempt / 'pins_after.json', after)
    receipt = {'returncode': result.returncode, 'terminal': view['terminal'], 'quiescent': view['quiescent'],
        'metadata': result.metadata, 'pins_unchanged': before == after, 'handle': str(handle.path), 'unit': handle.read()['unit']}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({key: receipt[key] for key in ('returncode', 'pins_unchanged', 'unit')}))
    raise SystemExit(result.returncode)
