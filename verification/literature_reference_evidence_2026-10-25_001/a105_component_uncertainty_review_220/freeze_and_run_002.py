"""Independent frozen compiler uncertainty verification; no model/episode work."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time

ROOT = Path('/home/chia/repos/gene_annotation_episode')
BASE = Path(__file__).resolve().parent
V = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
OWNER = V / 'a105_component_uncertainty_repair_215'
BASELINE = V / 'a105_component_uncertainty_review_220'
PIN = BASE / 'pin_002'
assert not PIN.exists()
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = json.loads((BASELINE / 'PIN_001.json').read_text())
baseline_hashes = baseline.get('hashes', baseline.get('sha256'))
assert isinstance(baseline_hashes, dict), baseline.keys()
for relative, expected in baseline_hashes.items():
    assert Path(relative).name != 'GOAL.md'
    source = BASELINE / 'pin_001' / relative
    assert digest(source) == expected, relative
    target = PIN / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
release = json.loads((OWNER / 'FINAL_CODE_HASHES_002.json').read_text())
for relative, expected in release['hashes'].items():
    source = ROOT / relative
    assert digest(source) == expected, relative
    target = PIN / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
for relative in ('verification/literature_reference_evidence_2026-10-25_001/a105_component_uncertainty_repair_215/V1_SCHEMA_BASELINE_001.json',):
    target = PIN / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / relative, target)
hashes = {str(p.relative_to(PIN)): digest(p) for p in PIN.rglob('*') if p.is_file()}
(BASE / 'PIN_002.json').write_text(json.dumps({'hashes': hashes,
    'owned_code_sha256': release['hashes'],
    'baseline': str(BASELINE)}, indent=2) + '\n')
sys.dont_write_bytecode = True
sys.path = [str(PIN), str(PIN / 'tests'), *[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT, ROOT / 'tests')]]
os.chdir(PIN)
import pytest
start = time.time()
code = pytest.main(['-c', str(PIN / 'pytest.ini'), '--rootdir', str(PIN), '-q',
    'tests/test_literature_compiled_assay_uncertainty_215.py::test_selected_large_integer_covariance_symmetry_before_float_projection',
    'tests/test_literature_compiled_assay_uncertainty_215.py::test_invalid_covariance_fails_actual_selected_operation',
    'tests/test_literature_compiled_assay_uncertainty_215.py::test_v1_defaults_and_original_record_do_not_promote_to_v2',
    'tests/test_literature_compiled_assay_uncertainty_215.py::test_exact_mixed_v1_v2_declarations_preserve_original_snapshot_without_factories',
    'tests/test_literature_compiled_assay_uncertainty_215.py::test_actual_selected_owned_two_operand_uncertainty_and_signed_covariance',
    'tests/test_literature_compiled_assay_uncertainty_215.py::test_mixed_actual_shared_loop_delivery_and_cold_readonly_reconstruction',
    '--basetemp', str(BASE / 'temporary_002'),
    '-o', 'cache_dir=' + str(BASE / 'cache_002'),
    '--junitxml', str(BASE / 'ROOT_TESTS_002.xml')])
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
    if getattr(module, '__file__', None) and name.startswith(('gene_annotation_episode', 'method_loop', 'test_'))}
outside = {name: path for name, path in imports.items() if not Path(path).is_relative_to(PIN)}
changed = [relative for relative, expected in hashes.items() if digest(PIN / relative) != expected]
result = {'exit_code': int(code), 'elapsed_seconds': time.time()-start,
    'imports': imports, 'imports_outside_pin': outside, 'changed_pinned_files': changed,
    'scope': 'Frozen selected compiler, signed component uncertainty, original-v1 compatibility and controlled typed/cold-reconstruction checks. No actual model-backed science or A105 adequacy claim.'}
(BASE / 'ROOT_RESULT_002.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k:v for k,v in result.items() if k != 'imports'}, indent=2))
raise SystemExit(int(code) or bool(outside or changed))
