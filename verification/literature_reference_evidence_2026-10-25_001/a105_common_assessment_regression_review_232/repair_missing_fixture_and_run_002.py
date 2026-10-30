"""Add one omitted unchanged data fixture in a NEW pin; rerun three failures only."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent
ORIGINAL = BASE / 'a105_common_assessment_binding_review_229'
PIN = HERE / 'pin_002'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
baseline = json.loads((ORIGINAL / 'PIN_001.json').read_text())
assert not PIN.exists()
hashes = {}
for name, expected in baseline['hashes'].items():
    assert Path(name).name != 'GOAL.md'
    source = ORIGINAL / 'pin_001' / name
    assert sha(source) == expected
    target = PIN / name; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target); hashes[name] = expected
relative = 'verification/literature_reference_evidence_2026-10-25_001/a105_common_scoring_gap_review_200/SOURCE_PACKET_001.json'
fixture = ROOT / relative
historical = BASE / 'a105_measurement_validation_review_208/pin_001' / relative
assert relative not in hashes and sha(fixture) == sha(historical)
target = PIN / relative; target.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(fixture, target); hashes[relative] = sha(fixture)
packet = json.loads(fixture.read_text())
data_source = Path(packet['source']['path'])
assert sha(data_source) == packet['source']['sha256']
tree = ET.parse(HERE / 'BINDING_TESTS_001.xml')
failed = [node for node in tree.iter('testcase') if node.find('failure') is not None]
assert len(failed) == 3
assert all('FileNotFoundError' in node.find('failure').text
           and 'a105_common_scoring_gap_review_200/SOURCE_PACKET_001.json' in node.find('failure').text
           for node in failed)
targets = ['tests/' + node.attrib['classname'].removeprefix('tests.') + '.py::' + node.attrib['name']
           for node in failed]
manifest = dict(hashes=hashes, original_code_pin=str(ORIGINAL / 'PIN_001.json'),
    added_data_fixture=relative, added_fixture_sha256=sha(fixture),
    historical_fixture_copy=str(historical), code_or_test_changes=[],
    external_original_source=dict(path=str(data_source), sha256=packet['source']['sha256']),
    targeted_failed_cases=targets,
    scope='Only one byte-identical original data fixture added; original pin/results unchanged. No new paper conversion.')
with (HERE / 'PIN_002.json').open('x') as stream:
    json.dump(manifest, stream, indent=2); stream.write('\n')
sys.dont_write_bytecode = True
sys.path = [str(PIN), str(PIN / 'tests'), *[p for p in sys.path
    if Path(p or os.getcwd()).resolve() not in (ROOT, ROOT / 'tests')]]
os.chdir(PIN)
import pytest
started = time.time()
code = pytest.main(['-c', str(PIN / 'pytest.ini'), '--rootdir', str(PIN), '-q', '-p', 'no:cacheprovider',
    '--tb=short', '--basetemp=' + str(HERE / 'binding_repair_temporary_002'),
    '--junitxml=' + str(HERE / 'BINDING_REPAIR_TESTS_002.xml'), *targets])
imports = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
    if getattr(module, '__file__', None)
    and name.startswith(('gene_annotation_episode', 'method_loop', 'test_', 'tests.test_'))}
outside = {name: path for name, path in imports.items() if not Path(path).is_relative_to(PIN)}
changed = [name for name, expected in hashes.items() if sha(PIN / name) != expected]
data_unchanged = sha(data_source) == packet['source']['sha256']
result = dict(exit_code=int(code), elapsed_seconds=time.time()-started, imports=imports,
    imports_outside_pin=outside, changed_pinned_files=changed, external_original_data_unchanged=data_unchanged,
    code_or_test_changes=[], scope='Only three original fixture failures rechecked. No complete repeated cohort or A105 adequacy claim.')
with (HERE / 'BINDING_REPAIR_RESULT_002.json').open('x') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps({key: value for key, value in result.items() if key != 'imports'}, indent=2))
raise SystemExit(int(code) or bool(outside or changed) or not data_unchanged)
