"""Run explicitly selected synthetic tests through the existing local lifecycle."""
import json
import os
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).resolve().parent
check = packet / sys.argv[1]
check.mkdir()
for name in ['temporary', 'cache']:
    (check / name).mkdir()
tests = sys.argv[2:] or ['tests/test_native_blast_standard_database_contracts.py',
    'tests/test_native_blast_standard_database_driver.py', 'tests/test_native_blast_standard_database_tool_info.py']
command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
           '--basetemp', str(check / 'temporary/pytest'), *[str(ROOT / p) for p in tests]]
env = {**os.environ, 'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(check / 'temporary'), 'TMP': str(check / 'temporary'), 'TEMP': str(check / 'temporary'),
    'XDG_CACHE_HOME': str(check / 'cache')}
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
sources = ['gene_annotation_episode/native_blast_standard_database_' + name + '.py'
           for name in ['contracts', 'driver', 'tool_info']] + tests
snapshots = []
for relative in dict.fromkeys(sources):
    raw = (ROOT / relative).read_bytes()
    destination = check / 'source_snapshot' / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    snapshots.append({'path': relative, 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)})
(check / 'source_snapshot.json').write_text(json.dumps(snapshots, indent=2)+'\n')
(check / 'selection.json').write_text(json.dumps({'command': command, 'policy': policy.to_dict(),
    'evidence': 'synthetic_contract_and_file_writing_process_only_no_database_BLAST'}, indent=2)+'\n')
try:
    result = run_local_job(command, cwd=check, policy=policy, stdout_path=check/'stdout.txt',
        stderr_path=check/'stderr.txt', env=env)
except Exception as error:
    (check/'failure.json').write_text(json.dumps({'type': type(error).__name__, 'detail': str(error)}, indent=2)+'\n')
    raise
receipt = {'returncode': result.returncode, 'stdout_path': str(result.stdout_path),
    'stderr_path': str(result.stderr_path), 'metadata': result.metadata}
(check/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({'directory': str(check), 'returncode': result.returncode}))
print(result.stdout_path.read_text())
print(result.stderr_path.read_text())
raise SystemExit(result.returncode)
