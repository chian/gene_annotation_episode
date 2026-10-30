"""Independent read-only audit of controlled 218/222 verification evidence."""
from pathlib import Path
import ast
import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OWNER = HERE.parent / 'a105_product_coupling_binding_218'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def write(name, value):
    with (HERE / name).open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write('\n')


def definitions(path):
    result = {}
    def visit(node, prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                key = prefix + child.name
                result[key] = ast.dump(child, include_attributes=False)
                visit(child, key + '.')
    visit(ast.parse(path.read_text()))
    return result


pins = {n: load(HERE / f'PIN_{n}.json') for n in ('002', '003')}
checks = {}
for n, pin in pins.items():
    changed = [name for name, sha in pin['hashes'].items()
               if digest(HERE / f'pin_{n}' / name) != sha]
    assert not changed, changed
    outcome = load(HERE / f'ROOT_RESULT_{n}.json')
    assert outcome['exit_code'] == 0
    assert not outcome['imports_outside_pin'] and not outcome['changed_pinned_files']
    suites = list(ET.parse(HERE / f'ROOT_TESTS_{n}.xml').getroot().iter('testsuite'))
    assert all(int(s.get(k, '0')) == 0 for s in suites for k in ('errors', 'failures', 'skipped'))
    checks[n] = {'pinned_files': len(pin['hashes']),
                 'passing_tests': sum(int(s.get('tests')) for s in suites),
                 'runner_elapsed_seconds': outcome['elapsed_seconds'],
                 'imports_verified_inside_pin': len(outcome['imports']),
                 'changed_files': changed}

delta = {name for name in pins['002']['hashes']
         if pins['002']['hashes'][name] != pins['003']['hashes'][name]}
expected_delta = {'pytest.ini', 'gene_annotation_episode/literature_product_coupling_storage.py',
                  'tests/test_literature_product_coupling_binding_218.py'}
assert delta == expected_delta, delta
old = ast.parse((HERE/'pin_002/gene_annotation_episode/literature_product_coupling_storage.py').read_text())
new = ast.parse((HERE/'pin_003/gene_annotation_episode/literature_product_coupling_storage.py').read_text())
old_helper = next(n for n in ast.walk(old) if isinstance(n, ast.FunctionDef) and n.name == '_meaning')
new_helper = next(n for n in ast.walk(new) if isinstance(n, ast.FunctionDef) and n.name == '_meaning_v1')
assert ast.dump(ast.Module(body=old_helper.body[1:] if ast.get_docstring(old_helper) else old_helper.body, type_ignores=[]), include_attributes=False) == ast.dump(
    ast.Module(body=new_helper.body[1:] if ast.get_docstring(new_helper) else new_helper.body, type_ignores=[]), include_attributes=False)

protected = load(OWNER/'PROTECTED_DEPENDENCIES_001.json')
updates = load(OWNER/'AUTHORIZED_DEPENDENCY_UPDATE_001.json')
for name, update in updates.items():
    assert protected[name] == update['original_before218_sha256']
    protected[name] = update['current_sha256']
assert all(digest(HERE/'pin_003'/name) == sha for name, sha in protected.items())
shared = {}
for name, sha in load(OWNER/'SHARED_BASELINE_001.json').items():
    before = OWNER/'before'/name
    assert digest(before) == sha
    previous, current = definitions(before), definitions(HERE/'pin_003'/name)
    shared[name] = {'added_definitions': sorted(current.keys()-previous.keys()),
                    'removed_definitions': sorted(previous.keys()-current.keys()),
                    'changed_definitions': sorted(k for k in current.keys() & previous.keys()
                                                  if current[k] != previous[k])}

proofs = []
for proof_file in sorted((HERE/'temporary_003').rglob('*PROOF*json')):
    proof = load(proof_file)
    old_case = 'actual_old_case' in proof
    state = Path(proof['actual_old_case'])/'state' if old_case else proof_file.parent/'state'
    assert all(digest(state/name) == sha for name, sha in proof['state_files'].items())
    assert proof['connection'] == 'mode=ro&immutable=1;query_only=ON'
    assert proof['written_rows' if old_case else 'changed_rows'] == 0
    db = sqlite3.connect((state/'state.sqlite3').resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
    try:
        db.execute('PRAGMA query_only=ON')
        counts = {table: db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                  for table in ('runtime_observations', 'runtime_actions',
                                'literature_product_coupling_operations')}
    finally:
        db.close()
    assert counts['runtime_observations'] == counts['runtime_actions'] == 3, counts
    assert counts['literature_product_coupling_operations'] == 1
    if not old_case:
        assert proof['ordinary_own_action_observations'] == 3
        assert proof['source_covariance_science_receive_model_blocked_before_composition']
        assert proof['actual_model_execution'] is False and proof['a105_adequacy_claim'] is False
    else:
        assert proof['current_projection_source_science_model_receive_blocked']
        assert proof['old_descriptor_not_migrated']
    proofs.append({'proof': str(proof_file.relative_to(HERE)), 'old_markerless_state': old_case,
                   'state_files_verified': len(proof['state_files']), 'counts': counts,
                   'zero_writes_recorded_and_file_hashes_reverified': True})
assert len(proofs) == 10 and sum(x['old_markerless_state'] for x in proofs) == 2
write('ROOT_COLD_PROOFS_001.json', {'scope': 'Controlled saved states only; counts and file hashes, no private model payloads.', 'proofs': proofs})
write('ROOT_PRESERVATION_001.json', {'test_cohorts_overlap_do_not_sum_as_unique_tests': True,
    'cohorts': checks, 'corrected_pin_delta_including_distinct_harness_config': sorted(delta), 'legacy_helper_executable_body_ast_equal_excluding_added_docstring': True,
    'protected_hashes_after_explicit215_update': protected, 'shared_definition_delta': shared,
    'live221_work_in_progress_excluded_from_frozen_pins': True})
print(json.dumps({'cohorts': checks, 'cold_proofs': len(proofs), 'old_markerless_proofs': 2,
                  'protected_files': len(protected), 'shared_files': len(shared), 'status': 'passed'}))
