"""Complement root229's already passed26 cases on the identical immutable pin."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent
ORIGINAL = BASE / 'a105_common_assessment_binding_review_229'
PIN = ORIGINAL / 'pin_001'
mode = sys.argv[1]
groups = {
    'pure': ['test_literature_common_assessment_221.py', 'test_literature_compiled_assay_185.py',
             'test_literature_compiled_assay_uncertainty_215.py', 'test_literature_product_coupling_212.py'],
    'binding': ['test_literature_compiled_assay_binding_185.py', 'test_literature_product_coupling_binding_218.py',
                'test_literature_numerical_declarations_203.py', 'test_literature_measurement_validation_binding_209.py'],
}
assert mode in groups
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
manifest = json.loads((ORIGINAL / 'PIN_001.json').read_text())
assert all(Path(name).name != 'GOAL.md' and sha(PIN / name) == expected
           for name, expected in manifest['hashes'].items())
sys.dont_write_bytecode = True
sys.path = [str(PIN), str(PIN / 'tests'), *[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT, ROOT / 'tests')]]
os.chdir(PIN)
import pytest
started = time.time()
args = ['-c', str(PIN / 'pytest.ini'), '--rootdir', str(PIN), '-q', '-p', 'no:cacheprovider',
        '--tb=short', '--basetemp=' + str(HERE / (mode + '_temporary_001')),
        '--junitxml=' + str(HERE / (mode.upper() + '_TESTS_001.xml')),
        *['tests/' + name for name in groups[mode]]]
code = pytest.main(args)
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
           if getattr(module, '__file__', None)
           and name.startswith(('gene_annotation_episode', 'method_loop', 'test_', 'tests.test_'))}
outside = {name: path for name, path in imports.items() if not Path(path).is_relative_to(PIN)}
changed = [name for name, expected in manifest['hashes'].items() if sha(PIN / name) != expected]
result = dict(exit_code=int(code), elapsed_seconds=time.time() - started, arguments=args,
              imports=imports, imports_outside_pin=outside, changed_pinned_files=changed,
              scope='Complementary existing regression modules on exact root229/owner223pin003. Controlled fixtures; no actual-model/A105 adequacy or external MinHash behavior claim.')
with (HERE / (mode.upper() + '_RESULT_001.json')).open('x') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps({key: value for key, value in result.items() if key != 'imports'}, indent=2))
raise SystemExit(int(code) or bool(outside or changed))
