"""Compare the same stale root-tool tests with all eight pre-059 originals."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

STAGE = Path(__file__).absolute().parent
ROOT = next(p for p in STAGE.parents if (p / '.venv/bin/python').exists())
PIN = STAGE / 'baseline_comparison_008'
shutil.copytree(STAGE / 'pin_006', PIN)
for path in (STAGE / 'baseline').rglob('*.py'):
    shutil.copy2(path, PIN / path.relative_to(STAGE / 'baseline'))
names = ['test_multiple_context_exchanges_complete_one_actual_action_slot_and_observation',
    'test_own_input_detail_requests_stay_inside_pending_decision',
    'test_lookup_visible_publications_extend_interpretation_basis_without_changing_raw_context',
    'test_injected_legacy_default_and_markerless_resume_do_not_migrate']
launcher = ('import pytest,sys;sys.path[:0]=[sys.argv[1],sys.argv[1]+"/tests"];'
    'raise SystemExit(pytest.main(["-q","--tb=short","-p","no:cacheprovider",'
    '*[sys.argv[1]+"/tests/test_runtime_decision_exchanges.py::"+n for n in sys.argv[2:]]]))')
with (STAGE / 'BASELINE_REGRESSION_TERMINAL_008.log').open('x') as stream:
    result = subprocess.run([str(ROOT / '.venv/bin/python'), '-B', '-c', launcher, str(PIN), *names],
        cwd=PIN, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, stdout=stream, stderr=subprocess.STDOUT)
originals = json.loads((STAGE / 'BASELINE_004.json').read_text())
for name, record in originals.items(): assert hashlib.sha256((PIN / name).read_bytes()).hexdigest() == record['sha256']
receipt = {'exit_code': result.returncode, 'tests': names, 'all_eight_originals_verified': originals,
    'comparison': 'All other complete application/shared-loop/static/test files identical to pin_006; no application source patch beyond restoration of the eight pre-059 originals.',
    'original_default': 'root_action_boundary=ROOT_BOUNDARY_VERSION',
    'constraint': 'No root default or legacy fixture modified; this comparison is not the final model-ready pin.'}
with (STAGE / 'BASELINE_REGRESSION_RECEIPT_008.json').open('x') as stream:
    json.dump(receipt, stream, indent=2); stream.write('\n')
print(json.dumps({'exit_code': result.returncode, 'verified_originals': len(originals)}))
