"""Run affected consumers using the joined immutable pin, record import custody."""
from pathlib import Path
import hashlib,json,os,sys,time
OWN=Path(__file__).resolve().parent
PIN=OWN/'pin_002';manifest=json.loads((OWN/'PIN_002.json').read_text())
def verify():
 for relative,expected in manifest['hashes'].items():assert hashlib.sha256((PIN/relative).read_bytes()).hexdigest()==expected,relative
 for name,expected in manifest['external_original_state_dependencies'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected,name
verify();os.chdir(PIN)
LIVE=OWN.parents[2]
sys.path[:]=[str(PIN),str(PIN/'tests'),*[v for v in sys.path if v and Path(v).resolve() not in (LIVE,LIVE/'tests',OWN)]]
import pytest
suite=['tests/test_literature_reported_curve_binding_231.py::test_each_public_selector_scope_keeps_order_and_only_named_coordinate_context']
start=time.time()
result=pytest.main(['-q',*suite,'--basetemp',str(OWN/'final_run_003'),'-o','cache_dir='+str(OWN/'pytest_cache_003'),
 '--junitxml',str(OWN/'FINAL_JUNIT_003.xml')])
imports={}
for name,module in list(sys.modules.items()):
 if name=='gene_annotation_episode' or name.startswith(('gene_annotation_episode.','method_loop.')):
  path=getattr(module,'__file__',None)
  if path:
   p=Path(path).resolve();relative=str(p.relative_to(PIN));assert relative in manifest['hashes'],relative
   imports[name]={'path':relative,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
verify()
record={'exit_code':int(result),'elapsed_seconds':time.time()-start,'selected_test_modules':suite,
 'imports':imports,'all_traced_imports_inside_pin':True,'all_pinned_and_external_original_files_unchanged':True,
 'actual_model_execution':False,'A105_complete':False,'full_goal_complete':False}
(OWN/'FINAL_RESULT_003.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='imports'}));sys.exit(int(result))
