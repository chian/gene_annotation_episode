"""Independent code-only authentication of delivered052/055 generations.

No paper, model history, provider credentials or scientific source is read.
"""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def verify_entries(entries, base):
    for name, row in entries.items():
        path = base / name
        assert path.stat().st_size == row['bytes'], name
        assert digest(path) == row['sha256'], name
    return len(entries)


def apply(directory, patch):
    result = subprocess.run(['patch', '-p1', '--batch', '--fuzz=0', '-i', str(patch)],
                            cwd=directory, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'offset' not in result.stdout and 'fuzz' not in result.stdout


def functions(path):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(path.read_text()).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def tasks(path):
    return {target.id: ast.dump(node.value, include_attributes=False)
            for node in ast.parse(path.read_text()).body if isinstance(node, ast.Assign)
            for target in node.targets if isinstance(target, ast.Name)
            and ('TASK' in target.id or target.id == 'ROLE_INSTRUCTIONS')}


def main():
    binding = BASE / 'a105_binding_native_design_052'
    count = BASE / 'a105_source_count_words_055'
    manifest052 = load(binding / 'MANIFEST_005.json')
    entries052 = verify_entries(manifest052['entries'], ROOT)
    entries055 = verify_entries(load(count / 'FINAL_MANIFEST_014.json'), count)
    snapshot052 = load(binding / 'SNAPSHOT_HASHMAP_005.json')
    rebuild052 = OUT / 'reconstructed_binding_005'
    rebuild052.mkdir()
    for name, row in snapshot052.items():
        if row['new']:
            continue
        baseline = binding / ('baseline_compatibility_005' if name.startswith('tests/')
                              else 'baseline_integration_004') / name
        target = rebuild052 / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(baseline, target)
    apply(rebuild052, binding / 'IMPLEMENTATION_INTEGRATION_005.patch')
    for name, row in snapshot052.items():
        assert digest(rebuild052 / name) == row['052_patch_sha256'], name
    apply(rebuild052, binding / 'AUTHORIZED_RENDERER_055_DELTA_005.patch')
    for name, row in snapshot052.items():
        for path in (rebuild052 / name, binding / 'snapshot_005' / name, ROOT / name):
            assert digest(path) == row['sha256'], str(path)
    old_test = binding / 'baseline_compatibility_005/tests/test_literature_native_rate_operand_information.py'
    new_test = ROOT / 'tests/test_literature_native_rate_operand_information.py'
    assert old_test.read_text().replace('assert len(catalog) == 18', 'assert len(catalog) == 19', 1) == new_test.read_text()
    before = load(binding / 'TEST_GENERATION_BEFORE_005.json')
    after = load(binding / 'TEST_GENERATION_AFTER_005.json')
    changed = {name for name in before if before[name] != after[name]}
    assert changed == {'gene_annotation_episode/native_blast_database_contracts.py',
                       'gene_annotation_episode/native_blast_database_driver.py'}
    tracked = load(binding / 'FROZEN_DEPENDENCY_PROOF_005.json')['tracked_binding_literature_sha256']
    for name, expected in tracked.items():
        assert before[name] == after[name] == digest(ROOT / name) == expected, name
    assert load(binding / 'TERMINAL_INTEGRATION_RECEIPT_005.json')['exit_code'] == 0
    assert '62 passed in 123.84s' in (binding / 'TERMINAL_INTEGRATION_005.log').read_text()

    delivery055 = load(count / 'FINAL_DELIVERY_RECEIPT_014.json')
    pin = count / 'frozen_checks_012/pin'
    pin_manifest = load(pin / 'PIN_MANIFEST.json')
    pin_count = verify_entries(pin_manifest['files'], pin)
    assert digest(pin / 'PIN_MANIFEST.json') == delivery055['pin_manifest_sha256']
    terminal = load(count / 'frozen_checks_012/TERMINAL_RECEIPT.json')
    worker = load(count / 'frozen_checks_012/WORKER_RECEIPT.json')
    assert terminal['exit_code'] == worker['pytest_exit_code'] == 0
    assert terminal['pin_manifest_sha256'] == worker['pin_manifest_sha256'] == digest(pin / 'PIN_MANIFEST.json')
    assert worker['application_and_test_imports_verified_from_pin'] == 184
    assert '426 passed in 193.11s' in (count / 'frozen_checks_012/TERMINAL.log').read_text()
    rebuild055 = OUT / 'reconstructed_count_014'
    rebuild055.mkdir()
    for name, row in delivery055['owned_files'].items():
        if row['baseline'] is not None:
            source = Path(row['baseline'])
            assert digest(source) == row['baseline_sha256'], name
            target = rebuild055 / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    apply(rebuild055, count / 'FINAL_PATCH_014.diff')
    for name, row in delivery055['owned_files'].items():
        for path in (rebuild055 / name, ROOT / name, count / 'snapshot_014' / name, pin / name):
            assert digest(path) == row['sha256'], str(path)
    renderer = 'gene_annotation_episode/literature_experimental_prompt.py'
    assert (ROOT / renderer).read_bytes() == (count / 'renderer_proposal_009/proposed.py').read_bytes()
    baseline_renderer = count / 'renderer_proposal_009/baseline.py'
    before_functions = functions(baseline_renderer)
    after_functions = functions(ROOT / renderer)
    changed_functions = [name for name in before_functions if before_functions[name] != after_functions[name]]
    assert changed_functions == ['_kinetic_received'], changed_functions
    assert tasks(baseline_renderer) == tasks(ROOT / renderer)
    storage = 'gene_annotation_episode/literature_kinetic_storage.py'
    assert functions(count / 'baseline_001' / storage)['_witness_label'] == functions(ROOT / storage)['_witness_label']
    helper = 'gene_annotation_episode/literature_binding_interaction_render.py'
    old_helper, new_helper = functions(pin / helper), functions(ROOT / helper)
    helper_changes = [name for name in old_helper if old_helper[name] != new_helper[name]]
    assert helper_changes == ['render_received'], helper_changes
    assert not (set(old_helper) ^ set(new_helper))
    for name in ('_received_returns', '_steering', '_kinetic_received'):
        assert functions(pin / renderer)[name] == functions(ROOT / renderer)[name], name
    public = load(count / 'RUNTIME_PUBLIC_AUDIT_014.json')
    for case in public['cases']:
        database = count / 'frozen_checks_012' / case['database']
        with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as db:
            before_dump = list(db.iterdump())
            assert db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == case['actions']
            assert db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == case['observations']
            assert db.execute('SELECT count(*) FROM literature_kinetic_operations').fetchone()[0] == case['populations']
            assert [r[0] for r in db.execute('SELECT credit FROM runtime_actions ORDER BY rowid')] == case['actual_action_credits']
            values = []
            for record, in db.execute('SELECT cells FROM literature_kinetic_received'):
                for row in json.loads(record):
                    values.append({'component': row['component'],
                        'count': row['numerator']['uncertainty_values']['count'],
                        'count_reported_value': row['numerator']['uncertainty_values']['count_reported_value'],
                        'count_status': row['numerator']['uncertainty']['count_reading_status'],
                        'count_relation': row['numerator']['uncertainty']['count_relation']})
            assert values == case['admitted_typed_values']
            assert before_dump == list(db.iterdump())
    receipt = {'passed': True, 'binding_manifest_entries': entries052, 'count_manifest_entries': entries055,
        'binding_patch_reconstructed_files': len(snapshot052), 'count_patch_reconstructed_files': len(delivery055['owned_files']),
        'binding_tracked_files_unchanged_during_terminal': len(tracked), 'count_pin_files_verified': pin_count,
        'independently_readonly_reproduced_count_cases': len(public['cases']),
        'binding_terminal': '62 passed in123.84s', 'count_terminal': '426 passed in193.11s',
        'count_pin_versus_live_binding_delta_functions': helper_changes,
        'current_head_whole_suite_rerun': False, 'source_paper_or_model_read': False,
        'scope': 'Code-generation and saved public runtime proof; synthetic/controlled choices, no scientific truth or complete A105 claim'}
    with (OUT / 'DELIVERY_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
