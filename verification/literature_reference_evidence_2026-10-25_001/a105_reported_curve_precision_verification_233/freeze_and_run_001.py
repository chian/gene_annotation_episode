"""Independently freeze228 finalpure code and original-source fixtures."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent
PREVIOUS = BASE / 'a105_common_assessment_binding_review_229'
OWNER = BASE / 'a105_reported_curve_precision_228'
PIN = HERE / 'pin_001'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
prior = json.loads((PREVIOUS / 'PIN_001.json').read_text())
freeze = json.loads((OWNER / 'FREEZE_001.json').read_text())
assert not PIN.exists()
hashes = {}
for name, expected in prior['hashes'].items():
    assert Path(name).name != 'GOAL.md'
    source = PREVIOUS / 'pin_001' / name
    assert sha(source) == expected
    target = PIN / name; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target); hashes[name] = expected
for entry in [*freeze['code_and_test'], *freeze['immutable_fixture_oracle_prefix_dependencies']]:
    name, expected = entry['path'], entry['sha256']
    assert Path(name).name != 'GOAL.md' and sha(ROOT / name) == expected
    target = PIN / name; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
    assert sha(target) == expected
    hashes[name] = expected
manifest = dict(hashes=hashes, original_owner_freeze=freeze,
                scope='Final228pure source reader/calculator only; selected integration not implemented.')
with (HERE / 'PIN_001.json').open('x') as stream:
    json.dump(manifest, stream, indent=2); stream.write('\n')
sys.dont_write_bytecode = True
sys.path = [str(PIN), str(PIN / 'tests'), *[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT, ROOT / 'tests')]]
os.chdir(PIN)
import pytest
started = time.time()
code = pytest.main(['-c', str(PIN / 'pytest.ini'), '--rootdir', str(PIN), '-q', '-p', 'no:cacheprovider',
    '--basetemp=' + str(HERE / 'temporary_001'), '--junitxml=' + str(HERE / 'ROOT_TESTS_001.xml'),
    'tests/test_literature_reported_curve_precision_228.py'])
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
           if getattr(module, '__file__', None)
           and name.startswith(('gene_annotation_episode', 'method_loop', 'test_', 'tests.test_'))}
outside = {name: path for name, path in imports.items() if not Path(path).is_relative_to(PIN)}
changed = [name for name, expected in hashes.items() if sha(PIN / name) != expected]
result = dict(exit_code=int(code), elapsed_seconds=time.time() - started, imports=imports,
              imports_outside_pin=outside, changed_pinned_files=changed,
              scope='Independent complete27case228pure module; original225source and227oracles, no selected transport/model/A105 adequacy claim.')
with (HERE / 'ROOT_RESULT_001.json').open('x') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps({key: value for key, value in result.items() if key != 'imports'}, indent=2))
raise SystemExit(int(code) or bool(outside or changed))
