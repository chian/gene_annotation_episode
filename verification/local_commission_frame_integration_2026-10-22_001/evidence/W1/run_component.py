"""Guarded isolated fixture invocation; never reuses a pytest basetemp."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT=Path('/tmp/gene-annotation-configured-caller-20261022-007')
EVIDENCE=Path(__file__).parent
name,*nodes=sys.argv[1:]
assert name and nodes
out=EVIDENCE/name
out.mkdir()
source_paths=sorted([*ROOT.glob('gene_annotation_episode/**/*.py'),*ROOT.glob('method_loop/**/*.py')])
test_paths=sorted({ROOT/n.split('::')[0] for n in nodes} | {ROOT/'tests/test_local_return_history.py', ROOT/'tests/test_episode_commissions.py'})
paths=source_paths+test_paths

def guard():
    return {str(p.relative_to(ROOT)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in paths}

def pin(record):
    outer=hashlib.sha256()
    for p in source_paths:
        relative=str(p.relative_to(ROOT))
        outer.update(relative.encode()+b'\0'+bytes.fromhex(record[relative]['sha256']))
    return outer.hexdigest()

before=guard()
for relative in ['gene_annotation_episode/local_commission_frame.py','gene_annotation_episode/wait_estimation_inputs.py','gene_annotation_episode/runtime.py','gene_annotation_episode/waiting.py','tests/test_local_commission_frame.py','tests/test_local_return_evidence.py']:
    target=out/'inputs'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes((ROOT/relative).read_bytes())
argv=['/home/chia/repos/gene_annotation_episode/.venv/bin/python','-B','-m','pytest','-q',*nodes,'--basetemp',str(out/'raw-fixtures'),'--junitxml',str(out/'junit.xml')]
(out/'COMMAND.json').write_text(json.dumps({'argv':argv,'cwd':str(ROOT),'environment_overrides':{'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1'}},indent=2)+'\n')
(out/'BEFORE.json').write_text(json.dumps(before,indent=2)+'\n')
started=time.monotonic()
with (out/'stdout.log').open('wb') as stdout,(out/'stderr.log').open('wb') as stderr:
    result=subprocess.run(argv,cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT),PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr)
after=guard()
(out/'AFTER.json').write_text(json.dumps(after,indent=2)+'\n')
summary={'returncode':result.returncode,'seconds':time.monotonic()-started,'source_and_selected_test_guard_unchanged':before==after,'changed_paths':[p for p in before if before[p]!=after[p]],'runtime_files':len(source_paths),'implementation_sha256_before':pin(before),'implementation_sha256_after':pin(after)}
(out/'RESULT.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
print(out)
raise SystemExit(result.returncode)
