"""Selected bounded installation/checks with frozen source and original handles.

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
parser.add_argument('--mode', choices=('install', 'check'))
parser.add_argument('--dependencies-from', type=Path)
parser.add_argument('--test', action='append', required=False)
parser.add_argument('--case', action='append', required=False)
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
    for name in (args.test or ['test_barcode_shared_registration.py', 'test_barcode_input_authority.py', 'test_expression_nmf_execution_integration.py', 'test_atac_differential_execution_integration.py', 'test_atac_differential_operands.py', 'test_native_atac_differential_contracts.py']):
        path = REPO / 'tests' / name
        if not path.is_file() or path.parent != REPO / 'tests':
            parser.error('explicit top-level test file required')
        (snapshot / 'tests').mkdir(exist_ok=True)
        shutil.copyfile(path, snapshot / 'tests' / path.name)
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
        'BARCODE495_ATTEMPT': str(attempt),
        'BARCODE495_SOFTWARE': str(REPO / 'verification/tool_graders_barcode_native_2026-10-27_492/check004/native-software.json'),
        'BARCODE494_SOFTWARE': str(REPO / 'verification/tool_graders_barcode_native_2026-10-27_492/check004/native-software.json'),
        'NMF488_SOFTWARE': str(REPO / 'verification/tool_graders_expression_nmf_native_grader_2026-10-27_484/check003/native-software.json')}
    software_pins = {}
    for key in ('BARCODE495_SOFTWARE', 'NMF488_SOFTWARE'):
        descriptor = Path(env[key])
        software_pins[str(descriptor)] = pin(descriptor)
        selected = json.loads(descriptor.read_text())
        for expected in [selected['python'], *selected['implementation_files'], *selected['runtime_files']]:
            actual = pin(expected['path'])
            if actual != expected:
                raise ValueError('selected_software_file_changed:' + expected['path'])
            software_pins[actual['path']] = actual
    save(attempt / 'selected_software_pins_before.json', [software_pins[key] for key in sorted(software_pins)])
    entry = snapshot / PACKET.relative_to(REPO) / 'bounded_entry.py'
    selected_cases = []
    for selected_case in args.case or []:
        filename, separator, node = selected_case.partition('::')
        if Path(filename).name != filename or not (snapshot / 'tests' / filename).is_file():
            parser.error('selected case requires a staged top-level test file')
        selected_cases.append(str(snapshot / 'tests' / filename) + (separator + node if separator else ''))
    argv = [str(python), '-B', '-S', str(entry), str(attempt), args.mode, *selected_cases]
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'mode': args.mode,
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
    names = ['source', 'dependency', 'stdlib', 'binary']
    if (attempt / 'selected_software_pins_before.json').exists():
        names.append('selected_software')
    for name in names:
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
