from pathlib import Path
import os,sys,json,time,hashlib
OUT=Path(__file__).resolve().parent;PIN=OUT/'pin_001'
sys.dont_write_bytecode=True;sys.path[:0]=[str(PIN),str(PIN/'tests')];os.chdir(PIN)
import pytest
selection=['tests/test_literature_ion_discrimination_binding_199.py', 'tests/test_literature_channel_binding_188.py', 'tests/test_literature_compiled_assay_binding_185.py', 'tests/test_literature_ion_discrimination_components_194.py', 'tests/test_literature_ion_discrimination_numbers_194.py', 'tests/test_communication.py', 'tests/test_literature_kinetic_integration.py', 'tests/test_literature_kinetic_model_integration.py', 'tests/test_literature_calibration_recovery_binding_173.py', 'tests/test_literature_experimental_prompt.py']
os.environ['ION_DISCRIMINATION_PROOF_DIR']=str(OUT/'root_original_runtime_001')
start=time.monotonic()
code=pytest.main(['-q','-p','no:cacheprovider','--rootdir='+str(PIN),*[str(PIN/p) for p in selection],'--junitxml='+str(OUT/'ROOT_001.xml'),'--basetemp='+str(OUT/'run_001')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items() if getattr(m,'__file__',None) and (n.startswith('gene_annotation_episode') or n.startswith('method_loop') or n.startswith('test_'))}
original=json.loads((OUT/'PIN_001.json').read_text());changed=[p for p,h in original.items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
r={'pytest_exit_code':int(code),'elapsed_seconds':time.monotonic()-start,'selection':selection,'import_count':len(imports),'imports_outside_pin':{n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)},'changed_pinned_files':changed,'scope':'Independent frozen199 selectedion/compiledinputs/sourcecustody/scopedtypedreturns/TASK/coldfactory with unchangedpure194; affectedchannel/compiled/communication/kinetic/calibration/prompt regressions. Controlledfixtures only. No full A105 adequacy or configured-model claim.'}
for name,value in [('ROOT_RESULT_001.json',r),('ROOT_IMPORTS_001.json',imports)]:
 with (OUT/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
raise SystemExit(int(code) or bool(changed) or bool(r['imports_outside_pin']))
