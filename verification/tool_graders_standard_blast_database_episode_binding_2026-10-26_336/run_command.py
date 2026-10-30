"""Execute selected development commands under the required local limits."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

root = Path(__file__).resolve().parents[2]
directory = Path(__file__).parent / ('check_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
directory.mkdir()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
args = sys.argv[1:]
if args[0] == 'pytest':
    command = [str(root / '.venv/bin/python'), '-B', '-m', 'pytest',
        *[str(root / value) if value.startswith('tests/') else value for value in args[1:]],
        '-q', '-p', 'no:cacheprovider', '--basetemp=' + str(directory / 'tmp')]
else:
    command = [str(root / '.venv/bin/python'), '-B', *[str(root / value) if value.startswith('verification/') else value for value in args]]
sources = [*sorted((root / 'gene_annotation_episode').glob('*.py')), *sorted((root / 'tests').glob('test_native_blast*.py'))]
snapshot = [dict(path=str(p.relative_to(root)), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), size_bytes=p.stat().st_size) for p in sources]
(directory / 'source_snapshot.json').write_text(json.dumps(snapshot, indent=2) + '\n')
result = run_local_job(command, cwd=directory, policy=policy, stdout_path=directory / 'stdout.txt', stderr_path=directory / 'stderr.txt',
    env={'PYTHONPATH': str(root) + ':' + str(root / 'tests'), 'PYTHONDONTWRITEBYTECODE': '1'})
receipt = dict(command=command, policy=policy.to_dict(), returncode=result.returncode, metadata=result.metadata,
    stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path))
(directory / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(directory, flush=True)
print(result.stdout_path.read_text()[-18000:])
print(result.stderr_path.read_text()[-4000:])
raise SystemExit(result.returncode)
