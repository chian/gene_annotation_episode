from pathlib import Path
import sys,json,time,hashlib
OUT=Path(__file__).resolve().parent
PIN=OUT/'pin_002'
sys.dont_write_bytecode=True
sys.path[:0]=[str(PIN),str(PIN/'tests')]
import pytest
start=time.monotonic()
code=pytest.main(['-q','--rootdir='+str(PIN),str(PIN/'tests/test_literature_channel_components_179.py'),'--junitxml='+str(OUT/'ROOT_002.xml'),'--basetemp='+str(OUT/'run_002')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items() if getattr(m,'__file__',None) and (n.startswith('gene_annotation_episode') or n.startswith('method_loop') or n.startswith('test_literature'))}
original=json.loads((OUT/'PIN_002.json').read_text()); changed=[p for p,h in original.items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
result={'pytest_exit_code':code,'elapsed_seconds':time.monotonic()-start,'changed_pinned_files':changed,'imports_outside_pin':{n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)},'import_count':len(imports),'scope':'Synthetic electrical source reader/calculator tests, including root-found trailing-unit-after-spread defect. No episode integration, new original-source execution, actual model science or full A105 adequacy claim.'}
(OUT/'ROOT_RESULT_002.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'ROOT_IMPORTS_002.json').write_text(json.dumps(imports,indent=2)+'\n')
raise SystemExit(code or bool(changed) or bool(result['imports_outside_pin']))
