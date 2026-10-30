from pathlib import Path
import sys,json,time,hashlib
OUT=Path(__file__).resolve().parent
PIN=OUT/'pin_001'
sys.dont_write_bytecode=True
sys.path[:0]=[str(PIN),str(PIN/'tests')]
import pytest
start=time.monotonic()
selection=['tests/test_literature_missing_input_semantics_177.py', 'tests/test_literature_transport_inputs.py::test_selected_concentrations_and_authoritative_km_supply_common_curve_calculator', 'tests/test_literature_transport_inputs.py::test_different_system_blocks_response_but_preserves_supported_native_and_single_arm_cells', 'tests/test_literature_transport_integration.py::test_selected_transport_response_actual_typed_delivery_and_observation_accounting[False]']
code=pytest.main(['-q',*selection,'--junitxml='+str(OUT/'ROOT_001.xml'),'--basetemp='+str(OUT/'run_001'))])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items() if getattr(m,'__file__',None) and (n.startswith('gene_annotation_episode') or n.startswith('method_loop') or n.startswith('test_literature'))}
original=json.loads((OUT/'PIN_001.json').read_text())
changed=[p for p,h in original.items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
result={'exit_code':code,'elapsed_seconds':time.monotonic()-start,'selection':selection,'changed_pinned_files':changed,'imports_outside_pin':{n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)},'imports':len(imports),'scope':'Prospective input semantics, exact authentic v1 read-only saved projections, unchanged numerical controls and repaired synthetic regression paths. Existing primary-fixture assertion not rerun. No full frozen runtime factory or A105 adequacy claim.'}
(OUT/'ROOT_RESULT_001.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'ROOT_IMPORTS_001.json').write_text(json.dumps(imports,indent=2)+'\n')
raise SystemExit(code or bool(changed) or bool(result['imports_outside_pin']))
