"""Recheck frozen code/dependencies without entering application or source work."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DELIVERY = HERE.parent / 'literature_contract_profile_model_run_063'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = DELIVERY / 'MANIFEST_001.json'
    assert digest(manifest_path) == 'c8f52688fd037baec3cf5c89e6d68cc80f7cd311a9da64d6ddb709cb694abbaa'
    manifest = json.loads(manifest_path.read_bytes())['files']
    for name, row in manifest.items():
        path = DELIVERY / name
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert path.resolve().is_relative_to(DELIVERY)
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    assert {str(p.relative_to(DELIVERY)) for p in DELIVERY.rglob('*') if p.is_file()} == set(manifest) | {'MANIFEST_001.json', 'SHA256SUMS_001.txt'}
    dependency_path = DELIVERY / 'RUNTIME_DEPENDENCIES_002.json'
    assert digest(dependency_path) == '626dd90a325e8c8fa416fc9ea5c9ab63667719eb6815b0a6beac828f821915cb'
    dependencies = json.loads(dependency_path.read_bytes())
    bound = [dependencies[k] for k in ('resolved_interpreter', 'pyvenv_cfg', 'configured_executable')]
    bound.extend(dependencies['actually_loaded_external_module_files'])
    bound.extend(row for distribution in dependencies['installed_distributions'] for row in distribution['files'])
    for row in bound:
        path = Path(row['path'])
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], row['path']
    pin = DELIVERY / 'pin_001'
    source_manifest = pin / 'SOURCE_MANIFEST.json'
    assert digest(source_manifest) == 'b09dfaa37615ab6f9ff02a18fd864d0c696a59ee11622cdf039a5c4a3319ef9c'
    for row in dependencies['actual_project_imports']:
        path = Path(row['path'])
        assert path.resolve().is_relative_to(pin)
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
    reset = json.loads((HERE / 'task_review_006/RESET_READ_RECEIPT_006.json').read_bytes())
    assert reset['completed_after_packet'] == 24 and reset['latest_human_read_last'] is True
    for row in reset['reset_files'] + reset['packet_complete_reads']:
        assert digest(Path(row['path'])) == row['sha256'], row['path']
    assert not (HERE / 'live_007').exists()
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'passed',
        'sealed_payloads': len(manifest), 'bound_external_rows': len(bound),
        'bound_project_imports': len(dependencies['actual_project_imports']),
        'source_manifest_sha256': digest(source_manifest), 'manifest_sha256': digest(manifest_path),
        'dependency_binding_sha256': digest(dependency_path), 'reset_files': 24,
        'scientific_inputs_hashed_only': True, 'application_imports': 0,
        'model_calls': 0, 'state_mutation': False, 'next': 'Unchanged configured runner in new root-owned live_007 directory'}
    with (HERE / 'PRELAUNCH_ROOT_RECEIPT_007.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
