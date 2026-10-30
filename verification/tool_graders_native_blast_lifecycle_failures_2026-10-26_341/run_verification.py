"""Run contract-scoped tests through the existing bounded local lifecycle."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


def pins():
    names = ['gene_annotation_episode/native_blast_database_result_publication.py',
        'gene_annotation_episode/native_blast_database_results.py',
        'tests/test_native_blast_database_results.py',
        'gene_annotation_episode/native_blast_database_metadata.py',
        'gene_annotation_episode/native_blast_standard_database_metadata.py',
        'gene_annotation_episode/native_blast_database_result_worker.py',
        'gene_annotation_episode/local_jobs.py', 'gene_annotation_episode/native_lifecycle.py']
    return [{'path': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
        'size_bytes': (ROOT / name).stat().st_size} for name in names]


def main():
    label = sys.argv[1]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory = Path(__file__).resolve().parent / (label + '_' + stamp)
    directory.mkdir()
    (directory / 'scratch').mkdir()
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q',
        '-p', 'no:cacheprovider', '--basetemp', str(directory / 'tmp'),
        str(ROOT / 'tests/test_native_blast_database_results.py'), *sys.argv[2:]]
    record = {'command': command, 'cwd': str(directory), 'policy': policy.to_dict(),
        'pins_before': pins(), 'started_at': datetime.now(timezone.utc).isoformat()}
    (directory / 'invocation.json').write_text(json.dumps(record, indent=2) + '\n')
    print(directory, flush=True)
    env = {'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
        **{key: str(directory / 'scratch') for key in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME')}}
    try:
        result = run_local_job(command, cwd=directory, policy=policy,
            stdout_path=directory / 'pytest.stdout', stderr_path=directory / 'pytest.stderr', env=env)
    except AcquisitionError as error:
        record.update(error={'code': error.code, 'phase': error.phase, 'operational': error.operational})
        returncode = 1
    else:
        record.update(returncode=result.returncode, metadata=result.metadata)
        returncode = result.returncode
    record.update(pins_after=pins(), ended_at=datetime.now(timezone.utc).isoformat())
    (directory / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'returncode': returncode, 'receipt': str(directory / 'receipt.json')}), flush=True)
    raise SystemExit(returncode)


if __name__ == '__main__':
    main()
