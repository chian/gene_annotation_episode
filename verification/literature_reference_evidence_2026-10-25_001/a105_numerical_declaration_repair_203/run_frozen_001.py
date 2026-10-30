"""Run explicit controlled tests with guarded immutable import provenance."""
from pathlib import Path
import hashlib,json,os,sys,time
base=Path(__file__).resolve().parent;pin=base/'pin_001';root=base.parents[2]
sys.dont_write_bytecode=True
sys.path=[str(pin),str(pin/'tests'),*[p for p in sys.path if Path(p or os.getcwd()).resolve() not in (root,root/'tests')]]
os.chdir(pin)
import pytest
group=sys.argv[1]
files=(['tests/test_literature_numerical_declarations_203.py'] if group=='primary' else [
 'tests/test_episode_contract_information.py','tests/test_contract_information_runtime_059.py',
 'tests/test_contract_information_custody_059.py','tests/test_contract_information_worker_059.py',
 'tests/test_literature_prompt_surface_144.py','tests/test_literature_channel_binding_188.py',
 'tests/test_literature_gel_communication.py','tests/test_literature_controlled_response_communication.py',
 'tests/test_literature_ion_display_ranges_206.py'])
manifest=json.loads((base/'FINAL_PIN_001.json').read_text())['hashes']
def changed():return [p for p,h in manifest.items() if hashlib.sha256((pin/p).read_bytes()).hexdigest()!=h]
assert not changed()
started=time.time()
code=pytest.main(['-c',str(pin/'pytest.ini'),'--rootdir',str(pin),'-q',*files,
 '--basetemp',str(base/('final_'+group+'_temporary')),
 '-o','cache_dir='+str(base/('final_'+group+'_cache')),
 '--junitxml',str(base/('FINAL_'+group.upper()+'_TESTS_001.xml'))])
imports={name:str(Path(module.__file__).resolve()) for name,module in sys.modules.items()
 if getattr(module,'__file__',None) and name.startswith(('gene_annotation_episode','method_loop','test_','literature_'))}
outside={name:path for name,path in imports.items() if not Path(path).is_relative_to(pin)}
record={'scope':'Explicit controlled synthetic construction/presentation/typed-custody checks. No actual model-backed scientific execution.','group':group,'exit_code':int(code),'started_at':started,'ended_at':time.time(),'files':files,'imports':imports,'imports_outside_pin':outside,'changed_pinned_files':changed(),'unbound205_imports':[n for n in imports if 'measurement_validation' in n]}
(base/('FINAL_'+group.upper()+'_PROVENANCE_001.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in ('imports','files')},indent=2))
raise SystemExit(int(code) or bool(outside or record['changed_pinned_files'] or record['unbound205_imports']))
