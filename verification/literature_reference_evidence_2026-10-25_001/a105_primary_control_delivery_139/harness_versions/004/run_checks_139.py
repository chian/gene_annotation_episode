"""Fingerprint the current inputs and retain actual pytest results/imports."""
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

def digest(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

paths = [p for directory in ('gene_annotation_episode', 'method_loop')
         for p in (ROOT / directory).rglob('*')
         if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
paths += [ROOT / 'tests/test_runtime.py', HERE / 'test_primary_delivery_139.py', Path(__file__).resolve(),
          ROOT / 'research/experimental_scoring_review_2026-10-23/a105_optical_case_031/primary_access_0.bin',
          HERE.parent / 'a105_optical_parent_repair_138/ROOT_ARTICLE_TEXT_001.txt']
selected_tests = sys.argv[2:] or [str(HERE / 'test_primary_delivery_139.py')]
paths += [ROOT / value.split('::', 1)[0] for value in selected_tests
          if not Path(value.split('::', 1)[0]).is_absolute()]
before = {str(p.relative_to(ROOT)): digest(p) for p in paths}
label = sys.argv[1]
(HERE / f'PIN_{label}.json').write_text(json.dumps(before, indent=2) + '\n')
import pytest
code = pytest.main([*selected_tests, '-q',
    '--basetemp=' + str(HERE / ('run' + label)), '--junitxml=' + str(HERE / f'RESULT_{label}.xml')])
after = {name: digest(ROOT / name) for name in before}
imports = {}
for name, module in list(sys.modules.items()):
    file = getattr(module, '__file__', None)
    if file:
        path = Path(file).resolve()
        if path.is_file() and path.is_relative_to(ROOT) and '.venv' not in path.parts:
            imports[name] = {'path': str(path.relative_to(ROOT)), **digest(path)}
(HERE / f'IMPORTS_{label}.json').write_text(json.dumps(imports, indent=2) + '\n')
(HERE / f'CHECK_{label}.json').write_text(json.dumps({'pytest_exit': code,
    'fingerprinted_file_count': len(before), 'changed_during_test': [name for name in before if before[name] != after[name]],
    'imported_local_module_count': len(imports)}, indent=2) + '\n')
raise SystemExit(code)
