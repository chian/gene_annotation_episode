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
OWNER=HERE.parent/'a105_product_coupling_binding_218'
PIN=HERE/'pin_001'
assert not PIN.exists()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
original=json.loads((OWNER/'PIN_002.json').read_text())
hashes={}
for relative,expected in original['hashes'].items():
    assert Path(relative).name!='GOAL.md'
    source=OWNER/'pin_002'/relative
    assert sha(source)==expected,relative
    target=PIN/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    hashes[relative]=expected
overlay=['gene_annotation_episode/literature_compiled_assay_inputs.py',
         'gene_annotation_episode/literature_compiled_assay_calculations.py',
         'tests/test_literature_common_assessment_221.py',
         'verification/literature_reference_evidence_2026-10-25_001/a105_common_scientific_sheet_review_219/ROOT_NUMERICAL_ORACLES_001.json']
before={name:sha(ROOT/name) for name in overlay}
for relative in overlay:
    target=PIN/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/relative,target)
    assert sha(target)==before[relative],relative
    hashes[relative]=before[relative]
assert before=={name:sha(ROOT/name) for name in overlay},'Concurrent source edit: do not run an inconsistent snapshot.'
manifest={'hashes':hashes,'overlay_sha256':before,'base':'218correctedpin002',
          'scope':'Root consistent live221snapshot, not an assertion of final221owner freeze.',
          'created_unix':time.time()}
with (HERE/'PIN_001.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
sys.dont_write_bytecode=True
sys.path=[str(PIN),str(PIN/'tests'),*[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT,ROOT/'tests')]]
os.chdir(PIN)
import pytest
start=time.time()
code=pytest.main(['-c',str(PIN/'pytest.ini'),'--rootdir',str(PIN),'-q',
    'tests/test_literature_common_assessment_221.py',
    '--basetemp',str(HERE/'temporary_001'),'-p','no:cacheprovider',
    '--junitxml',str(HERE/'ROOT_TESTS_001.xml')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
changed=[p for p,h in hashes.items() if sha(PIN/p)!=h]
result={'exit_code':int(code),'elapsed_seconds':time.time()-start,
    'imports':imports,'imports_outside_pin':outside,'changed_pinned_files':changed,
    'scope':'Retained-source and explicitly synthetic pure common221engineering checks. No selected common binding, actual model, or A105 adequacy claim.'}
with (HERE/'ROOT_RESULT_001.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='imports'},indent=2))
raise SystemExit(int(code) or bool(outside or changed))
