"""Independent frozen218 selected-binding checks, not model-backed science."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time

ROOT=Path('/home/chia/repos/gene_annotation_episode')
BASE=Path(__file__).resolve().parent
OWNER=ROOT/'verification/literature_reference_evidence_2026-10-25_001/a105_product_coupling_binding_218'
PIN=BASE/'pin_003'
assert not PIN.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OWNER/'PIN_002.json').read_text())
for relative,expected in manifest['hashes'].items():
    assert Path(relative).name!='GOAL.md'
    source=OWNER/'pin_002'/relative
    assert sha(source)==expected,relative
    target=PIN/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
for relative,expected in manifest['changed_code_hashes'].items():
    assert sha(PIN/relative)==expected
with (BASE/'PIN_003.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
sys.dont_write_bytecode=True
sys.path=[str(PIN),str(PIN/'tests'),*[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT,ROOT/'tests')]]
os.chdir(PIN)
import pytest
start=time.time()
code=pytest.main(['-c',str(PIN/'pytest.ini'),'--rootdir',str(PIN),'-q',
    'tests/test_literature_product_coupling_binding_218.py::test_new_policy_preserves_chemical_locant_and_constructs_withholds_attached_statistics',
    'tests/test_literature_product_coupling_binding_218.py::test_current_repository_reads_actual_markerless_pin001_rows_and_forms_readonly_without_science',
    'tests/test_literature_product_coupling_binding_218.py::test_unknown_host_projection_generation_is_rejected_after_source_authentication',
    'tests/test_literature_product_coupling_binding_218.py::test_saved_projection_is_authenticated_without_fallback_to_altered_outcome',
    'tests/test_literature_product_coupling_binding_218.py::test_recurring_task_and_scoped_text_on_all_actual_surfaces',
    'tests/test_literature_product_coupling_binding_218.py::test_broad_context_and_same_artifact_alias_mask_unrequested_measurements',
    'tests/test_literature_product_coupling_binding_218.py::test_selected_shared_loop_original_form_and_first_readonly_cold_composition',
    '--basetemp',str(BASE/'temporary_003'),'-o','cache_dir='+str(BASE/'cache_003'),
    '--junitxml',str(BASE/'ROOT_TESTS_003.xml')])
imports={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items()
    if getattr(m,'__file__',None) and n.startswith(('gene_annotation_episode','method_loop','test_'))}
outside={n:p for n,p in imports.items() if not Path(p).is_relative_to(PIN)}
changed=[p for p,h in manifest['hashes'].items() if sha(PIN/p)!=h]
result={'exit_code':int(code),'elapsed_seconds':time.time()-start,
    'imports':imports,'imports_outside_pin':outside,'changed_pinned_files':changed,
    'scope':'Original-source controlled selected product/coupling paths, pure components, existing compiler cold compatibility and exact declarations. No actual model or A105 adequacy claim.'}
with (BASE/'ROOT_RESULT_003.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='imports'},indent=2))
raise SystemExit(int(code) or bool(outside or changed))
