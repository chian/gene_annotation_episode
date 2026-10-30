"""Run the218 engineering cohort against its immutable source/test pin."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time
BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_001'
ROOT=Path('/home/chia/repos/gene_annotation_episode')
sys.dont_write_bytecode=True
sys.path=[str(PIN),str(PIN/'tests'),*[p for p in sys.path if Path(p or os.getcwd()).resolve() not in (ROOT,ROOT/'tests')]]
os.chdir(PIN)
import pytest
arguments=['-q','-p','no:cacheprovider','--tb=short',
    '--basetemp='+str(BASE/'pytest_001'), '--junitxml='+str(BASE/'FROZEN_TESTS_001.xml'),
    'tests/test_literature_product_coupling_binding_218.py',
    'tests/test_literature_product_coupling_212.py',
    'tests/test_literature_measurement_validation_205.py',
    'tests/test_literature_partner_source_fields.py',
    'tests/test_literature_measurement_validation_binding_209.py',
    'tests/test_literature_numerical_declarations_203.py',
    'tests/test_literature_compiled_assay_uncertainty_215.py',
    'tests/test_literature_compiled_assay_binding_185.py']
started=time.monotonic();code=pytest.main(arguments)
manifest=json.loads((BASE/'PIN_001.json').read_text())['hashes']
changed=[p for p,h in manifest.items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
imports={name:str(Path(module.__file__).resolve()) for name,module in sys.modules.items()
    if getattr(module,'__file__',None) and name.startswith(('gene_annotation_episode','method_loop','test_'))}
outside={name:p for name,p in imports.items() if not Path(p).is_relative_to(PIN)}
result={'exit_code':int(code),'elapsed_seconds':time.monotonic()-started,'arguments':arguments,
    'imports':imports,'imports_outside_pin':outside,'changed_pinned_files':changed,
    'scope':'Controlled fixture providers and deterministic retained-source readers; no configured-model scientific execution or A105 adequacy claim.'}
(BASE/'FROZEN_RESULT_001.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('imports','arguments')},indent=2))
raise SystemExit(int(code) or bool(changed) or bool(outside))
