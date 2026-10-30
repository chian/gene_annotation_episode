"""Run one independently warranted probe under the user resource contract."""
from pathlib import Path
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

OWN = Path(__file__).resolve().parent
OUT = OWN / 'probe001'
OUT.mkdir(exist_ok=False)
paths = [ROOT / line.split('  ', 1)[1] for line in (OWN / 'SOURCE_PINS_001.sha256').read_text().splitlines()]
paths += [ROOT / 'gene_annotation_episode/native_blast_database_acquisition.py']
pins = lambda: [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
before = pins()
(OUT / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n')
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
cmd = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
       '--basetemp', str(OUT / 'temporary'), str(OWN / 'test_source_only_artifact_authority.py')]
env = dict(os.environ, PYTHONPATH=str(ROOT) + os.pathsep + str(ROOT / 'tests'), PYTHONDONTWRITEBYTECODE='1')
(OUT / 'request.json').write_text(json.dumps(dict(command=cmd, cwd=str(OUT), policy=policy.to_dict(),
    scientific_inputs='synthetic harness only; no native BLAST, database search, remote API/HPC or model calls'), indent=2) + '\n')
result = run_local_job(cmd, cwd=OUT, policy=policy, stdout_path=OUT / 'stdout.txt', stderr_path=OUT / 'stderr.txt', env=env)
(OUT / 'receipt.json').write_text(json.dumps(dict(returncode=result.returncode, metadata=result.metadata), indent=2) + '\n')
after = pins()
(OUT / 'source-after.json').write_text(json.dumps(after, indent=2) + '\n')
print(json.dumps(dict(returncode=result.returncode, sources_unchanged=before == after)))
print((OUT / 'stdout.txt').read_text())
raise SystemExit(result.returncode)
