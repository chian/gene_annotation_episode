"""Independent frozen223 common selected-binding checks, not model-backed science."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time

ROOT=Path('/home/chia/repos/gene_annotation_episode')
BASE=Path(__file__).resolve().parent
OWNER=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_common_assessment_binding_223'
PIN=BASE/'pin_001'
assert not PIN.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OWNER/'PIN_003.json').read_text())
for relative,expected in manifest['hashes'].items():
    assert Path(relative).name!='GOAL.md'
    source=OWNER/'pin_003'/relative
    assert sha(source)==expected,relative
    target=PIN/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
with (BASE/'PIN_001.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
sys.dont_write_bytecode=True
sys.path=[str(PIN),str(PIN/'tests'),*[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT,ROOT/'tests')]]
os.chdir(PIN)
import pytest
start=time.time()
code=pytest.main(['-c',str(PIN/'pytest.ini'),'--rootdir',str(PIN),'-q',
    'tests/test_literature_common_assessment_binding_223.py',
    '--basetemp',str(BASE/'temporary_001'),'-o','cache_dir='+str(BASE/'cache_001'),
    '--junitxml',str(BASE/'ROOT_TESTS_001.xml')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
changed=[p for p,h in manifest['hashes'].items() if sha(PIN/p)!=h]
result={'exit_code':int(code),'elapsed_seconds':time.time()-start,
    'imports':imports,'imports_outside_pin':outside,'changed_pinned_files':changed,
    'scope':'Independent exact223selected common binding tests, controlled providers, actual source/old closed fixtures; no configured-model/A105adequacy or externalMinHashbehaviorclaim.'}
with (BASE/'ROOT_RESULT_001.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='imports'},indent=2))
raise SystemExit(int(code) or bool(outside or changed))
