"""Run selected pinned tests and retain actual import/terminal result custody."""
from pathlib import Path
import contextlib
import hashlib
import json
import os
import sys
import time

OWN=Path(__file__).resolve().parent
PIN=OWN/'pin_001'
label=sys.argv[1]
targets=sys.argv[2:]
assert targets and label.replace('_','').isalnum()
os.chdir(PIN)
sys.path.insert(0,str(PIN));sys.path.insert(0,str(PIN/'tests'))
import pytest
started=time.monotonic()
with (OWN/(label+'.log')).open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
    code=pytest.main(['-q','--tb=short','-o','cache_dir='+str(OWN/(label+'_cache')),
        '--basetemp='+str(OWN/(label+'_state')),'--junitxml='+str(OWN/(label+'.xml')),*targets])
imports={}
for module in list(sys.modules.values()):
    filename=getattr(module,'__file__',None)
    if not filename:continue
    path=Path(filename).resolve()
    if path.is_relative_to(PIN) and path.is_file():
        imports[str(path.relative_to(PIN))]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    elif path.is_relative_to(OWN.parents[2]) and path.suffix=='.py':
        raise AssertionError('Local import escaped immutable pin: '+str(path))
manifest=json.loads((OWN/'PIN_001.json').read_text())
assert all(hashlib.sha256((PIN/relative).read_bytes()).hexdigest()==digest for relative,digest in manifest['hashes'].items())
result={'status':'terminal','exit_code':int(code),'seconds':time.monotonic()-started,'targets':targets,
    'pin_manifest_sha256':hashlib.sha256((OWN/'PIN_001.json').read_bytes()).hexdigest(),
    'all_pinned_input_hashes_unchanged':True,'actual_local_imports':imports,
    'actual_model_execution':False,'private_provider_data_read':False}
(OWN/(label+'_RESULT.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'exit_code':int(code),'seconds':result['seconds'],'local_imports':len(imports),'log':str(OWN/(label+'.log'))}))
raise SystemExit(code)
