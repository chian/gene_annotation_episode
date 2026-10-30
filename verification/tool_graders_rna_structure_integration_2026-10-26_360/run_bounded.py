"""Record actual test/native execution through the existing local lifecycle."""
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]


def main():
    label, *command = sys.argv[1:]
    directory = PACKET / label
    directory.mkdir(exist_ok=False)
    (directory / 'tmp').mkdir()
    (directory / 'cache').mkdir()
    policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
    env = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(REPO),
        'TMPDIR': str(directory / 'tmp'), 'TMP': str(directory / 'tmp'), 'TEMP': str(directory / 'tmp'),
        'XDG_CACHE_HOME': str(directory / 'cache'), 'PIP_CACHE_DIR': str(directory / 'cache/pip'),
        'PYTEST_ADDOPTS': '-p no:cacheprovider'}
    paths = [*sorted((REPO / 'gene_annotation_episode').glob('*rna_structure*.py')),
        *sorted((REPO / 'tests').glob('test_native_rna_structure*.py')),
        *(REPO / 'gene_annotation_episode' / name for name in ('local_jobs.py', 'native_lifecycle.py',
            'practical_execution_state.py', 'execution_contracts.py', 'communication.py', 'practical_execution_records.py',
            'practical_execution_operations.py', 'execution_progress.py', 'execution_episodes.py', 'episode_receipts.py',
            'runtime.py', 'episode_return_records.py', 'practical_resource_episodes.py'))]
    hashes = {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    for path in paths:
        target = directory / 'source' / path.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    argv = [str(REPO / '.venv/bin/python'), '-B', *command]
    (directory / 'selected_request.json').write_text(json.dumps({'argv': argv, 'cwd': str(directory),
        'policy': policy.to_dict(), 'environment': env, 'source_sha256_before': hashes}, indent=2) + '\n')
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory / 'stdout.txt',
        stderr_path=directory / 'stderr.txt', env=env)
    after = {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    receipt = {'returncode': result.returncode, 'stdout_path': str(result.stdout_path),
        'stderr_path': str(result.stderr_path), 'metadata': result.metadata,
        'source_sha256_after': after, 'sources_unchanged': after == hashes}
    (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'directory': str(directory), 'returncode': result.returncode, 'sources_unchanged': after == hashes}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
