"""Run the scoped native Workflow tests under the existing caller-owned limits."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
import method_loop


def snapshot():
    paths = set((ROOT / 'gene_annotation_episode').rglob('*.py'))
    paths.update(Path(method_loop.__file__).parent.rglob('*.py'))
    paths.update(ROOT / 'tests' / name for name in (
        'test_native_infernal_preparation_driver.py',
        'test_native_infernal_preparation_results_integration.py',
        'test_native_infernal_preparation_workflow_modes.py'))
    paths.update((Path(__file__).resolve(), Path(__file__).with_name('pytest_worker.py')))
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename and filename.endswith('.py'):
            paths.add(Path(filename))
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_file()}


def main():
    label = sys.argv[1]
    directory = Path(__file__).resolve().parent / label
    directory.mkdir()
    temporary = directory / 'temporary'
    temporary.mkdir()
    before = snapshot()
    started = datetime.now(timezone.utc).isoformat()
    (directory / 'sources_before.json').write_text(json.dumps(before, indent=2) + '\n')
    command = [str(ROOT / '.venv/bin/python'), str(Path(__file__).with_name('pytest_worker.py')), '-vv', '-p', 'no:cacheprovider',
        str(ROOT / 'tests/test_native_infernal_preparation_workflow_modes.py'),
        '--basetemp=' + str(temporary / 'pytest'), '--junitxml=' + str(directory / 'tests.xml'), *sys.argv[2:]]
    result = run_local_job(command, cwd=directory, policy=LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None),
        stdout_path=directory / 'stdout.log', stderr_path=directory / 'stderr.log',
        env={**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1',
            'TMPDIR': str(temporary), 'XDG_CACHE_HOME': str(temporary / 'cache')})
    after = snapshot()
    (directory / 'sources_after.json').write_text(json.dumps(after, indent=2) + '\n')
    receipt = {'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
        'command': command, 'returncode': result.returncode, 'metadata': result.metadata,
        'source_changes_during_run': {p: {'before': before.get(p), 'after': after.get(p)}
            for p in before.keys() | after.keys() if before.get(p) != after.get(p)}}
    (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'directory': str(directory), 'returncode': result.returncode,
        'source_changes_during_run': list(receipt['source_changes_during_run'])}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
