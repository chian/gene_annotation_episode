"""Verify repaired frozen241 in the existing project dependency environment."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
from importlib.metadata import version

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PIN=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_endpoint_signal_components_241/implementation_005'

def verify():
    files=json.loads((PIN/'MANIFEST_003.json').read_text())['files']
    for f in files:
        raw=(PIN/f['path']).read_bytes()
        assert len(raw)==f['bytes'] and hashlib.sha256(raw).hexdigest()==f['sha256'],f['path']
    return len(files)

before=verify()
env=dict(os.environ,PYTHONPATH=str(PIN),PYTHONDONTWRITEBYTECODE='1')
command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',
    'tests/test_literature_endpoint_signal_components_241.py','--tb=short']
start=time.monotonic()
result=subprocess.run(command,cwd=PIN,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(HERE/'PROJECT_ENV_PYTEST_003.txt').write_text(result.stdout)
# Verify actual imports in the same exact selected environment, separately from
# pytest's plug-in machinery. No source or model payload is interpreted here.
sys.path.insert(0,str(PIN))
import gene_annotation_episode.literature_endpoint_signal_calculations
imports=[]
for name,module in sorted(sys.modules.items()):
    if name.startswith('gene_annotation_episode') and getattr(module,'__file__',None):
        path=Path(module.__file__).resolve();assert path.is_relative_to(PIN),str(path)
        imports.append({'module':name,'path':str(path.relative_to(PIN)),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
receipt={'status':'passed' if result.returncode==0 else 'failed','command':command,
    'cwd':str(PIN),'python':sys.executable,'exit_code':result.returncode,
    'seconds':time.monotonic()-start,'output':result.stdout,
    'packages':{n:version(n) for n in ('pytest','Pillow','jsonschema')},
    'pin_files_before':before,'pin_files_after':verify(),'actual_local_imports':imports,
    'reason_for_full_run':'Earlier frozen tests used Pillow10.2/jsonschema4.10 outside declared project ranges; test repaired pin in existing conforming project environment.',
    'no_dependencies_installed':True,'scope':'Pure frozen endpoint module, no selected/model/controller run.'}
(HERE/'ROOT_PROJECT_ENV_REVIEW_003.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ('status','output','seconds','packages')}))
raise SystemExit(result.returncode)
