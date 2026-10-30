"""Run explicitly selected synthetic checks under the required local limits."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

root = Path(__file__).resolve().parents[2]
directory = Path(__file__).parent / ('check_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
directory.mkdir()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
command = [str(root / '.venv/bin/python'), '-B', '-m', 'pytest',
    *[str(root / p) for p in sys.argv[1:]], '-q', '-p', 'no:cacheprovider', '--basetemp=' + str(directory / 'tmp')]
result = run_local_job(command, cwd=directory, policy=policy,
    stdout_path=directory / 'stdout.txt', stderr_path=directory / 'stderr.txt',
    env={'PYTHONPATH': str(root) + ':' + str(root / 'tests'), 'PYTHONDONTWRITEBYTECODE': '1'})
receipt = dict(command=command, policy=policy.to_dict(), returncode=result.returncode, metadata=result.metadata,
    stdout_path=str(result.stdout_path), stderr_path=str(result.stderr_path))
(directory / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(directory)
print(result.stdout_path.read_text()[-14000:])
print(result.stderr_path.read_text()[-4000:])
raise SystemExit(result.returncode)
