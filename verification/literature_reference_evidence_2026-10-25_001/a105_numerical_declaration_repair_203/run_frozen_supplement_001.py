from pathlib import Path
import hashlib,json,os,sys,time
base=Path(__file__).resolve().parent;pin=base/'pin_002';root=base.parents[2]
sys.dont_write_bytecode=True;sys.path=[str(pin),str(pin/'tests'),*[p for p in sys.path if Path(p or os.getcwd()).resolve() not in (root,root/'tests')]];os.chdir(pin)
import pytest
files=['tests/test_literature_prompt_surface_144.py::test_fresh_source_only_caller_retains_exact_bytes_configuration_and_source_assignment_without_model','tests/test_literature_prompt_surface_144.py::test_source_only_owned_model_bootstrap_preserves_default_science_and_declared_failure','tests/test_literature_controlled_response_communication.py::test_actual_registered_sheet_reference_and_native_number_validation','tests/test_literature_controlled_response_communication.py::test_actual_joint_scope_witness_reference_behind_native_definition']
manifest=json.loads((base/'FINAL_PIN_002.json').read_text())['hashes']
def changed():return [p for p,h in manifest.items() if hashlib.sha256((pin/p).read_bytes()).hexdigest()!=h]
assert not changed();start=time.time()
code=pytest.main(['-c',str(pin/'pytest.ini'),'--rootdir',str(pin),'-q',*files,'--basetemp',str(base/'final_supplement_temporary'),'-o','cache_dir='+str(base/'final_supplement_cache'),'--junitxml',str(base/'FINAL_REGRESSION_SUPPLEMENT_TESTS_001.xml')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items() if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_','literature_','caller_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(pin)}
record={'scope':'Only5missing-asset controlled regression cases; package and original test bytes identical to pin001.','exit_code':int(code),'started_at':start,'ended_at':time.time(),'files':files,'imports':imports,'imports_outside_pin':outside,'changed_pinned_files':changed(),'unbound205_imports':[n for n in imports if 'measurement_validation' in n]}
(base/'FINAL_REGRESSION_SUPPLEMENT_PROVENANCE_001.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k not in ('files','imports')},indent=2));raise SystemExit(int(code) or bool(outside or record['changed_pinned_files'] or record['unbound205_imports']))
