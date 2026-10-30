from pathlib import Path
import os,sys,json,time,hashlib
OUT=Path(__file__).resolve().parent;PIN=OUT/'pin_002'
sys.dont_write_bytecode=True;sys.path[:0]=[str(PIN),str(PIN/'tests')];os.chdir(PIN)
import pytest
selection=['tests/test_literature_ion_discrimination_components_194.py::test_full_task_matches_root_printed_proposal_and_schema_formulas_are_closed']
start=time.monotonic()
code=pytest.main(['-q','-p','no:cacheprovider','--rootdir='+str(PIN),*[str(PIN/p) for p in selection],'--junitxml='+str(OUT/'ROOT_002.xml'),'--basetemp='+str(OUT/'run_002')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items() if getattr(m,'__file__',None) and (n.startswith('gene_annotation_episode') or n.startswith('method_loop') or n.startswith('test_'))}
original=json.loads((OUT/'PIN_002.json').read_text());changed=[p for p,h in original.items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
r={'pytest_exit_code':int(code),'elapsed_seconds':time.monotonic()-start,'selection':selection,'import_count':len(imports),'imports_outside_pin':{n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)},'changed_pinned_files':changed,'scope':'Independent frozen194 pure numerical/source reader regression; no storage, episode binding, new model science or complete A105 scoring claim.'}
for name,value in [('ROOT_RESULT_002.json',r),('ROOT_IMPORTS_002.json',imports)]:
 with (OUT/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
raise SystemExit(int(code) or bool(changed) or bool(r['imports_outside_pin']))
