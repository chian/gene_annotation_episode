"""Root identity/coverage verification of the frozen066 no-model package.

Reads only code, sealed metadata and runtime dependency files; scientific input
files are hashed without decoding. Does not rerun model or scientific checks.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
DELIVERY = BASE / 'literature_contract_profile_model_run_063'
PIN = DELIVERY / 'pin_001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)


def main():
    manifest_path = DELIVERY / 'MANIFEST_001.json'
    assert sha(manifest_path) == 'c8f52688fd037baec3cf5c89e6d68cc80f7cd311a9da64d6ddb709cb694abbaa'
    payloads = json.loads(manifest_path.read_bytes())['files']
    for name, expected in payloads.items():
        path = DELIVERY / name
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert path.resolve().is_relative_to(DELIVERY)
        assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'], name
    actual = {str(path.relative_to(DELIVERY)) for path in DELIVERY.rglob('*') if path.is_file()}
    assert actual == set(payloads) | {'MANIFEST_001.json', 'SHA256SUMS_001.txt'}
    checksums = {}
    for line in (DELIVERY / 'SHA256SUMS_001.txt').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert name not in checksums
        checksums[name] = digest
    assert checksums == {**{name: row['sha256'] for name, row in payloads.items()}, 'MANIFEST_001.json': sha(manifest_path)}
    before = json.loads((DELIVERY / 'verification_001/CONTRACT_SNAPSHOT_ACCEPTED_001.json').read_bytes())
    after = json.loads((DELIVERY / 'verification_001/CONTRACT_SNAPSHOT_NEW_001.json').read_bytes())
    compared = ('scope', 'descriptor', 'operations', 'returns', 'invalid_feedback', 'saved_exchange_probe',
        'descriptor_modules_imported', 'models', 'controller', 'scientific_progress', 'restoration',
        'local_jobs', 'disabled_model_entrypoints', 'attempted_model_entrypoints')
    for key in compared:
        assert canonical(before[key]) == canonical(after[key]), key
    assert len(after['operations']) == 19 and len(after['returns']) == 18
    for name, row in after['returns'].items():
        assert row['compact_result']['expanded_schema'] == row['literal_result']['expanded_schema'] == row['literal'], name
        assert len(row['compact_result']['declaration']['fact_references']) == 1
        assert row['literal_result']['declaration']['fact_references'] == []
    assert {row['module']: row['sha256'] for row in before['actual_project_imports']} == {
        row['module']: row['sha256'] for row in after['actual_project_imports']}
    assert len(after['actual_project_imports']) == 142
    for value in after['saved_exchange_probe'].values():
        assert value is True or isinstance(value, str)
    dependencies_path = DELIVERY / 'RUNTIME_DEPENDENCIES_002.json'
    assert sha(dependencies_path) == '626dd90a325e8c8fa416fc9ea5c9ab63667719eb6815b0a6beac828f821915cb'
    dependencies = json.loads(dependencies_path.read_bytes())
    project = {row['module']: row for row in dependencies['actual_project_imports']}
    assert len(project) == 160
    new_pin = {row['pin_relative_path']: row for row in json.loads((PIN / 'SOURCE_MANIFEST.json').read_bytes())['files']}
    for row in project.values():
        path = Path(row['path'])
        assert path.is_relative_to(PIN)
        expected = new_pin[str(path.relative_to(PIN))]
        assert row['bytes'] == expected['size'] and row['sha256'] == expected['sha256'] == sha(path)
    reconstruction = json.loads((DELIVERY / 'verification_001/DESCRIPTOR_RECONSTRUCTION_002.json').read_bytes())
    for row in [*after['actual_project_imports'], *reconstruction['actual_project_imports']]:
        assert project[row['module']] == row
    assert reconstruction['complete_composition_descriptor_equal'] is True
    assert reconstruction['saved_factory_descriptor_equal'] is True
    assert reconstruction['substituted_implementation_rejected'] is True
    bound = [dependencies[key] for key in ('resolved_interpreter', 'pyvenv_cfg', 'configured_executable')]
    bound.extend(dependencies['actually_loaded_external_module_files'])
    bound.extend(row for distribution in dependencies['installed_distributions'] for row in distribution['files'])
    for row in bound:
        path = Path(row['path'])
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], row['path']
    assert len(bound) == 4274
    old_dependencies = json.loads((DELIVERY / 'RUNTIME_DEPENDENCIES_001.json').read_bytes())
    for key in ('actually_loaded_external_module_files', 'installed_distributions', 'resolved_interpreter',
                'pyvenv_cfg', 'configured_executable'):
        assert dependencies[key] == old_dependencies[key], key
    worker = json.loads((DELIVERY / 'verification_001/WORKER_IMPORT_PROBE_002.json').read_bytes())
    assert worker['exit_code'] == 0 and len(worker['actual_paths']) == 4
    assert all(Path(path).is_relative_to(PIN) for path in worker['actual_paths'])
    assert not dependencies['attempted_model_entrypoints'] and not after['attempted_model_entrypoints']
    assert not any((DELIVERY / name).exists() for name in ('live_001', 'preparation_001'))
    receipt = json.loads((DELIVERY / 'PRELAUNCH_METADATA_RECEIPT_001.json').read_bytes())
    assert sha(DELIVERY / 'PRELAUNCH_METADATA_RECEIPT_001.json') == '831d7e9611c24437c4df772de1b4626ed2fb5614fb2e11bc0eeedba3a88bbd62'
    assert receipt['source_registration'] is False and receipt['source_inputs_decoded'] is False
    assert receipt['runtime_actions'] == receipt['runtime_observations'] == receipt['provider_entries'] == 0
    result = {'scope': 'Root accepts bounded metadata/import/contract preparation only; actual scientific/model work unproved',
        'sealed_payloads_verified': len(payloads), 'sha_lines_verified': len(checksums), 'no_extra_files': True,
        'exact_cross_pin_contract_operations': 19, 'exact_cross_pin_return_projections': 18,
        'compact_literal_pairs_per_snapshot': 18, 'matching_snapshot_project_imports': 142,
        'bound_project_imports': len(project), 'bound_external_file_rows_reverified': len(bound),
        'installed_distributions': len(dependencies['installed_distributions']),
        'loaded_external_module_files': len(dependencies['actually_loaded_external_module_files']),
        'binding002_external_rows_identical_to001': True, 'safe_path_worker_imports': 4,
        'actual_descriptor_reconstruction_checks_inspected': True,
        'root_application_imports_this_verifier': 0, 'root_model_calls': 0,
        'scientific_input_decoding': False, 'real_c1_c4_delivery_proved': False,
        'next': 'Existing pinned offline source registration and prospective JOB/TASK review; no model launch yet',
        'manifest_sha256': sha(manifest_path), 'dependency_binding_sha256': sha(dependencies_path)}
    with (HERE / 'METADATA_DELIVERY_ROOT_RECEIPT_004.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('sealed_payloads_verified', 'exact_cross_pin_contract_operations',
        'exact_cross_pin_return_projections', 'bound_project_imports', 'bound_external_file_rows_reverified',
        'root_model_calls', 'real_c1_c4_delivery_proved')}))


if __name__ == '__main__':
    main()
