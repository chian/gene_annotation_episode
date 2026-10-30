"""Pin an exact consistent221snapshot and independently run its pure checks."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time

ROOT=Path('/home/chia/repos/gene_annotation_episode')
HERE=Path(__file__).resolve().parent
OWNER=HERE
PIN=HERE/'pin_002'
assert not PIN.exists()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
original=json.loads((HERE/'PIN_001.json').read_text())
hashes={}
for relative,expected in original['hashes'].items():
    assert Path(relative).name!='GOAL.md'
    source=HERE/'pin_001'/relative
    assert sha(source)==expected,relative
    target=PIN/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    hashes[relative]=expected
relative='verification/literature_reference_evidence_2026-10-25_001/a105_identified_product_scoring_case_207/acquisition_001.bin'
source=ROOT/relative
expected='fe5ba79bc3152f6d94f730cc7e02b43c041fbcb5092afa434386ba3c60c2e7de'
assert sha(source)==expected
shutil.copy2(source,PIN/relative)
hashes[relative]=expected
manifest={'hashes':hashes,'overlay_sha256':original['overlay_sha256'],'base':'root224pin001',
          'scope':'Exact prior root snapshot plus missing byte-identical207acquisition fixture; no code changes.',
          'created_unix':time.time()}
with (HERE/'PIN_002.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
sys.dont_write_bytecode=True
sys.path=[str(PIN),str(PIN/'tests'),*[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT,ROOT/'tests')]]
os.chdir(PIN)
import pytest
start=time.time()
code=pytest.main(['-c',str(PIN/'pytest.ini'),'--rootdir',str(PIN),'-q',
    'tests/test_literature_common_assessment_221.py',
    '--basetemp',str(HERE/'temporary_002'),'-p','no:cacheprovider',
    '--junitxml',str(HERE/'ROOT_TESTS_002.xml')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
changed=[p for p,h in hashes.items() if sha(PIN/p)!=h]
result={'exit_code':int(code),'elapsed_seconds':time.time()-start,
    'imports':imports,'imports_outside_pin':outside,'changed_pinned_files':changed,
    'scope':'Retained-source and explicitly synthetic pure common221engineering checks. No selected common binding, actual model, or A105 adequacy claim.'}
with (HERE/'ROOT_RESULT_002.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='imports'},indent=2))
raise SystemExit(int(code) or bool(outside or changed))
