"""Freeze the accepted pure tree plus the exclusively owned binding increment."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent/'a105_common_assessment_design_221'
PIN = HERE/'pin_002'
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = json.loads((BASE/'PIN_002.json').read_text())
owned = list(json.loads((HERE/'BASELINE_001.json').read_text())['owned_existing_files'])
owned.append('tests/test_literature_common_assessment_binding_223.py')
PIN.mkdir(exist_ok=False)
hashes = {}
for entry in source['files']:
    name = entry['path']
    assert Path(name).name != 'GOAL.md'
    original = BASE/'pin_002'/name
    assert digest(original) == entry['sha256'], name
    target = PIN/name; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original, target); hashes[name] = entry['sha256']
overlay = {}
for name in owned:
    original = ROOT/name; before = digest(original)
    target = PIN/name; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original, target)
    assert before == digest(original) == digest(target), name
    hashes[name] = overlay[name] = before
for name in ['OLD_STATE_BASELINE_001.json']:
    relative = str((HERE/name).relative_to(ROOT)); target = PIN/relative
    target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(HERE/name, target)
    hashes[relative] = digest(target)
(PIN/'pytest.ini').write_text('[pytest]\npythonpath = . tests\ntestpaths = tests\n')
hashes['pytest.ini'] = digest(PIN/'pytest.ini')
for name, sha in json.loads((HERE/'BASELINE_001.json').read_text())['protected_files'].items():
    assert digest(ROOT/name) == sha, ('protected live dependency changed', name)
for name in ('literature_compiled_assay_inputs.py', 'literature_compiled_assay_calculations.py'):
    assert digest(ROOT/'gene_annotation_episode'/name) == digest(PIN/'gene_annotation_episode'/name)
manifest = {'scope': '223 selected common compiler binding on accepted221pure; controlled fixtures only.',
    'base': str(BASE/'PIN_002.json'), 'hashes': hashes, 'owned_code_hashes': overlay,
    'actual_model_execution': False, 'a105_adequacy_claim': False,
    'external_closed_fixture': 'OLD_STATE_BASELINE_001.json identifies original controlled root220data states; no outside code imports.'}
with (HERE/'PIN_002.json').open('x') as f:
    json.dump(manifest, f, indent=2, sort_keys=True)
runner = '''from pathlib import Path
import hashlib,json,os,sys,time
HERE=Path(__file__).resolve().parent
PIN=HERE/'pin_002'
sys.dont_write_bytecode=True
sys.path[:0]=[str(PIN),str(PIN/'tests')]
os.chdir(PIN)
import pytest
args=['-c',str(PIN/'pytest.ini'),'-q','-p','no:cacheprovider','--tb=short',
    '--basetemp='+str(HERE/'pytest_002'),'--junitxml='+str(HERE/'FROZEN_TESTS_002.xml'),
    'tests/test_literature_common_assessment_binding_223.py',
    'tests/test_literature_common_assessment_221.py',
    'tests/test_literature_compiled_assay_185.py',
    'tests/test_literature_compiled_assay_binding_185.py',
    'tests/test_literature_compiled_assay_uncertainty_215.py',
    'tests/test_literature_product_coupling_binding_218.py',
    'tests/test_literature_numerical_declarations_203.py',
    'tests/test_literature_measurement_validation_binding_209.py',
    'tests/test_literature_product_coupling_212.py']
started=time.time();code=pytest.main(args)
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_','tests.test_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
hashes=json.loads((HERE/'PIN_002.json').read_text())['hashes']
changed=[n for n,h in hashes.items() if hashlib.sha256((PIN/n).read_bytes()).hexdigest()!=h]
result={'exit_code':code,'elapsed_seconds':time.time()-started,'arguments':args,'imports':imports,
    'imports_outside_pin':outside,'changed_pinned_files':changed,
    'scope':'Controlled selected shared-loop/form/cold paths and scientific pure regressions; no actual model or A105 adequacy claim.'}
with (HERE/'FROZEN_RESULT_002.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
assert not outside and not changed
raise SystemExit(code)
'''
with (HERE/'run_frozen_002.py').open('x') as f:
    f.write(runner)
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(PIN)+os.pathsep+str(PIN/'tests'))
with (HERE/'FROZEN_TEST_RUN_002.log').open('x') as log:
    result = subprocess.run([sys.executable, str(HERE/'run_frozen_002.py')], cwd=PIN, env=env,
        stdout=log, stderr=subprocess.STDOUT)
print(json.dumps({'exit_code': result.returncode, 'log': str(HERE/'FROZEN_TEST_RUN_002.log')}))
raise SystemExit(result.returncode)
