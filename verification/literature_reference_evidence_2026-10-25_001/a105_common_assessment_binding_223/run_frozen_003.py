from pathlib import Path
import hashlib,json,os,sys,time
HERE=Path(__file__).resolve().parent
PIN=HERE/'pin_003'
sys.dont_write_bytecode=True
sys.path[:0]=[str(PIN),str(PIN/'tests')]
os.chdir(PIN)
import pytest
args=['-c',str(PIN/'pytest.ini'),'-q','-p','no:cacheprovider','--tb=short',
    '--basetemp='+str(HERE/'pytest_003'),'--junitxml='+str(HERE/'FROZEN_TESTS_003.xml'),
    'tests/test_literature_common_assessment_binding_223.py',
    'tests/test_literature_common_assessment_221.py',
    'tests/test_literature_compiled_assay_185.py',
    'tests/test_literature_compiled_assay_binding_185.py',
    'tests/test_literature_compiled_assay_uncertainty_215.py',
    'tests/test_literature_product_coupling_binding_218.py',
    'tests/test_literature_numerical_declarations_203.py',
    'tests/test_literature_measurement_validation_binding_209.py',
    'tests/test_literature_product_coupling_212.py']
started=time.time();code=pytest.main(args)
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_','tests.test_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
hashes=json.loads((HERE/'PIN_003.json').read_text())['hashes']
changed=[n for n,h in hashes.items() if hashlib.sha256((PIN/n).read_bytes()).hexdigest()!=h]
result={'exit_code':code,'elapsed_seconds':time.time()-started,'arguments':args,'imports':imports,
    'imports_outside_pin':outside,'changed_pinned_files':changed,
    'scope':'Controlled selected shared-loop/form/cold paths and scientific pure regressions; no actual model or A105 adequacy claim.'}
with (HERE/'FROZEN_RESULT_003.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
assert not outside and not changed
raise SystemExit(code)
