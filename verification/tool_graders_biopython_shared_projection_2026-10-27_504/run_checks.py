"""Biopython shared projection checks using the existing bounded verification runner.

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
parser.add_argument('--mode', choices=('check',), default='check')
parser.add_argument('--dependencies-from', type=Path)
parser.add_argument('--test', action='append', required=False)
parser.add_argument('--support-file', action='append', default=[])
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
    selected_tests = args.test or ['test_biopython_shared_projection.py']
    save(attempt / 'selected_tests.json', selected_tests)
    shutil.copytree(REPO / 'tests', snapshot / 'tests', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    fixture_roots = ['research/slotted_process_library/publications/2026-10-24-001',
        'verification/tool_graders_batch_001/biopython_pairwise',
        'verification/tool_graders_batch_001/integration',
        'verification/tool_graders_batch_001/prodigal']
    for relative in fixture_roots:
        shutil.copytree(REPO / relative, snapshot / relative, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for fixture in ('tool_graders_protein_structure_inputs_2026-10-27_386',
            'tool_graders_protein_structure_execution_2026-10-27_390',
            'tool_graders_protein_structure_workflow_2026-10-27_410'):
        source = REPO / 'verification' / fixture / 'fixture_helpers.py'
        destination = snapshot / source.relative_to(REPO)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    fixtures = 'verification/tool_graders_protein_structure_inputs_2026-10-27_386/fixtures'
    shutil.copytree(REPO / fixtures, snapshot / fixtures)
    for fixture in ('tool_graders_protein_structure_shared_contract_2026-10-27_380',
            'tool_graders_protein_structure_result_host_contract_2026-10-27_403'):
        for source in (REPO / 'verification' / fixture).glob('*.md'):
            destination = snapshot / source.relative_to(REPO)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
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
    # Separately selected native services do not inherit the enclosing worker's
    # PYTHONHOME. The standard bin/lib layout keeps their interpreter and stdlib
    # resolution within this same frozen closure too.
    (runtime / 'bin').mkdir()
    python = runtime / 'bin/python'
    shutil.copyfile(REPO / '.venv/bin/python', python)
    python.chmod(0o555)
    # Service-local interpreter startup must also exclude the host user's site.
    # No alternate Python home is declared: the copied lib remains authoritative.
    venv_config = runtime / 'pyvenv.cfg'
    venv_config.write_text('include-system-site-packages = false\n')
    venv_config.chmod(0o444)
    stdlib = runtime / 'lib/python3.12'
    shutil.copytree('/usr/lib/python3.12', stdlib,
        ignore=shutil.ignore_patterns('site-packages', 'dist-packages', '__pycache__', '*.pyc'))
    # Existing structure-worker fixtures supply their own application PYTHONPATH.
    # Resolve dependencies in the frozen interpreter too, without processing
    # copied environment-specific .pth files or falling back to host packages.
    site = stdlib / 'dist-packages'
    site.mkdir()
    (site / 'frozen_dependencies.pth').write_text(str(dependencies) + '\n')
    for name, root in (('source', snapshot), ('dependency', dependencies), ('stdlib', stdlib)):
        freeze(root)
        save(attempt / (name + '_pins_before.json'), [pin(p) for p in sorted(root.rglob('*')) if p.is_file()])
    save(attempt / 'binary_pins_before.json', [pin(python), pin(venv_config)])
    for name in ('temporary', 'cache', 'installed'):
        (attempt / name).mkdir()
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, dependencies))), 'PYTHONHOME': str(runtime),
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
        'TMPDIR': str(attempt / 'temporary'), 'TMP': str(attempt / 'temporary'), 'TEMP': str(attempt / 'temporary'),
        'XDG_CACHE_HOME': str(attempt / 'cache'), 'PIP_CACHE_DIR': str(attempt / 'cache/pip'),
        'BIOPYTHON504_ATTEMPT': str(attempt)}
    authority = Path('/home/chia/.codex/attachments/6960b4a1-b2e0-46d4-8003-fcb7685a2232/pasted-text-1.txt')
    authority_pin = pin(authority)
    assert authority_pin['sha256'] == 'f43e46c2433c44d320d1bbdb4e08f6cb85608a29d50911c2be28eb963581b6dc'
    save(attempt / 'user_supplied_authority_pin.json', authority_pin)
    entry = snapshot / PACKET.relative_to(REPO) / 'bounded_entry.py'
    argv = [str(python), '-B', '-S', str(entry), str(attempt), args.mode]
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'mode': args.mode,
        'tests': selected_tests, 'support_files': args.support_file,
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
