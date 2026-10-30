"""Operator-only verification: fixed 20 GiB RAM, 4 GiB scratch, no wall cap."""
import hashlib
import json
from pathlib import Path
import sys
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
repo = Path(__file__).resolve().parents[2]
directory = Path(__file__).resolve().parent / sys.argv[1]
directory.mkdir()
temporary = directory / 'temporary'
temporary.mkdir()
paths = [repo / 'gene_annotation_episode' / name for name in (
 'rfam_batch_alignment.py', 'rfam_batch_report_contracts.py', 'rfam_batch_report.py',
 'rfam_batch_report_grader.py', 'rfam_batch_report_views.py')]
paths += list((repo / 'tests').glob('test_rfam_batch_report*.py'))
paths += [repo / 'tests/test_rfam_batch_alignment.py']
paths += [Path(__file__)]
def hashes():
 return {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
command = [str(repo / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
 '--basetemp=' + str(temporary / 'pytest'), '--junitxml=' + str(directory / 'tests.xml'),
 *[str(repo / name) if not name.startswith('-') else name for name in sys.argv[2:]]]
if sys.argv[2] == '--script':
 script = repo / sys.argv[3]
 paths.append(script)
 command = [str(repo / '.venv/bin/python'), str(script), str(directory)]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
environment = {'PYTHONPATH': str(repo), 'PYTHONDONTWRITEBYTECODE': '1',
 'TMPDIR': str(temporary), 'TMP': str(temporary), 'TEMP': str(temporary), 'XDG_CACHE_HOME': str(directory / 'cache')}
before = hashes()
result = run_local_job(command, cwd=directory, policy=policy, env=environment)
receipt = {'command': command, 'policy': policy.to_dict(), 'environment': environment,
 'returncode': result.returncode, 'stdout_path': str(result.stdout_path), 'stderr_path': str(result.stderr_path),
 'metadata': result.metadata, 'source_sha256_before': before, 'source_sha256_after': hashes()}
(directory / 'verification-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(result.stdout_path.read_text())
if result.stderr_path.stat().st_size: print(result.stderr_path.read_text(), file=sys.stderr)
print(json.dumps({'returncode': result.returncode, 'receipt': str(directory / 'verification-receipt.json')}))
raise SystemExit(result.returncode)
