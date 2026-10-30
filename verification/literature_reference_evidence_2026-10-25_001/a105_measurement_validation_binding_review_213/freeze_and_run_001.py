"""Root independent selected-operation/typed-return verification of209."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time

ROOT=Path('/home/chia/repos/gene_annotation_episode')
BASE=Path(__file__).resolve().parent
OWNER=BASE.parent/'a105_measurement_validation_binding_209'
PIN=BASE/'pin_001'
original=json.loads((OWNER/'FINAL_PIN_001.json').read_text())
assert not PIN.exists()
for relative,digest in original['hashes'].items():
    assert Path(relative).name!='GOAL.md'
    source=OWNER/'pin_001'/relative
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest,relative
    target=PIN/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
(BASE/'PIN_001.json').write_text(json.dumps(original,indent=2)+'\n')
sys.dont_write_bytecode=True
sys.path=[str(PIN),str(PIN/'tests'),*[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT,ROOT/'tests')]]
os.chdir(PIN)
import pytest
started=time.time()
files=['tests/test_literature_measurement_validation_binding_209.py',
    'tests/test_literature_numerical_declarations_203.py::test_catalog_matches_actual_bound_complete_host_type_and_preserves_interpretations',
    'tests/test_literature_numerical_declarations_203.py::test_actual_standard_c1_worker_reopens_legacy_alias_original_request_without_model_work',
    'tests/test_literature_numerical_declarations_203.py::test_pending_legacy_decision_uses_original_snapshot_before_current_fact_or_catalog_factories',
    'tests/test_literature_numerical_declarations_203.py::test_mixed_native_literal_and_alias_expand_and_saved_validate_without_changing_either',
    'tests/test_literature_numerical_declarations_203.py::test_native_literal_opacity_rejects_altered_schema_labels_and_nested_aliases']
code=pytest.main(['-c',str(PIN/'pytest.ini'),'--rootdir',str(PIN),'-q',*files,
    '--basetemp',str(BASE/'temporary_001'),'-o','cache_dir='+str(BASE/'cache_001'),
    '--junitxml',str(BASE/'ROOT_TESTS_001.xml')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
changed=[p for p,h in original['hashes'].items() if hashlib.sha256((PIN/p).read_bytes()).hexdigest()!=h]
record={'exit_code':int(code),'elapsed_seconds':time.time()-started,'files':files,'imports':imports,
    'imports_outside_pin':outside,'changed_pinned_files':changed,
    'unbound212_imports':[n for n in imports if 'product_coupling' in n],
    'scope':'Controlled original-source selected operations/typed delivery/cold reconstruction and exact declaration regressions. No actual model-backed science, new product-coupling verification or A105 adequacy claim.'}
(BASE/'ROOT_RESULT_001.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in ('imports','files')},indent=2))
raise SystemExit(int(code) or bool(outside or changed or record['unbound212_imports']))
