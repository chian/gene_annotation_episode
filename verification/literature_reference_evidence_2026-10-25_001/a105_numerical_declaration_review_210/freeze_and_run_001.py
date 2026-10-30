"""Root independent fixed-code declaration/custody run; synthetic decisions."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time

ROOT = Path('/home/chia/repos/gene_annotation_episode')
BASE = Path(__file__).resolve().parent
OWNER = BASE.parent/'a105_numerical_declaration_repair_203'
PIN = BASE/'pin_001'
manifest = json.loads((OWNER/'FINAL_PIN_002.json').read_text())
assert not PIN.exists()
for relative,digest in manifest['hashes'].items():
    assert Path(relative).name != 'GOAL.md'
    source = OWNER/'pin_002'/relative
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, relative
    target = PIN/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
(BASE/'PIN_001.json').write_text(json.dumps(manifest,indent=2)+'\n')
sys.dont_write_bytecode = True
sys.path = [str(PIN),str(PIN/'tests'),*[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT,ROOT/'tests')]]
os.chdir(PIN)
import pytest
started=time.time()
code=pytest.main(['-c',str(PIN/'pytest.ini'),'--rootdir',str(PIN),'-q',
    'tests/test_literature_numerical_declarations_203.py',
    '--basetemp',str(BASE/'temporary_001'),'-o','cache_dir='+str(BASE/'cache_001'),
    '--junitxml',str(BASE/'ROOT_TESTS_001.xml')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
         if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
changed=[p for p,h in manifest['hashes'].items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
record={'exit_code':int(code),'elapsed_seconds':time.time()-started,'imports':imports,
    'imports_outside_pin':outside,'changed_pinned_files':changed,
    'scope':'Root independent declaration, presentation, controlled selected operation and custody tests; no actual model-backed investigation, new paper or A105 adequacy claim.'}
(BASE/'ROOT_RESULT_001.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='imports'},indent=2))
raise SystemExit(int(code) or bool(outside or changed))
