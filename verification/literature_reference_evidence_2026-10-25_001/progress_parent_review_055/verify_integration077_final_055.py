"""Final bounded integration acceptance using actual frozen017 records."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
HERE = Path(__file__).resolve().parent
IMPL = BASE / 'a105_ratio_episode_integration_077/implementation_005'
PIN = IMPL / 'coherent_pin_017'
def read(path):
    return json.loads(path.read_text())
def check(path, row):
    data = path.read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], str(path)
artifact = read(IMPL / 'FINAL_ARTIFACT_MANIFEST_018.json')
for row in artifact['files']:
    check(IMPL / row['path'], row)
before, after = [read(IMPL / name) for name in ('PIN_MANIFEST_BEFORE_017.json', 'PIN_MANIFEST_AFTER_017.json')]
assert before == after
pin_rows = {r['path']: r for r in before}
for row in before:
    check(PIN / row['path'], row)
assert {str(p.relative_to(PIN)) for p in PIN.rglob('*') if p.is_file()} == set(pin_rows)
owned = read(IMPL / 'FINAL_OWNED_MANIFEST_017.json')
patch = ''
for row in owned:
    check(ROOT / row['path'], row)
    check(PIN / row['path'], row)
    original = IMPL / 'before' / row['path']
    old, label = (original.read_text(), 'a/' + row['path']) if original.is_file() else ('', '/dev/null')
    patch += ''.join(difflib.unified_diff(old.splitlines(True), (ROOT / row['path']).read_text().splitlines(True),
        fromfile=label, tofile='b/' + row['path']))
assert patch == (IMPL / 'FINAL_OWNED_PATCH_017.diff').read_text()
audits = list((IMPL / 'import_audit_017').glob('*.json'))
assert len(audits) == 8
imports = set()
for path in audits:
    audit = read(path)
    assert not audit['outside_pin']
    for item in audit['imports']:
        module_path = Path(item['path']).resolve()
        assert module_path.is_relative_to(PIN)
        relative = str(module_path.relative_to(PIN))
        assert pin_rows[relative]['sha256'] == item['sha256']
        imports.add(relative)
assert '186 passed' in (IMPL / 'pytest_pinned_017.log').read_text()
index = read(IMPL / 'FINAL_PROOF_INDEX_018.json')
cases = index['nonduplicated_final_connected_cases']
assert len(cases) == 2 and len({r['directory'] for r in cases}) == 2
for case in cases:
    directory = IMPL / case['directory']
    assert not directory.is_symlink()
    proof = read(directory / 'CONNECTED_PROOF.json')
    readonly = read(directory / 'READONLY_STDOUT.txt')
    spec, returned = proof['spec'], proof['returned']
    rows = returned['form']['requested_signal']
    assert len(rows) == 1 and rows[0]['component'] == 'reported_ratio' and rows[0]['value'] == .64
    assert returned['outcome'] == 'closed' and returned['failure'] is None
    assert returned['completion']['units_consumed'] == 2
    parent, child = spec['parent']['episode_id'], spec['child']['episode_id']
    expected = [(parent, 0, 1, 'wait:1'), (parent, 1, 0, 'child_0'), (parent, 2, 2, 'reason:2'),
                (child, 0, 0, 'tool:0'), (child, 1, 1, 'tool:1')]
    assert sorted(map(tuple, proof['observation_identities'])) == sorted(expected)
    assert readonly['query_only'] == 1 and readonly['total_changes'] == 0
    assert readonly['first_projection'] == rows and readonly['observation_count'] == 5
    assert not readonly['source_image_decoder_model_population_receive_mutation_called']
    steering = proof['parent_steering']
    for label in ('K426A', '1–253', '37 °C', 'pH 7.4'):
        assert label in steering
    for hidden in ('128.000', '200.000', 'difference_from_reference', 'log_reported_ratio',
                   rows[0]['sheet_ref'], rows[0]['subject_ref']):
        assert hidden not in steering

# Re-execute the FIRST fresh readonly proof against the actual pinned recovery
# case. Startup uses only this root-owned directory; insert the pin afterwards
# to avoid adding a new process record to the sealed agent import-audit folder.
test = ast.parse((PIN / 'tests/test_literature_ratio_source_connected_readonly.py').read_bytes())
script = next(ast.literal_eval(n.value) for n in test.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'READONLY' for t in n.targets))
directory = IMPL / cases[1]['directory']
prefix = 'import sys\nsys.path.insert(0,' + repr(str(PIN)) + ')\n'
result = subprocess.run([sys.executable, '-c', prefix + script, str(directory / 'state'),
    str(directory / 'actual-connected077.json')], cwd=HERE, text=True, capture_output=True,
    env={**os.environ, 'PYTHONPATH': str(HERE), 'PYTHONDONTWRITEBYTECODE': '1'})
with (HERE / 'PIN017_RECOVERY_READONLY_ROOT_STDOUT_055.txt').open('x') as stream:
    stream.write(result.stdout)
with (HERE / 'PIN017_RECOVERY_READONLY_ROOT_STDERR_055.txt').open('x') as stream:
    stream.write(result.stderr)
assert result.returncode == 0, result.stderr
independent = json.loads(result.stdout)
assert independent['total_changes'] == 0 and independent['query_only'] == 1
assert Path(independent['storage_import']).is_relative_to(PIN)
assert independent['first_projection'] == read(directory / 'READONLY_STDOUT.txt')['first_projection']
# All selected code and receipt artifacts remain unchanged after root replay.
for row in before:
    check(PIN / row['path'], row)
for case in cases:
    for field in ('connected_proof', 'readonly_stdout'):
        check(IMPL / case[field]['path'], case[field])
receipt = {'utc': datetime.now(timezone.utc).isoformat(),
    'accepted_scope': 'Optional source-ratio LiteratureEpisodes engineering integration, exact typed subset, persistence, reconstruction and ordinary observations',
    'artifact_files_rehashed': len(artifact['files']), 'final_pin_files_verified': len(before),
    'owned_current_and_pinned_files_verified': len(owned), 'exact_ten_file_patch_reconstructed': True,
    'actual_import_processes_verified': len(audits), 'unique_actual_imported_pin_files_verified': len(imports),
    'final_pinned_tests': 186, 'two_distinct_original_and_recovery_connected_proofs_verified': True,
    'root_fresh_readonly_recovery_projection': {'query_only': 1, 'total_changes': 0, 'observation_count': 5},
    'root_independent_selected_durable_case': '055 own earlier007 checkout case also passed; that proof is historical and does not replace final017',
    'same_source_display_correction_root_verified': True,
    'remaining': 'Primary/configured-model validation and full broader literature scope; controlled-v3/local design still requires corrections and implementation',
    'goal_complete': False}
with (HERE / 'INTEGRATION077_ROOT_ACCEPTANCE_055.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps(receipt))
