"""Root final008 source/package/dependency verification, no science acquisition."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
STAGE = BASE / 'a105_controlled_response_design_056/implementation_stage_008'
PIN = STAGE / 'execution_pin_008'


def fingerprint(path):
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def load(path):
    return json.loads(path.read_bytes())


def main():
    delivery_path = STAGE / 'DELIVERY_008.json'
    assert fingerprint(delivery_path)['sha256'] == '855bf0e1f761617b7d2331f046592cd190497783e21eaa95c52e91465bba9d4c'
    delivery = load(delivery_path)
    for name, expected in delivery['artifact_hashes'].items():
        assert fingerprint(STAGE / name) == expected, name
    pin = load(STAGE / 'PIN_MANIFEST_008.json')['pin_files']
    for name, expected in pin.items():
        assert fingerprint(PIN / name) == expected, name
    assert {str(path.relative_to(PIN)) for path in PIN.rglob('*') if path.is_file()} == set(pin)
    rebuilt = HERE / 'root_reconstructed_008'
    rebuilt.mkdir()
    for name in delivery['owned_new_paths']:
        (rebuilt / name).parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(['patch', '-p0', '--batch', '-i', str(STAGE / 'NEW_FILES_008.patch')],
                            cwd=rebuilt, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    for name, expected in delivery['owned_new_paths'].items():
        for base in (rebuilt, ROOT, PIN, STAGE / 'final_snapshot_008'):
            assert fingerprint(base / name) == expected, (str(base), name)
    dependencies = load(STAGE / 'DEPENDENCY_AFTER_008.json')
    for name, expected in dependencies['accepted006_and007_verified_files'].items():
        assert fingerprint(ROOT / name) == {key: expected[key] for key in ('sha256', 'bytes')}, name
    imports = load(STAGE / 'ACTUAL_IMPORTS_008.json')
    assert imports['pytest_exitstatus'] == 0 and not imports['misplaced_package_imports']
    actual_imports = {}
    for name, record in imports['imports'].items():
        if name == 'gene_annotation_episode' or name.startswith('gene_annotation_episode.'):
            path = Path(record['path']).resolve()
            relative = str(path.relative_to(PIN.resolve()))
            assert fingerprint(path)['sha256'] == record['sha256'] == pin[relative]['sha256']
            actual_imports[name] = relative
    terminal = load(STAGE / 'TERMINAL_008.json')
    assert terminal['exit_code'] == 0
    assert fingerprint(STAGE / 'TERMINAL_STDOUT_008.txt') == terminal['stdout']
    assert fingerprint(STAGE / 'TERMINAL_STDERR_008.txt') == terminal['stderr']
    assert '319 passed in 3.62s' in (STAGE / 'TERMINAL_STDOUT_008.txt').read_text()
    after = load(STAGE / 'PIN_AFTER_008.json')
    assert after == {'all_pinned_files_unchanged': True, 'extra_pin_files': []}
    fixed = load(HERE / 'DEFINED_UNIT_PARTIAL_PROBE_008_002.json')
    assert fixed['saved_validation_accepts_its_own_valid_partial']
    assert fixed['promoting_unavailable_definition_to_supported_rejected']
    receipt = {'scope': 'Pure reader source/package/actual-test-artifact verification; no paper, model or runtime execution.',
               'sealed_artifacts_verified': len(delivery['artifact_hashes']),
               'pin_files_verified': len(pin), 'new_files_independently_reconstructed': len(delivery['owned_new_paths']),
               'frozen006_007_files_verified': len(dependencies['accepted006_and007_verified_files']),
               'actual_package_imports_verified': actual_imports,
               'owner_targeted_terminal_verified': '319 passed in 3.62s; exit0; root did not rerun the whole suite',
               'independent_partial_roundtrip_fix_reproduced': True,
               'domain_delta_scope': 'Documented independent schema-only change; pin uses its recorded generation; no full runtime coherence claim.',
               'native_selected_runtime_or_primary_coverage_established': False}
    with (HERE / 'DELIVERY_ROOT_RECEIPT_008.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
