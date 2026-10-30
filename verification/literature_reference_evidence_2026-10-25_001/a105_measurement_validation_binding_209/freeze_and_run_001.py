"""Freeze implementation before final controlled binding/regression checks."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time

ROOT=Path('/home/chia/repos/gene_annotation_episode')
BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_001'
assert not PIN.exists()
ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.pyc','GOAL.md')
shutil.copytree(BASE.parent/'a105_measurement_validation_review_208/pin_001',PIN,ignore=ignore)
for name in ('gene_annotation_episode','method_loop','tests'):
    shutil.copytree(ROOT/name,PIN/name,dirs_exist_ok=True,ignore=ignore)
source='research/experimental_scoring_review_2026-10-23/a105_calibration_primary_case_167/source/PMC6454709.xml'
(PIN/source).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/source,PIN/source)
assert hashlib.sha256((PIN/source).read_bytes()).hexdigest()=='86896c47556f7eeef975856dbbe2d3bab3b6143b91d1f826078e29771761b698'
hashes={str(path.relative_to(PIN)):hashlib.sha256(path.read_bytes()).hexdigest()
        for path in PIN.rglob('*') if path.is_file()}
record={'scope':'Current code/tests plus retained fixture baseline, fixed before final checks. No actual provider/model records or GOAL.md included.',
    'frozen_unix':time.time(),'hashes':hashes}
(BASE/'FINAL_PIN_001.json').write_text(json.dumps(record,indent=2)+'\n')
sys.dont_write_bytecode=True
sys.path=[str(PIN),str(PIN/'tests'),*[path for path in sys.path
          if Path(path or os.getcwd()).resolve() not in (ROOT,ROOT/'tests')]]
os.chdir(PIN)
import pytest
start=time.time()
files=['tests/test_literature_measurement_validation_binding_209.py',
       'tests/test_literature_measurement_validation_205.py',
       'tests/test_literature_calibration_recovery_169.py',
       'tests/test_literature_calibration_recovery_binding_173.py',
       'tests/test_literature_numerical_declarations_203.py::test_catalog_matches_actual_bound_complete_host_type_and_preserves_interpretations',
       'tests/test_literature_numerical_declarations_203.py::test_actual_public_return_surfaces_keep_scientific_task_interpretations_and_usable_declaration',
       'tests/test_literature_numerical_declarations_203.py::test_actual_selected_legacy_child_delivery_preserves_original_type_subset_and_observations',
       'tests/test_literature_numerical_declarations_203.py::test_pending_legacy_decision_uses_original_snapshot_before_current_fact_or_catalog_factories']
code=pytest.main(['-c',str(PIN/'pytest.ini'),'--rootdir',str(PIN),'-q',*files,
    '--basetemp',str(BASE/'final_temporary_001'),'-o','cache_dir='+str(BASE/'final_cache_001'),
    '--junitxml',str(BASE/'FINAL_TESTS_001.xml')])
imports={name:str(Path(module.__file__).resolve()) for name,module in sys.modules.items()
         if getattr(module,'__file__',None) and name.startswith(('gene_annotation_episode','method_loop','test_'))}
outside={name:path for name,path in imports.items() if not Path(path).is_relative_to(PIN)}
changed=[path for path,digest in hashes.items() if hashlib.sha256((PIN/path).read_bytes()).hexdigest()!=digest]
result={'exit_code':int(code),'elapsed_seconds':time.time()-start,'files':files,'imports':imports,
    'imports_outside_pin':outside,'changed_pinned_files':changed,
    'scope':'Pure calculations and controlled selected-operation/typed-return/reconstruction verification. No actual model-backed literature execution or A105 adequacy claim.'}
(BASE/'FINAL_RESULT_001.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items() if key not in ('imports','files')},indent=2))
raise SystemExit(int(code) or bool(outside or changed))
