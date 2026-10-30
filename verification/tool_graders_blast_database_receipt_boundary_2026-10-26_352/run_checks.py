"""Selected checks with recorded local-job limits and source versions."""
from pathlib import Path
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

out = Path(__file__).resolve().parent / sys.argv[1]
out.mkdir(exist_ok=False)
paths = [ROOT / 'gene_annotation_episode' / name for name in (
    'episode_receipts.py', 'native_blast_database_returns.py', 'native_blast_database_results.py',
    'native_blast_database_result_publication.py', 'native_blast_database_result_worker.py',
    'execution_episodes.py', 'episode_services.py', 'blast_vdb_function_inputs.py')]
paths += [ROOT / 'tests' / name for name in ('test_native_blast_database_receipt_boundary.py',
    'test_native_blast_database_episode_binding.py', 'test_native_blast_vdb_function_integration.py')]

def pin():
    return [dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]

before = pin()
for p in paths:
    copy = out / 'source' / p.relative_to(ROOT)
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_bytes(p.read_bytes())
(out / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n')
command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp', str(out / 'temporary'), *sys.argv[2:]]
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
env = dict(os.environ, PYTHONPATH=str(ROOT) + os.pathsep + str(ROOT / 'tests'), PYTHONDONTWRITEBYTECODE='1')
(out / 'request.json').write_text(json.dumps(dict(command=command, policy=policy.to_dict(),
    scientific_inputs='synthetic fixtures; no live BLAST/database/API/HPC execution'), indent=2) + '\n')
result = run_local_job(command, cwd=out, policy=policy, stdout_path=out/'stdout.txt',
    stderr_path=out/'stderr.txt', env=env)
(out/'receipt.json').write_text(json.dumps(dict(returncode=result.returncode, metadata=result.metadata), indent=2) + '\n')
after = pin()
(out/'source-after.json').write_text(json.dumps(after, indent=2) + '\n')
print(json.dumps(dict(returncode=result.returncode, sources_unchanged=before == after)))
print((out/'stdout.txt').read_text()[-10000:])
raise SystemExit(result.returncode)
