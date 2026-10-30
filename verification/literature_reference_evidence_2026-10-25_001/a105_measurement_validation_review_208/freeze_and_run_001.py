"""Root-owned frozen pure205 checks; no model or episode execution."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time

ROOT = Path('/home/chia/repos/gene_annotation_episode')
BASE = Path(__file__).resolve().parent
PIN = BASE / 'pin_001'
OWNER = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_measurement_validation_pure_205'
BASELINE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_numerical_declaration_repair_203/pin_001'
assert not PIN.exists()
shutil.copytree(BASELINE, PIN, ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
owned = json.loads((OWNER / 'MANIFEST_002.json').read_text())
checks = []
for record in owned['files']:
    relative = record['path']
    if relative.startswith(('gene_annotation_episode/', 'tests/')):
        source = ROOT / relative
        current = hashlib.sha256(source.read_bytes()).hexdigest()
        assert current == record['sha256'], relative
        target = PIN / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        checks.append({'path': relative, 'sha256': current})
for relative in (
    'verification/literature_reference_evidence_2026-10-25_001/a105_common_scoring_gap_review_200/SOURCE_PACKET_001.json',
    'verification/literature_reference_evidence_2026-10-25_001/a105_measurement_validation_pure_205/FINAL_TASK_001.txt',
):
    destination = PIN / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / relative, destination)
# The pre-existing original-source fixture points to an absolute source path.
# Record and verify that immutable data dependency rather than rewriting it.
packet = json.loads((ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_common_scoring_gap_review_200/SOURCE_PACKET_001.json').read_text())
original = Path(packet['source']['path'])
assert hashlib.sha256(original.read_bytes()).hexdigest() == packet['source']['sha256']
hashes = {str(p.relative_to(PIN)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in PIN.rglob('*') if p.is_file()}
(BASE / 'PIN_001.json').write_text(json.dumps({'hashes': hashes, 'owner_checks': checks,
    'original_data_dependency': {'path': str(original), 'sha256': packet['source']['sha256']}}, indent=2) + '\n')
sys.dont_write_bytecode = True
sys.path = [str(PIN), str(PIN / 'tests'), *[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT, ROOT / 'tests')]]
os.chdir(PIN)
import pytest
start = time.time()
code = pytest.main(['-c', str(PIN / 'pytest.ini'), '--rootdir', str(PIN), '-q',
    'tests/test_literature_measurement_validation_205.py',
    'tests/test_literature_calibration_recovery_169.py',
    '--basetemp', str(BASE / 'temporary_001'),
    '-o', 'cache_dir=' + str(BASE / 'cache_001'),
    '--junitxml', str(BASE / 'ROOT_TESTS_001.xml')])
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
           if getattr(module, '__file__', None) and name.startswith(('gene_annotation_episode', 'method_loop', 'test_'))}
outside = {name: path for name, path in imports.items() if not Path(path).is_relative_to(PIN)}
changed = [path for path, digest in hashes.items() if hashlib.sha256((PIN / path).read_bytes()).hexdigest() != digest]
result = {'exit_code': int(code), 'elapsed_seconds': time.time()-start,
    'imports': imports, 'imports_outside_pin': outside, 'changed_pinned_files': changed,
    'original_data_unchanged': hashlib.sha256(original.read_bytes()).hexdigest() == packet['source']['sha256'],
    'scope': 'Independent frozen rerun of pure parser/calculator and recovery checks. No selected operation, typed child delivery or actual model execution.'}
(BASE / 'ROOT_RESULT_001.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'imports'}, indent=2))
raise SystemExit(int(code) or bool(outside or changed) or not result['original_data_unchanged'])
