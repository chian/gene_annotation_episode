"""Independent structural audit of closed controlled223 state, never live payloads."""
from pathlib import Path
import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

def write_new(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

result = json.loads((HERE / 'ROOT_RESULT_001.json').read_text())
assert result['exit_code'] == 0
assert not result['imports_outside_pin'] and not result['changed_pinned_files']
manifest = json.loads((HERE / 'PIN_001.json').read_text())
assert all(Path(name).name != 'GOAL.md' for name in manifest['hashes'])
assert all(sha(HERE / 'pin_001' / name) == expected for name, expected in manifest['hashes'].items())
xml = ET.parse(HERE / 'ROOT_TESTS_001.xml')
cases = list(xml.iter('testcase'))
assert cases and not list(xml.iter('failure')) and not list(xml.iter('error')) and not list(xml.iter('skipped'))

proofs = []
for case_dir in sorted((HERE / 'temporary_001').iterdir()):
    if case_dir.is_symlink() or not case_dir.is_dir():
        continue
    path = case_dir / 'COLD_PROOF_223.json'
    if not path.exists():
        continue
    proof = json.loads(path.read_text())
    assert proof['read_only_before_composer'] and proof['source_science_model_receive_blocked_before_composer']
    assert proof['original_form_schema_rows_and_descriptor']
    assert proof['changed_rows'] == 0 and proof['selected_common_operations'] == 1
    assert proof['actual_model_execution'] is False and proof['a105_adequacy_claim'] is False
    expected_count = 9 if proof['nested'] else 7
    assert proof['ordinary_completed_actions_and_observations'] == expected_count
    before = {name: sha(case_dir / 'state' / name) for name in proof['state_files']}
    assert before == proof['state_files']
    form = json.loads((case_dir / 'ORIGINAL_FORM_223.json').read_text())
    components = [row['component'] for row in form['numbers']]
    assert components == (['product_reference_contrast'] if proof['nested'] else [
        'estimate_product_test', 'product_reference_contrast',
        'post_binding_residual_ratio', 'binding_only_residual_variance'])
    db = sqlite3.connect((case_dir / 'state' / 'state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)
    with db:
        rows = db.execute('SELECT run_id FROM runtime_runs').fetchall()
        assert len(rows) == 1
        run_id = rows[0][0]
        counts = {table: db.execute('SELECT count(*) FROM ' + table + ' WHERE run_id=?', (run_id,)).fetchone()[0]
                  for table in ['runtime_actions', 'runtime_observations', 'literature_compiled_assay_operations']}
        assert counts == dict(runtime_actions=expected_count, runtime_observations=expected_count,
                              literature_compiled_assay_operations=1)
        assert db.total_changes == 0
    db.close()
    assert before == {name: sha(case_dir / 'state' / name) for name in proof['state_files']}
    proofs.append(dict(directory=str(case_dir.relative_to(HERE)), profile=proof['profile'], alias=proof['alias'],
                       index=proof['index'], nested=proof['nested'], counts=counts, selected_components=components,
                       state_files=len(before), proof_sha256=sha(path)))
assert len(proofs) == 9
assert {(p['index'], p['alias'], p['profile']) for p in proofs if not p['nested']} == {
    (index, alias, profile) for index in (1, 3) for alias in (False, True)
    for profile in (None, 'operation_contract_information_v1')}
assert sum(p['nested'] for p in proofs) == 1

old = json.loads((BASE / 'a105_common_assessment_binding_223' / 'OLD_STATE_BASELINE_001.json').read_text())
old_root = Path(old['proof_directory']) / 'state'
assert all(sha(old_root / name) == expected for name, expected in old['state_files'].items())
write_new('ROOT_CLOSED_PROOF_AUDIT_001.json', dict(
    passed=True, completed_pytest_cases=len(cases), pinned_files_verified=len(manifest['hashes']),
    repository_imports=len(result['imports']), proofs=proofs, old_state_files_unchanged=len(old['state_files']),
    old_compatibility='Closed v1/v2 data reader only; original runtime descriptors require their original code pin.',
    scope='Closed controlled-provider fixtures and original typed scientific state only. No actual private provider contents, actual-model quality or A105 adequacy claim.'))
print(json.dumps(dict(passed=True, completed_pytest_cases=len(cases), unique_cold_proofs=len(proofs),
                      pinned_files=len(manifest['hashes'])), indent=2))
