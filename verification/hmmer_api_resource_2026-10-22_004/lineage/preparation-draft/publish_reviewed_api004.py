"""Publish only an explicitly reviewed, hash-pinned new API004 candidate.

This script is prepared for root inspection. It is never run by preparation
without root's separate authorization of the concrete contract/report/inventory.
No application imports, constructors, tests, DB reads or transport are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def all_files(root):
    values = {}
    for path in sorted(root.rglob('*')):
        assert not path.is_symlink(), str(path)
        if path.is_file():
            values[str(path.relative_to(root))] = path
        else:
            assert path.is_dir(), str(path)
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reviewed-contract', type=Path, required=True)
    parser.add_argument('--publish', action='store_true', required=True)
    args = parser.parse_args()
    contract = json.loads(args.reviewed_contract.read_text())
    required = {'version', 'candidate', 'capsule_destination', 'report_destination',
        'candidate_report_relative_path', 'expected_report_sha256', 'member_inventory_path',
        'member_inventory_sha256', 'runtime_pin', 'source_inputs_path', 'source_inputs_sha256',
        'root_results_path', 'root_results_sha256', 'capsule_directory_mode'}
    assert set(contract) == required and contract['version'] == 'root_reviewed_api004_publication_contract_v1'
    candidate = Path(contract['candidate'])
    capsule = Path(contract['capsule_destination'])
    report = Path(contract['report_destination'])
    assert str(candidate) == '/tmp/api-planning-publication-preparation-20261022-001/candidate'
    assert str(capsule) == '/home/chia/repos/gene_annotation_episode/verification/hmmer_api_resource_2026-10-22_004'
    assert str(report) == '/home/chia/repos/gene_annotation_episode/docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_004.md'
    assert not capsule.exists() and not report.exists()
    assert contract['capsule_directory_mode'] == '0555'
    inventory_path = Path(contract['member_inventory_path'])
    source_inputs_path = Path(contract['source_inputs_path'])
    results_path = Path(contract['root_results_path'])
    assert sha(inventory_path) == contract['member_inventory_sha256']
    assert sha(source_inputs_path) == contract['source_inputs_sha256']
    assert sha(results_path) == contract['root_results_sha256']
    inventory = json.loads(inventory_path.read_text())
    inputs = json.loads(source_inputs_path.read_text())
    results = json.loads(results_path.read_text())
    assert results['distinct_current_pin_cases'] == 316
    assert results['all_source_and_test_bytes_and_membership_unchanged'] is True
    assert results['runtime_implementation_sha256'] == contract['runtime_pin'] == inputs['runtime_pin']
    assert len(inputs['files']) == 344
    paths = all_files(candidate)
    assert set(paths) == set(inventory['members']) and 'MANIFEST.json' not in paths
    for name, row in inventory['members'].items():
        assert row['publish_mode'] in {'0444', '0555'}
        assert sha(paths[name]) == row['sha256'] and paths[name].stat().st_size == row['bytes'], name
    runtime = {name: row for name, row in inputs['files'].items() if not name.startswith('tests/')}
    tests = {name: row for name, row in inputs['files'].items() if name.startswith('tests/')}
    assert len(runtime) == 133 and len(tests) == 211
    actual_candidate_sources = {name for name in paths if name.endswith('.py') and
        name.split('/')[0] in {'gene_annotation_episode', 'method_loop', 'tests'}}
    assert actual_candidate_sources == set(inputs['files'])
    checkout = Path('/tmp/gene-annotation-hmmer-api-20261022-004')
    actual_checkout_sources = {str(path.relative_to(checkout)) for prefix in
        ('gene_annotation_episode', 'method_loop', 'tests')
        for path in (checkout/prefix).rglob('*.py') if '__pycache__' not in path.parts}
    assert actual_checkout_sources == set(inputs['files'])
    for name, row in inputs['files'].items():
        assert sha(candidate/name) == row['sha256']
        assert (candidate/name).stat().st_size == row['bytes']
        assert sha(checkout/name) == row['sha256']
        assert (checkout/name).stat().st_size == row['bytes']
    pin = hashlib.sha256()
    for name, row in sorted(runtime.items()):
        pin.update(name.encode()+b'\0'+bytes.fromhex(row['sha256']))
    assert pin.hexdigest() == contract['runtime_pin']
    parent = Path('/home/chia/repos/gene_annotation_episode/verification/hmmer_api_resource_2026-10-22_003')
    assert sha(parent/'MANIFEST.json') == '32dc15a3533d99d36cae42125549b17da6832066c0ec11af51a3afbeadaf59f1'
    parent_rows = json.loads((parent/'MANIFEST.json').read_text())['members']
    assert len(parent_rows) == 1444
    expected_parent = {row['path'] for row in parent_rows} | {'MANIFEST.json'}
    assert {name.removeprefix('parent-generation003/') for name in paths
        if name.startswith('parent-generation003/')} == expected_parent
    for name in expected_parent:
        assert sha(candidate/'parent-generation003'/name) == sha(parent/name)
    assets = json.loads((parent/'STATIC_INPUTS.json').read_text())['files']
    assert len(assets) == 319
    for name in assets:
        assert sha(candidate/name) == sha(parent/name)
    report_copy = candidate/contract['candidate_report_relative_path']
    assert sha(report_copy) == contract['expected_report_sha256']
    # Mutations begin only after the complete reviewed candidate preflight.
    # Existing paths are never overwritten; any failure leaves partial new work
    # for root inspection rather than repairing or relabeling source evidence.
    shutil.copytree(candidate, capsule, copy_function=shutil.copy2)
    with report.open('xb') as stream:
        stream.write(report_copy.read_bytes())
    for name, row in inventory['members'].items():
        path = capsule/name
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
        path.chmod(int(row['publish_mode'], 8))
    members = [{'path': name, 'sha256': row['sha256'], 'bytes': row['bytes'], 'mode': row['publish_mode']}
        for name, row in sorted(inventory['members'].items())]
    manifest = {'version': 'hmmer_api_resource_verification_capsule_v1',
        'implementation_sha256': contract['runtime_pin'],
        'publication_state': 'published_readonly_from_root_reviewed_contract',
        'root_results_sha256': contract['root_results_sha256'],
        'reviewed_contract_sha256': sha(args.reviewed_contract),
        'directory_mode': contract['capsule_directory_mode'], 'members': members}
    manifest_path = capsule/'MANIFEST.json'
    with manifest_path.open('x') as stream:
        stream.write(json.dumps(manifest, indent=2)+'\n')
    manifest_path.chmod(0o444)
    report.chmod(0o444)
    for directory in sorted([p for p in capsule.rglob('*') if p.is_dir()],
            key=lambda path: len(path.parts), reverse=True):
        directory.chmod(0o555)
    capsule.chmod(0o555)
    assert set(all_files(capsule)) == set(inventory['members']) | {'MANIFEST.json'}
    assert sha(report) == contract['expected_report_sha256']
    for row in members:
        path = capsule/row['path']
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
        assert f'{stat.S_IMODE(path.stat().st_mode):04o}' == row['mode']
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o555 for path in [capsule,
        *[p for p in capsule.rglob('*') if p.is_dir()]])
    print(json.dumps({'capsule': str(capsule), 'manifest_sha256': sha(manifest_path),
        'report': str(report), 'report_sha256': sha(report), 'members': len(members),
        'runtime_pin': contract['runtime_pin'], 'directory_mode': '0555'}, indent=2))


if __name__ == '__main__':
    main()
