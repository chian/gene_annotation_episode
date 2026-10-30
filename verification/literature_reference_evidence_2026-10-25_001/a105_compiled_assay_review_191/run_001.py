from pathlib import Path
import os,sys,json,time,hashlib
OUT=Path(__file__).resolve().parent;PIN=OUT/'pin_001'
sys.dont_write_bytecode=True;sys.path[:0]=[str(PIN),str(PIN/'tests')];os.chdir(PIN)
import pytest
selection=['tests/test_literature_compiled_assay_185.py','tests/test_literature_compiled_assay_binding_185.py','tests/test_communication.py','tests/test_literature_experimental_prompt.py','tests/test_literature_assay_prompt.py','tests/test_literature_assay_integration.py']
os.environ['COMPILED_ASSAY_PROOF_DIR']=str(OUT/'root_joined_proof_001')
start=time.monotonic()
code=pytest.main(['-q','-p','no:cacheprovider','--rootdir='+str(PIN),*[str(PIN/name) for name in selection],'--junitxml='+str(OUT/'ROOT_001.xml'),'--basetemp='+str(OUT/'run_001')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items() if getattr(m,'__file__',None) and (n.startswith('gene_annotation_episode') or n.startswith('method_loop') or n.startswith('test_'))}
original=json.loads((OUT/'PIN_001.json').read_text());changed=[p for p,h in original.items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
result={'pytest_exit_code':int(code),'elapsed_seconds':time.monotonic()-start,'changed_pinned_files':changed,'imports_outside_pin':{n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)},'import_count':len(imports),'selection':selection,'scope':'New saved-component compilation numeric/custody/selected shared-loop/exact typed child-parent/cold original descriptor factory with science off before construction; existing communication/task/assay regressions. Controlled synthetic provider. Not original-paper combined assay, actual model science, cross-assay synthesis or A105 adequacy.'}
for name,value in [('ROOT_RESULT_001.json',result),('ROOT_IMPORTS_001.json',imports)]:
 with (OUT/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
raise SystemExit(int(code) or bool(changed) or bool(result['imports_outside_pin']))
