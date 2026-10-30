from pathlib import Path
import sys,json,time,hashlib
OUT=Path(__file__).resolve().parent; PIN=OUT/'pin_001'
sys.dont_write_bytecode=True; sys.path[:0]=[str(PIN),str(PIN/'tests')]
import pytest
start=time.monotonic()
selection=['tests/test_literature_active_site_saved_reconstruction_182.py', 'tests/test_literature_active_site_inputs.py', 'tests/test_literature_active_site_storage.py', 'tests/test_literature_active_site_integration.py']
code=pytest.main(['-q','--rootdir='+str(PIN),*[str(PIN/name) for name in selection],'--junitxml='+str(OUT/'ROOT_001.xml'),'--basetemp='+str(OUT/'run_001')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items() if getattr(m,'__file__',None) and (n.startswith('gene_annotation_episode') or n.startswith('method_loop') or n.startswith('test_literature'))}
original=json.loads((OUT/'PIN_001.json').read_text()); changed=[p for p,h in original.items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
result={'pytest_exit_code':code,'elapsed_seconds':time.monotonic()-start,'changed_pinned_files':changed,'imports_outside_pin':{n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)},'import_count':len(imports),'selection':selection,'scope':'Synthetic active-site exact authentic v1 saved reconstruction and current corrected selected shared-loop/cold-descriptor factory, with original science/parser/unitconverter/calculator/domain algebra blocked before constructor. Existing source-input/storage/integration regressions. No new primary-source read/model inference/A105 adequacy claim.'}
(OUT/'ROOT_RESULT_001.json').write_text(json.dumps(result,indent=2)+'\n'); (OUT/'ROOT_IMPORTS_001.json').write_text(json.dumps(imports,indent=2)+'\n')
raise SystemExit(code or bool(changed) or bool(result['imports_outside_pin']))
