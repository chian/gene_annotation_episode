"""Run W1 through local_jobs; preserve exact source versions and native receipts."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

output = Path(__file__).parent / sys.argv[1]
output.mkdir()
tests = ['tests/test_native_hmmer_preparation_workflow.py',
         'tests/test_native_hmmer_preparation_nested_workflow.py']
paths = [*sorted((ROOT / 'gene_annotation_episode').glob('*.py')),
         *[ROOT / name for name in tests if (ROOT / name).exists()]]
def hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
before = hashes()
requested = [str(ROOT / value) if value.startswith('tests/') else value
             for value in (sys.argv[2:] or tests)]
command = [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
           *requested, '--basetemp=' + str(output / 'temporary'), '--junitxml=' + str(output / 'junit.xml')]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
(output / 'intent.json').write_text(json.dumps({'command': command, 'policy': policy.to_dict(),
    'source_hashes': before}, indent=2) + '\n')
result = run_local_job(command, cwd=output, policy=policy,
    env={'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1'})
after = hashes()
changed = [name for name in before if before[name] != after[name]]
(output / 'receipt.json').write_text(json.dumps({'returncode': result.returncode,
    'metadata': result.metadata, 'stdout_path': str(result.stdout_path), 'stderr_path': str(result.stderr_path),
    'source_hashes_before': before, 'source_hashes_after': after,
    'sources_unchanged': not changed, 'changed_sources': changed}, indent=2) + '\n')
(output / 'stdout.log').write_bytes(result.stdout_path.read_bytes())
(output / 'stderr.log').write_bytes(result.stderr_path.read_bytes())
print(json.dumps({'directory': str(output), 'returncode': result.returncode, 'changed_sources': changed,
    'stdout_tail': result.stdout_path.read_text()[-12000:], 'stderr_tail': result.stderr_path.read_text()[-1500:]}))
raise SystemExit(result.returncode)
