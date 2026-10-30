"""Administrative launcher; scientific imports/probes/tests run in one quota."""
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
    for version in ('2026-10-21-001', '2026-10-24-001'):
        publication = 'research/slotted_process_library/publications/' + version
        shutil.copytree(REPO / publication, snapshot / publication)
    native_program = 'resources/software/infernal-1.1.5/hmmer/src/phmmer'
    files = ['pyproject.toml', 'cases/gene_001/target.faa', 'cases/gene_001/target.fna', native_program,
        str(PACKET.relative_to(REPO) / 'CONTRACT.md'),
        str(PACKET.relative_to(REPO) / 'baseline/runtime.py'),
        str(PACKET.relative_to(REPO) / 'baseline/bvbrc_appservice_custody.py')]
    for relative in files:
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / relative, target)
    for path in snapshot.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
    (snapshot / native_program).chmod(0o555)
    for path in sorted((p for p in snapshot.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    snapshot.chmod(0o555)
    for subdirectory in ('temporary', 'cache'):
        (attempt / subdirectory).mkdir()
    python = REPO / '.venv/bin/python'
    refsite = REPO / 'reference/episode_tools/.venv/lib/python3.12/site-packages'
    rootsite = REPO / '.venv/lib/python3.12/site-packages'
    env = {'PYTHONPATH': os.pathsep.join(map(str, (snapshot, refsite, rootsite))),
        'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONSAFEPATH': '1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'TRANSPORT458_ORIGINAL_REPO': str(REPO),
        'TMPDIR': str(attempt / 'temporary'), 'TMP': str(attempt / 'temporary'),
        'TEMP': str(attempt / 'temporary'), 'XDG_CACHE_HOME': str(attempt / 'cache'),
        'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
    tests = sys.argv[3:] or ['tests/test_composed_episode_assignment_transport.py']
    argv = [str(python), '-B', '-S', '-m', 'pytest', '-q', '--tb=short', '-p', 'no:cacheprovider',
        '--basetemp=' + str(attempt / 'temporary/pytest'), '--rootdir=' + str(snapshot),
        '--junitxml=' + str(attempt / 'junit.xml'), *[str(snapshot / path) for path in tests]]
    pins = [pin(path) for path in sorted(snapshot.rglob('*')) if path.is_file()]
    save(attempt / 'source_pins_before.json', pins)
    retained = [REPO / 'verification/tool_graders_chromatin_workflow_2026-10-27_451/probe001/selected-branches.json',
        REPO / 'verification/tool_graders_chromatin_workflow_2026-10-27_451/check001/temporary/pytest/chromatin4510/state/state.sqlite3',
        REPO / 'verification/tool_graders_chromatin_workflow_2026-10-27_451/check002/temporary/pytest/chromatin4510/state/state.sqlite3',
        REPO / 'verification/tool_graders_chromatin_hic_binding_2026-10-27_457/check002/HIC_SOFTWARE.json']
    authority = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
    assert pin(authority)['sha256'] == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
    save(attempt / 'input_pins_before.json', [pin(path) for path in [python, Path(__file__), authority, *retained]])
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
    state = status(handle)
    if not state['terminal'] or not state['quiescent']:
        print(json.dumps({key: state[key] for key in ('state', 'terminal', 'quiescent')}))
        raise SystemExit(3)
    result = collect(handle)
    groups = {}
    for label in ('source', 'input'):
        before = json.loads((attempt / (label + '_pins_before.json')).read_bytes())
        after = [pin(row['path']) for row in before]
        save(attempt / (label + '_pins_after.json'), after)
        groups[label + '_pins_unchanged'] = before == after
    receipt = {'returncode': result.returncode, 'terminal': True, 'quiescent': True,
        'metadata': result.metadata, **groups, 'handle': str(handle.path), 'unit': handle.read()['unit']}
    save(attempt / 'receipt.json', receipt)
    print(json.dumps({key: receipt[key] for key in ('returncode', 'source_pins_unchanged', 'input_pins_unchanged', 'unit')}))
    raise SystemExit(result.returncode)
else:
    raise ValueError(operation)
