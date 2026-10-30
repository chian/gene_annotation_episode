"""Bounded metadata-boundary tests; adapted from workload 247's runner."""
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
destination = HERE / sys.argv[1]
destination.mkdir()
temporary = destination / 'temporary'
temporary.mkdir()
test = ROOT / 'tests/test_native_infernal_preparation_reference_visibility.py'
sources = [test, Path(__file__).resolve(), *sorted((ROOT / 'gene_annotation_episode').glob('*.py')),
    *sorted((ROOT / 'method_loop').rglob('*.py'))]


def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}


before = hashes()
command = [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp=' + str(temporary / 'pytest'), '--junitxml=' + str(destination / 'tests.xml'),
    str(test), *sys.argv[2:]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
environment = {'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(temporary),
    'TMP': str(temporary), 'TEMP': str(temporary), 'XDG_CACHE_HOME': str(destination / 'cache')}
intent = {'command': command, 'policy': policy.to_dict(), 'environment': environment,
    'source_hashes_before': before,
    'fixture_scope': 'Synthetic metadata/actions/forms; real Store/receipts/resolvers. No native/grade/network execution.'}
(destination / 'intent.json').write_text(json.dumps(intent, indent=2, sort_keys=True) + '\n')
result = run_local_job(command, cwd=destination, policy=policy, env=environment)
after = hashes()
receipt = {**intent, 'source_hashes_after': after,
    'changed_files': [name for name in before if before[name] != after.get(name)],
    'returncode': result.returncode, 'stdout_path': str(result.stdout_path),
    'stderr_path': str(result.stderr_path), 'metadata': result.metadata}
(destination / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size:
    print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({'returncode': result.returncode, 'receipt': str(destination / 'receipt.json')}))
raise SystemExit(result.returncode)
