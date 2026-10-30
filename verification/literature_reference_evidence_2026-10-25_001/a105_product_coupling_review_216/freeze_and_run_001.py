"""Independent frozen product/cofactor verification; no model/episode work."""
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
OWNER = V / 'a105_product_coupling_pure_212'
BASELINE = V / 'a105_measurement_validation_binding_review_213'
PIN = BASE / 'pin_001'
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
release = json.loads((OWNER / 'RELEASE_MANIFEST_001.json').read_text())
for relative, expected in release['owned_code_sha256'].items():
    source = ROOT / relative
    assert digest(source) == expected, relative
    target = PIN / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
for relative, record in release['protected_dependencies'].items():
    assert digest(ROOT / relative) == digest(PIN / relative) == record['release_sha256'], relative
for relative in (
    'verification/literature_reference_evidence_2026-10-25_001/a105_identified_product_scoring_case_207/SOURCE_PACKET_001.json',
    'verification/literature_reference_evidence_2026-10-25_001/a105_identified_product_review_211/TASK_PROPOSAL_001.txt',
):
    target = PIN / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / relative, target)
hashes = {str(p.relative_to(PIN)): digest(p) for p in PIN.rglob('*') if p.is_file()}
(BASE / 'PIN_001.json').write_text(json.dumps({'hashes': hashes,
    'owned_code_sha256': release['owned_code_sha256'],
    'protected_dependencies': release['protected_dependencies']}, indent=2) + '\n')
sys.dont_write_bytecode = True
sys.path = [str(PIN), str(PIN / 'tests'), *[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT, ROOT / 'tests')]]
os.chdir(PIN)
import pytest
start = time.time()
code = pytest.main(['-c', str(PIN / 'pytest.ini'), '--rootdir', str(PIN), '-q',
    'tests/test_literature_product_coupling_212.py',
    'tests/test_literature_measurement_validation_205.py',
    'tests/test_literature_partner_source_fields.py',
    '--basetemp', str(BASE / 'temporary_001'),
    '-o', 'cache_dir=' + str(BASE / 'cache_001'),
    '--junitxml', str(BASE / 'ROOT_TESTS_001.xml')])
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
    if getattr(module, '__file__', None) and name.startswith(('gene_annotation_episode', 'method_loop', 'test_'))}
outside = {name: path for name, path in imports.items() if not Path(path).is_relative_to(PIN)}
changed = [relative for relative, expected in hashes.items() if digest(PIN / relative) != expected]
result = {'exit_code': int(code), 'elapsed_seconds': time.time()-start,
    'imports': imports, 'imports_outside_pin': outside, 'changed_pinned_files': changed,
    'scope': 'Pure source-bound parsing/calculation and helper checks. No selected binding, model execution or A105 adequacy claim.'}
(BASE / 'ROOT_RESULT_001.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k:v for k,v in result.items() if k != 'imports'}, indent=2))
raise SystemExit(int(code) or bool(outside or changed))
