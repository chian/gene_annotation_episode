"""Administrative launch/collection of the diagnosed HIC fixture correction.

The full Workflow test remains inside the ordinary 20 GiB/4 GiB native lifecycle.
Use the original459/check003 production/input bytes to isolate the fixture fix.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
BASE = REPO / 'verification/tool_graders_chromatin_hic_workflow_2026-10-27_459/check003/source_snapshot'
AUTHORITY = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
AUTHORITY_SHA = '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
operation, name = sys.argv[1:3]
attempt = PACKET / name


def pin(path):
    path = Path(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'size_bytes': path.stat().st_size}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


if operation == 'launch':
    attempt.mkdir(exist_ok=False)
    snapshot = attempt / 'source_snapshot'
    for package in ('gene_annotation_episode', 'method_loop'):
        shutil.copytree(BASE / package, snapshot / package,
            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    files = ['tests/test_native_hic_chromatin_workflow.py', 'pyproject.toml',
        'verification/tool_graders_chromatin_workflow_2026-10-27_451/fixture_helpers.py',
        'verification/tool_graders_chromatin_hic_workflow_2026-10-27_459/fixture_helpers.py',
        'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json',
        'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/HIC_WORKFLOW_VERIFICATION_015.md',
        'verification/tool_graders_hic_workflow_repair_2026-10-27_465/run_bounded.py',
        'verification/tool_graders_hic_workflow_repair_2026-10-27_465/REPAIR_CONTRACT.md']
    for fixture in ('native009/valid', 'native010/present_zero_block'):
        prefix = 'verification/tool_graders_chromatin_hic_native_2026-10-27_454/' + fixture + '/'
        files.extend(prefix + filename for filename in ('output.hic', 'BYTE_AUDIT.json', 'OUTCOME.json'))
    files += [str(p.relative_to(BASE)) for p in
        (BASE / 'research/slotted_process_library/publications/2026-10-24-001').rglob('*') if p.is_file()]
    for filename in files:
        owned = filename == 'tests/test_native_hic_chromatin_workflow.py' or filename.startswith(
            'verification/tool_graders_hic_workflow_repair_2026-10-27_465/')
        target = snapshot / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile((REPO if owned else BASE) / filename, target)
    save(attempt / 'source_origin.json', {'production_and_original_input_base': str(BASE),
        'corrected_test_and_administration_base': str(REPO),
        'original_failed_attempt': str(BASE.parent),
        'scope': 'full seven-test Workflow suite; correction only to declared-absent fixture cleanup'})
    for path in snapshot.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
    for path in sorted([p for p in snapshot.rglob('*') if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    snapshot.chmod(0o555)
    for directory in ('temporary', 'cache'):
        (attempt / directory).mkdir()
    assert pin(AUTHORITY)['sha256'] == AUTHORITY_SHA
    python = REPO / '.venv/bin/python'
    refsite = REPO / 'reference/episode_tools/.venv/lib/python3.12/site-packages'
    rootsite = REPO / '.venv/lib/python3.12/site-packages'
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, refsite, rootsite))), 'PYTHONNOUSERSITE': '1',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONSAFEPATH': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        'WORKFLOW459_ATTEMPT': str(attempt), 'TMPDIR': str(attempt / 'temporary'),
        'TMP': str(attempt / 'temporary'), 'TEMP': str(attempt / 'temporary'), 'XDG_CACHE_HOME': str(attempt / 'cache'),
        'HDF5_PLUGIN_PATH': str(attempt / 'no-hdf5-plugins'), 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
    argv = [str(python), '-B', '-S', '-m', 'pytest', '-q', '--tb=short', '-p', 'no:cacheprovider',
        '--basetemp=' + str(attempt / 'temporary/pytest'), '--rootdir=' + str(snapshot),
        str(snapshot / 'tests/test_native_hic_chromatin_workflow.py'), '--junitxml=' + str(attempt / 'junit.xml')]
    save(attempt / 'source_pins_before.json', [pin(p) for p in sorted(snapshot.rglob('*')) if p.is_file()])
    save(attempt / 'binary_pins_before.json', [pin(python), pin(__file__)])
    save(attempt / 'original_goal_identity.json', {'path': str(AUTHORITY), 'sha256': AUTHORITY_SHA})
    sys.path.insert(0, str(snapshot))
else:
    sys.path.insert(0, str(attempt / 'source_snapshot'))

from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect

handle = NativeJobHandle(attempt / 'handle.json')
if operation == 'launch':
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
    save(attempt / 'selected_request.json', {'argv': argv, 'environment': env, 'policy': policy.to_dict(), 'cwd': str(attempt)})
    prepare_job(argv, cwd=attempt, policy=policy, handle_path=handle.path,
        stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=env)
    resume_start(handle)
    print(json.dumps({'handle': str(handle.path), 'unit': handle.read()['unit'], 'state': status(handle)['state']}))
elif operation == 'collect':
    view = status(handle)
    if not view['terminal'] or not view['quiescent']:
        print(json.dumps({key: view[key] for key in ('state', 'terminal', 'quiescent')}))
        raise SystemExit(3)
    result = collect(handle)
    before = json.loads((attempt / 'source_pins_before.json').read_text())
    after = [pin(row['path']) for row in before]
    binaries = json.loads((attempt / 'binary_pins_before.json').read_text())
    binaries_after = [pin(row['path']) for row in binaries]
    save(attempt / 'source_pins_after.json', after)
    save(attempt / 'binary_pins_after.json', binaries_after)
    receipt = {'returncode': result.returncode, 'terminal': view['terminal'], 'quiescent': view['quiescent'],
        'metadata': result.metadata, 'source_pins_unchanged': before == after,
        'binary_pins_unchanged': binaries == binaries_after, 'handle': str(handle.path), 'unit': handle.read()['unit']}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({key: receipt[key] for key in
        ('returncode', 'source_pins_unchanged', 'binary_pins_unchanged', 'unit')}))
    raise SystemExit(result.returncode)
else:
    raise ValueError('unknown operation')
