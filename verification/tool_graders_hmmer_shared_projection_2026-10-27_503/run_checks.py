"""HMMER shared-projection checks using the existing bounded verification runner.

Only stdlib staging and local lifecycle bootstrap run on the host. Application
imports, installation, dependency inspection, scientific work and tests execute
inside the selected 20 GiB/4 GiB/zero-swap/no-wall-limit handle.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]


def pin(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            h.update(block)
    return {'path': str(path), 'sha256': h.hexdigest(), 'size_bytes': path.stat().st_size}


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def freeze(root):
    for path in root.rglob('*'):
        if path.is_file():
            path.chmod(0o555 if os.access(path, os.X_OK) else 0o444)
    for path in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    root.chmod(0o555)


parser = argparse.ArgumentParser()
parser.add_argument('operation', choices=('launch', 'status', 'collect'))
parser.add_argument('attempt')
parser.add_argument('--mode', choices=('check',))
parser.add_argument('--dependencies-from', type=Path)
parser.add_argument('--test', action='append', required=False)
parser.add_argument('--support-file', action='append', default=[])
parser.add_argument('--native-phmmer', action='store_true')
parser.add_argument('--test-filter')
args = parser.parse_args()
if not args.attempt.isidentifier():
    parser.error('simple attempt name required')
attempt = PACKET / args.attempt
if args.operation == 'launch':
    if args.mode is None:
        parser.error('explicit mode required')
    attempt.mkdir(exist_ok=False)
    snapshot = attempt / 'source_snapshot'
    for package in ('gene_annotation_episode', 'method_loop'):
        shutil.copytree(REPO / package, snapshot / package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(REPO / 'tests', snapshot / 'tests',
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    captures = Path('verification/hmmer_reported_timing_actual_service_2026-10-22_001/workspace/public-search-http-captures')
    for key in ('26bc8bd463741aea924eabd181e41bfc91237dc04a04c7a3f5d03f6f64bd1e39',
                '4e88be472b0304cdea6ed5c38126eef0d7865b5345ad21863e9c9e318afc1c67',
                '4f8a4e3724b4713cc66862aca1fd3b6849fcfd5f55ddabd46e74f3accc29dc0a'):
        source = REPO / captures / key / 'response.entity'
        target = snapshot / captures / key / 'response.entity'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    selected_tests = args.test or ['test_hmmer_grading_publication.py',
        'test_hmmer_grading_api_returns.py', 'test_public_search.py']
    for name in selected_tests:
        path = REPO / 'tests' / name
        if not path.is_file() or path.parent != REPO / 'tests':
            parser.error('explicit top-level test file required')
    save(attempt / 'selected_tests.json', selected_tests)
    save(attempt / 'selected_filter.json', args.test_filter)
    if args.native_phmmer:
        native_paths = ['cases/gene_001/target.fna', 'cases/gene_001/target.faa',
            *['cases/gene_001/jobs/homology_001/' + name for name in (
                'job.json', 'reviewed.fasta', 'homology_search.stdout', 'hits.tbl', 'domains.tbl')],
            'resources/software/infernal-1.1.5/hmmer/src/phmmer']
        for name in native_paths:
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, target)
    for path in PACKET.glob('*.py'):
        dest = snapshot / path.relative_to(REPO)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    shutil.copyfile(REPO / 'pyproject.toml', snapshot / 'pyproject.toml')
    dependencies = attempt / 'dependencies'
    original = (args.dependencies_from.resolve(strict=True) if args.dependencies_from else
        REPO / '.venv/lib/python3.12/site-packages')
    shutil.copytree(original, dependencies, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    runtime = attempt / 'runtime'
    runtime.mkdir()
    python = runtime / 'python'
    shutil.copyfile(REPO / '.venv/bin/python', python)
    python.chmod(0o555)
    stdlib = runtime / 'lib/python3.12'
    shutil.copytree('/usr/lib/python3.12', stdlib,
        ignore=shutil.ignore_patterns('site-packages', 'dist-packages', '__pycache__', '*.pyc'))
    for name, root in (('source', snapshot), ('dependency', dependencies), ('stdlib', stdlib)):
        freeze(root)
        save(attempt / (name + '_pins_before.json'), [pin(p) for p in sorted(root.rglob('*')) if p.is_file()])
    save(attempt / 'binary_pins_before.json', [pin(python)])
    for name in ('temporary', 'cache', 'installed'):
        (attempt / name).mkdir()
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, dependencies))), 'PYTHONHOME': str(runtime),
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
        'TMPDIR': str(attempt / 'temporary'), 'TMP': str(attempt / 'temporary'), 'TEMP': str(attempt / 'temporary'),
        'XDG_CACHE_HOME': str(attempt / 'cache'), 'PIP_CACHE_DIR': str(attempt / 'cache/pip'),
        'HMMER503_ATTEMPT': str(attempt)}
    entry = snapshot / PACKET.relative_to(REPO) / 'bounded_entry.py'
    argv = [str(python), '-B', '-S', str(entry), str(attempt), args.mode]
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'mode': args.mode,
        'tests': selected_tests, 'support_files': args.support_file, 'native_phmmer': args.native_phmmer,
        'test_filter': args.test_filter,
        'policy': {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'wall_seconds': None}, 'swap_bytes': 0})

sys.path[:0] = [str(attempt / 'source_snapshot'), str(attempt / 'dependencies')]
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect

handle = NativeJobHandle(attempt / 'handle.json')
if args.operation == 'launch':
    prepare_job(argv, cwd=attempt, policy=LocalJobPolicy(21474836480, 4294967296, None),
        handle_path=handle.path, stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=env)
    resume_start(handle)
    print(json.dumps({'handle': str(handle.path), 'state': status(handle)['state'], 'unit': handle.read()['unit']}))
elif args.operation == 'status':
    view = status(handle)
    save(attempt / 'last_status.json', view)
    print(json.dumps({k: view[k] for k in ('state', 'terminal', 'quiescent')}))
else:
    view = status(handle)
    if not view['terminal'] or not view['quiescent']:
        print(json.dumps({k: view[k] for k in ('state', 'terminal', 'quiescent')}))
        raise SystemExit(3)
    result = collect(handle)
    unchanged = {}
    for name in ('source', 'dependency', 'stdlib', 'binary'):
        before = json.loads((attempt / (name + '_pins_before.json')).read_text())
        after = [pin(row['path']) for row in before]
        save(attempt / (name + '_pins_after.json'), after)
        unchanged[name + '_unchanged'] = before == after
    installed = attempt / 'installed'
    if any(installed.iterdir()):
        freeze(installed)
        save(attempt / 'installed_pins.json', [pin(p) for p in sorted(installed.rglob('*')) if p.is_file()])
    receipt = {'returncode': result.returncode, 'handle': str(handle.path), 'unit': handle.read()['unit'],
        'terminal': view['terminal'], 'quiescent': view['quiescent'], **unchanged, 'metadata': result.metadata}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'metadata'}))
    raise SystemExit(result.returncode if all(unchanged.values()) else 4)
