"""Root review of final mixed-pin selected/cold integration, controlled choices."""
import contextlib
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNER = HERE.parent / 'a105_summary_precision_binding_251'
JOINED = HERE / 'joined_pin_008'
assert not JOINED.exists()
sys.dont_write_bytecode = True
manifest = json.loads((OWNER / 'PIN_MANIFEST_013.json').read_text())
packet = json.loads((OWNER / 'FINAL_PACKET_MANIFEST_013.json').read_text())
for row in packet['files']:
    assert sha256((OWNER / row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
hashes = {}
for row in manifest['files']:
    relative = Path(row['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    assert relative.name != 'GOAL.md'
    data = (OWNER / row['pin_path']).read_bytes()
    assert sha256(data).hexdigest() == row['sha256'], str(relative)
    target = JOINED / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    hashes[str(relative)] = row['sha256']
for row in manifest['supplement_proof_files']:
    assert sha256((OWNER / row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']

def verify_joined():
    for relative, digest in hashes.items():
        assert sha256((JOINED / relative).read_bytes()).hexdigest() == digest, relative

verify_joined()
os.chdir(JOINED)
sys.path[:0] = [str(JOINED), str(JOINED / 'tests')]
import pytest
started = time.monotonic()
with (HERE / 'ROOT_JOINED_SELECTED_008.log').open('x') as output:
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = pytest.main([
            '-q', '--tb=short', '-c', '/dev/null', '-p', 'no:cacheprovider',
            '--basetemp=' + str(HERE / 'selected_state_008'),
            '--junitxml=' + str(HERE / 'ROOT_JOINED_SELECTED_008.xml'),
            'tests/test_literature_kinetic_summary_precision_binding_251.py',
            '-k', 'selected_shared_loop_first_readonly_composer_and_observations or '
            'original_pending_alias_first_cold_compose_no_new_factories or '
            'legacy_selected_kinetic_request_result_and_cold_unchanged or '
            'original_source_narrow_identity_context_survives_parent_view_and_cold',
        ])
imports = {}
for name, module in tuple(sys.modules.items()):
    filename = getattr(module, '__file__', None)
    if not filename:
        continue
    path = Path(filename).resolve()
    if path.is_relative_to(JOINED) and path.is_file():
        relative = str(path.relative_to(JOINED))
        digest = sha256(path.read_bytes()).hexdigest()
        assert hashes.get(relative) == digest, relative
        imports[relative] = digest
    elif name != '__main__' and path.suffix == '.py' and path.is_relative_to(ROOT) and not path.is_relative_to(Path(sys.prefix)):
        raise AssertionError('Project import escaped joined pin: ' + str(path))
verify_joined()
cases = ET.parse(HERE / 'ROOT_JOINED_SELECTED_008.xml').getroot().findall('.//testcase')
failed = [case.attrib for case in cases if case.find('failure') is not None or case.find('error') is not None]
result = {
    'status': 'pass' if int(code) == 0 and len(cases) == 9 and not failed else 'fail',
    'pytest_exit_code': int(code), 'cases': [case.attrib for case in cases], 'failed': failed,
    'elapsed_seconds': time.monotonic() - started,
    'joined_input_files_rehashed_before_and_after': len(hashes),
    'packet_files_rehashed': len(packet['files']),
    'supplement_proof_files_rehashed': len(manifest['supplement_proof_files']),
    'input_manifest_sha256': sha256((OWNER / 'PIN_MANIFEST_013.json').read_bytes()).hexdigest(),
    'actual_local_imports': imports,
    'controlled_choices_only': True, 'actual_model_backed_science': False,
    'private_provider_data_read': False, 'goal_changed': False, 'A105_complete': False,
}
with (HERE / 'ROOT_JOINED_SELECTED_REVIEW_008.json').open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps({k: v for k, v in result.items() if k not in ('actual_local_imports', 'cases')}, indent=2))
assert result['status'] == 'pass', result
