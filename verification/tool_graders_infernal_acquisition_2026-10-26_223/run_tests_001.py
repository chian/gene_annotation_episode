"""Operator verification using the existing bounded local job runner."""
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


repo = Path(__file__).resolve().parents[2]
directory = Path(__file__).resolve().parent / sys.argv[1]
directory.mkdir()
temporary = directory / 'temporary'
temporary.mkdir()
command = [str(repo / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    str(repo / 'tests/test_native_infernal_acquisition.py'),
    '--basetemp=' + str(temporary / 'pytest'), '--junitxml=' + str(directory / 'tests.xml'), *sys.argv[2:]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
environment = {'PYTHONPATH': str(repo), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(temporary), 'TMP': str(temporary), 'TEMP': str(temporary),
    'XDG_CACHE_HOME': str(directory / 'cache')}
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
receipt = {'command': command, 'policy': policy.to_dict(), 'environment': environment,
    'returncode': result.returncode, 'stdout_path': str(result.stdout_path),
    'stderr_path': str(result.stderr_path), 'metadata': result.metadata}
(directory / 'verification-receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({'returncode': result.returncode, 'receipt': str(directory / 'verification-receipt.json')}))
raise SystemExit(result.returncode)
