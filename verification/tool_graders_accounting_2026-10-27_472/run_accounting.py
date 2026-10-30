"""Administrative launch/collection only; accounting executes in one quota."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
ATTEMPT = PACKET / 'check001'
operation = sys.argv[1]


def pin(path):
    path = Path(path)
    return {'path': str(path), 'resolved_path': str(path.resolve()),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'size_bytes': path.stat().st_size}


def save(path, value):
    with path.open('x') as output:
        json.dump(value, output, indent=2, allow_nan=False)
        output.write('\n')


if operation == 'launch':
    ATTEMPT.mkdir(exist_ok=False)
    source = ATTEMPT / 'source_snapshot'
    shutil.copytree(ROOT / 'gene_annotation_episode', source / 'gene_annotation_episode',
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    original_script = ROOT / 'research/tool_grader_goal_2026-10-24/apply_progress_110.py'
    script = source / 'apply_progress_110.py'
    shutil.copyfile(original_script, script)
    shutil.copyfile(Path(__file__), source / 'run_accounting.py')
    shutil.copyfile(PACKET / 'ACCOUNTING_SCOPE.md', source / 'ACCOUNTING_SCOPE.md')
    for path in source.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
    for path in sorted((p for p in source.rglob('*') if p.is_dir()),
                       key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    source.chmod(0o555)
    for name in ('temporary', 'cache'):
        (ATTEMPT / name).mkdir()
    python = ROOT / '.venv/bin/python'
    authority = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
    assert pin(authority)['sha256'] == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
    save(ATTEMPT / 'source_pins_before.json',
        [pin(p) for p in sorted(source.rglob('*')) if p.is_file()])
    save(ATTEMPT / 'input_pins_before.json',
        [pin(p) for p in (python, authority, original_script,
                         ROOT / 'research/tool_grader_goal_2026-10-24/SCOPE.json',
                         ROOT / 'research/tool_grader_goal_2026-10-24/PROGRESS_UPDATE_109.json')])

sys.path.insert(0, str(ATTEMPT / 'source_snapshot'))
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, prepare_job, resume_start, status, collect

handle = NativeJobHandle(ATTEMPT / 'handle.json')
if operation == 'launch':
    argv = [str(python), '-B', '-S', str(script), str(ROOT), str(ATTEMPT)]
    env = {'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONSAFEPATH': '1', 'TMPDIR': str(ATTEMPT / 'temporary'),
        'TMP': str(ATTEMPT / 'temporary'), 'TEMP': str(ATTEMPT / 'temporary'),
        'XDG_CACHE_HOME': str(ATTEMPT / 'cache')}
    policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296,
                           wall_seconds=None)
    save(ATTEMPT / 'selected_request.json', {'argv': argv, 'environment': env,
        'policy': policy.to_dict(), 'cwd': str(ATTEMPT)})
    prepare_job(argv, cwd=ATTEMPT, policy=policy, handle_path=handle.path,
        stdout_path=ATTEMPT / 'stdout.txt', stderr_path=ATTEMPT / 'stderr.txt', env=env)
    resume_start(handle)
    print(json.dumps({'handle': str(handle.path), 'unit': handle.read()['unit'],
                      'state': status(handle)['state']}))
elif operation == 'collect':
    observed = status(handle)
    if not observed['terminal'] or not observed['quiescent']:
        print(json.dumps({k: observed[k] for k in ('state', 'terminal', 'quiescent')}))
        raise SystemExit(3)
    result = collect(handle)
    groups = {}
    for label in ('source', 'input'):
        before = json.loads((ATTEMPT / (label + '_pins_before.json')).read_bytes())
        after = [pin(row['path']) for row in before]
        save(ATTEMPT / (label + '_pins_after.json'), after)
        groups[label + '_pins_unchanged'] = before == after
    receipt = {'returncode': result.returncode, 'terminal': True, 'quiescent': True,
        'metadata': result.metadata, **groups, 'handle': str(handle.path),
        'unit': handle.read()['unit']}
    save(ATTEMPT / 'receipt.json', receipt)
    print(json.dumps(receipt))
    raise SystemExit(result.returncode)
else:
    raise ValueError(operation)
