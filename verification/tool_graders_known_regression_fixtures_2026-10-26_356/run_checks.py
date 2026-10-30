"""Bounded selected regression checks; no native/API work is requested."""
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
paths = [ROOT / p for p in (
    'tests/test_numeric_bounds.py', 'tests/test_execution_tool_contract_declarations.py',
    'tests/test_scoring_retirement.py', 'gene_annotation_episode/credit.py',
    'gene_annotation_episode/scientific_credit.py', 'gene_annotation_episode/evidence_geometry.py',
    'gene_annotation_episode/api_service_execution.py', 'gene_annotation_episode/api_bvbrc.py')]

def pins():
    return [dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]

before = pins()
for p in paths:
    target=out/'source'/p.relative_to(ROOT)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(p.read_bytes())
(out/'source-before.json').write_text(json.dumps(before,indent=2)+'\n')
command=[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q','-p','no:cacheprovider',
    '--basetemp',str(out/'temporary'),*sys.argv[2:]]
policy=LocalJobPolicy(20*1024**3,4*1024**3,None)
env=dict(os.environ,PYTHONPATH=str(ROOT)+os.pathsep+str(ROOT/'tests'),PYTHONDONTWRITEBYTECODE='1')
(out/'request.json').write_text(json.dumps(dict(command=command,policy=policy.to_dict(),
    scope='synthetic bound-value records and operation declarations; no native/API execution'),indent=2)+'\n')
result=run_local_job(command,cwd=out,policy=policy,stdout_path=out/'stdout.txt',stderr_path=out/'stderr.txt',env=env)
(out/'receipt.json').write_text(json.dumps(dict(returncode=result.returncode,metadata=result.metadata),indent=2)+'\n')
after=pins()
(out/'source-after.json').write_text(json.dumps(after,indent=2)+'\n')
print(json.dumps(dict(returncode=result.returncode,sources_unchanged=before==after)))
print((out/'stdout.txt').read_text()[-6000:])
raise SystemExit(result.returncode)
