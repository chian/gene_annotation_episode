"""Freeze actual runtime, selected constructed tests/contracts, then test the pin."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PIN = HERE / 'coherent_pin_014'
PREVIOUS = HERE / 'coherent_pin_009'
TESTS = [
    'test_literature_ratio_source_inputs.py',
    'test_literature_ratio_source_calculations.py',
    'test_literature_ratio_source_validation.py',
    'test_literature_ratio_source_storage.py',
    'test_literature_ratio_source_readonly.py',
    'test_literature_ratio_source_runtime_receipt.py',
    'test_literature_experimental_prompt_delivery.py',
    'test_literature_reference_parent_prompt.py',
    'test_literature_ratio_source_episode_integration.py',
    'test_literature_ratio_source_prompt_delivery.py',
    'test_literature_ratio_source_connected_readonly.py',
]
assert not PIN.exists(), 'Immutable generation already exists'
PIN.mkdir()
for package in ('gene_annotation_episode', 'method_loop'):
    shutil.copytree(PREVIOUS/package, PIN/package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
(PIN/'tests').mkdir()
for name in TESTS + ['test_runtime.py', 'literature_ratio_source_worker_fixture_077.py', 'test_scientific_process_prompt_delivery.py']:
    source = PREVIOUS/'tests'/name
    if not source.exists(): source = ROOT/'tests'/name
    shutil.copy2(source, PIN/'tests'/name)
shutil.copy2(PREVIOUS/'pyproject.toml', PIN/'pyproject.toml')
base = Path('verification/literature_reference_evidence_2026-10-25_001')
contracts = list((ROOT/base/'a105_visual_signal_reader_070/normative').glob('*SCHEMA_008.json'))
contracts += list((ROOT/base/'visual_signal_parent_review_067/text_locator_declarations_008').glob('*SCHEMA_008.json'))
contracts += [ROOT/base/'a105_ratio_episode_integration_077/BASELINE_DEFAULT_CONTRACTS_001.json']
for source in contracts:
    target = PIN/source.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
audit = '''import atexit,hashlib,json,os,sys
from pathlib import Path
pin=Path(__file__).resolve().parent
def record():
 rows=[];bad=[]
 for name,module in tuple(sys.modules.items()):
  if not (name.startswith(('gene_annotation_episode','method_loop')) or name.startswith('test_') or name=='literature_ratio_source_worker_fixture_077'):continue
  source=getattr(module,'__file__',None)
  if not source:continue
  path=Path(source).resolve()
  if not path.is_relative_to(pin):bad.append(str(path))
  rows.append({'module':name,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 target=Path(os.environ['SOURCE077_IMPORT_AUDIT']);target.mkdir(parents=True,exist_ok=True)
 (target/(str(os.getpid())+'.json')).write_text(json.dumps({'pid':os.getpid(),'argv':sys.argv,'pin':str(pin),'outside_pin':bad,'imports':rows},indent=2))
atexit.register(record)
'''
(PIN/'sitecustomize.py').write_text(audit)
def manifest():
    return [{'path':str(p.relative_to(PIN)), 'bytes':p.stat().st_size,
        'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(PIN.rglob('*')) if p.is_file()]
before=manifest()
(HERE/'PIN_MANIFEST_BEFORE_014.json').write_text(json.dumps(before,indent=2))
environment={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
    'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
    'source_root':str(ROOT),'predecessor_pin':str(PREVIOUS),'only_extra_test_dependency':'test_scientific_process_prompt_delivery.py','pin':str(PIN),'tests':TESTS,
    'command':['-m','pytest',*['tests/'+n for n in TESTS],'-q','-p','no:cacheprovider','--basetemp='+str(HERE/'tmp_pinned_014')]}
(HERE/'ENVIRONMENT_014.json').write_text(json.dumps(environment,indent=2))
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':os.pathsep.join((str(PIN),str(PIN/'tests'))),
    'SOURCE077_IMPORT_AUDIT':str(HERE/'import_audit_014')}
with (HERE/'pytest_pinned_014.log').open('w') as log:
    process=subprocess.run([sys.executable,*environment['command']],cwd=PIN,env=env,stdout=log,stderr=subprocess.STDOUT)
after=manifest()
(HERE/'PIN_MANIFEST_AFTER_014.json').write_text(json.dumps(after,indent=2))
assert before==after, 'Frozen code changed during proof'
audits=[json.loads(p.read_text()) for p in (HERE/'import_audit_014').glob('*.json')]
assert audits and not any(a['outside_pin'] for a in audits)
(HERE/'PIN_RUN_RECEIPT_014.json').write_text(json.dumps({'exit_code':process.returncode,
    'code_unchanged':True,'audit_process_count':len(audits),'all_recorded_project_imports_inside_pin':True,
    'files':len(before)},indent=2))
sys.exit(process.returncode)
