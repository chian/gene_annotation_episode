"""Retain protected test receipts; no native scientific search."""
from dataclasses import asdict
from pathlib import Path
import json
import hashlib
import os
import sys
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / sys.argv[1]
OUT.mkdir()
work = OUT / 'temporary'
work.mkdir()
paths = sorted({*ROOT.joinpath('gene_annotation_episode').glob('native_blast*database*.py'),
    *ROOT.joinpath('gene_annotation_episode').glob('blast*.py'),
    *ROOT.joinpath('tests').glob('test_native_blast*database*.py'), ROOT/'tests/test_blast_fasta_record_identity_integration.py'})
frozen = OUT/'frozen_sources'
frozen.mkdir()
before = {}
for path in paths:
    raw = path.read_bytes()
    key = str(path.relative_to(ROOT))
    before[key] = hashlib.sha256(raw).hexdigest()
    target = frozen/key
    target.parent.mkdir(exist_ok=True, parents=True)
    target.write_bytes(raw)
(OUT/'source_hashes_before.json').write_text(json.dumps(before, indent=2)+'\n')
policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '--basetemp', str(work / 'pytest'), *sys.argv[2:]]
result = run_local_job(command, cwd=OUT, policy=policy, stdout_path=OUT/'stdout.txt', stderr_path=OUT/'stderr.txt', env={**os.environ, 'PYTHONPATH': str(ROOT) + ':' + str(ROOT/'tests'), 'PYTHONDONTWRITEBYTECODE':'1'})
(OUT/'receipt.json').write_text(json.dumps(dict(command=command, cwd=str(OUT), policy=asdict(policy), returncode=result.returncode, metadata=result.metadata), indent=2) + '\n')
(OUT/'source_hashes_after.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, indent=2)+'\n')
print((OUT/'stdout.txt').read_text())
print((OUT/'stderr.txt').read_text())
raise SystemExit(result.returncode)
