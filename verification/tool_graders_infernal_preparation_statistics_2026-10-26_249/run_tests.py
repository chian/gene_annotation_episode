"""Run this workload's tests under the caller-owned local limits."""
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
directory = BASE/sys.argv[1]
directory.mkdir(parents=True,exist_ok=False)
paths = sys.argv[2:] or ['tests/test_infernal_preparation_statistics.py','tests/test_infernal_preparation_calculations.py']
command = [str(ROOT/'.venv/bin/python'),'-m','pytest','-q','-p','no:cacheprovider',*[str(ROOT/p) for p in paths]]
sources = paths+['gene_annotation_episode/infernal_preparation_statistics.py','gene_annotation_episode/infernal_preparation_calculations.py',
               'gene_annotation_episode/infernal_preparation_schema.py','gene_annotation_episode/infernal_preparation_models.py']
before = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
result = run_local_job(command,cwd=directory,policy=LocalJobPolicy(20*1024**3,4*1024**3,None),
    stdout_path=directory/'stdout.txt',stderr_path=directory/'stderr.txt',
    env={'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(directory)})
receipt = dict(command=command,returncode=result.returncode,metadata=result.metadata,
    source_sha256_before=before,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})
(directory/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print((directory/'stdout.txt').read_text())
print((directory/'stderr.txt').read_text())
sys.exit(result.returncode)
