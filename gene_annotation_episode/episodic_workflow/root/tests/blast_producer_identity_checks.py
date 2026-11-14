"""Retained manifest/proof readers and controlled running-module checks.

The retained bundle is copied verbatim from the existing native6 fixture. Live
producer checks use controlled inventory/file-check ports and actual loaded
module paths. They do not execute BLAST or establish deployment file validity.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

OLD = 'gene_annotation_episode.episodic_workflow.root.library.native_blast_database_driver'
NEW = 'gene_annotation_episode.episodic_workflow.root.library.native_blast_database_driver'
ORIGINAL_CASES = ('historical_manifest', 'historical_producer_proof',
    'historical_missing_driver', 'historical_changed_check_rejected',
    'unknown_entry_rejected', 'runtime_self')
CASES = (*ORIGINAL_CASES, 'current_manifest', 'current_missing_driver',
         'mixed_current_entry_rejected', 'mixed_old_entry_rejected', 'runtime_wrong_entry')


def retained():
    return json.loads((Path(__file__).parent /
        'fixtures/blast_producer_identity/original_native6_bundle.json').read_bytes())


def manifest(entry=OLD):
    value = deepcopy(retained()['producer_verification']['manifest'])
    value['entry_module'] = entry
    if entry == NEW:
        for row in value['package_files']:
            if row['relative_path'] in ('gene_annotation_episode/native_blast_database_driver.py',
                                        'gene_annotation_episode/native_blast_database_contracts.py'):
                row['relative_path'] = row['relative_path'].replace('gene_annotation_episode/',
                    'gene_annotation_episode/episodic_workflow/root/library/', 1)
    return value


def validate(contracts, value):
    return contracts.validate_native_blast_database_producer_manifest(value,
        module_root=value['module_root'], python_executable=value['python']['path'])


def reject(function, value, code):
    before = deepcopy(value)
    try:
        function(value)
    except ValueError as error:
        assert code in str(error), (str(error), code)
    else:
        raise AssertionError('invalid producer identity was accepted')
    assert value == before


def verify_record(contracts, bundle):
    artifacts = {row['artifact_key']: row for row in bundle['artifacts']}
    contracts._validate_producer_verification(bundle, artifacts,
        lambda code: any(row['code'] == code for row in bundle['failures']))


def runtime_check(driver, directory, wrong):
    entry = OLD if wrong else driver.__name__
    value = manifest(entry)
    root = Path(driver.__file__).resolve().parents[len(driver.__package__.split('.'))]
    value['module_root'] = str(root)
    value['python']['path'] = str(Path(sys.executable).resolve())
    value['runtime_files'] = []
    # Include both sets of pinned names. Otherwise missing-file validation alone
    # would conceal whether the actual loaded module matches the declared one.
    existing = {row['relative_path'] for row in value['package_files']}
    for row in manifest(NEW)['package_files']:
        if row['relative_path'] not in existing:
            value['package_files'].append(row)
    directory.mkdir()
    source = directory / 'producer.json'
    raw = (json.dumps(value, sort_keys=True) + '\n').encode()
    source.write_bytes(raw)
    attempt = directory / 'attempt'
    attempt.mkdir()
    bundle = {'plan': {'attempt_directory': str(attempt), 'producer_manifest': {
        'path': str(source), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}},
        'producer_verification': {'manifest': None, 'manifest_observed_sha256': None,
            'package_inventory_exact': None, 'running_module_paths_match': None,
            'checks': [], 'status': 'failed'},
        'artifacts': [], 'failures': [], 'process': {'returncode': None}}

    def file_check(expected, *, kind):
        return {'kind': kind, 'path': expected['path'], 'observed_sha256': expected['sha256'],
                'size_bytes': expected['size_bytes'], 'status': 'verified',
                'checked_at': '2026-11-13T00:00:00+00:00'}

    with patch.object(driver, '_inventory', return_value=(
            [root / row['relative_path'] for row in value['package_files']], False)), \
            patch.object(driver, '_check_file', side_effect=file_check), \
            patch.object(driver.subprocess, 'run', side_effect=AssertionError('native work forbidden')), \
            patch.object(driver.subprocess, 'Popen', side_effect=AssertionError('native work forbidden')):
        driver._verify_producer(bundle)
    assert bundle['producer_verification']['manifest'] == value
    assert bundle['producer_verification']['running_module_paths_match'] is (not wrong)
    assert bundle['producer_verification']['status'] == ('failed' if wrong else 'verified')
    assert [row['code'] for row in bundle['failures']] == (
        ['producer_runtime_path_mismatch'] if wrong else [])


def check(name, contracts, driver, work):
    assert name in CASES
    if name.startswith('runtime_'):
        runtime_check(driver, work / name, name == 'runtime_wrong_entry')
    elif name in ('historical_producer_proof', 'historical_changed_check_rejected'):
        value = retained()
        if name == 'historical_changed_check_rejected':
            value['producer_verification']['checks'][0]['observed_sha256'] = 'f' * 64
            reject(lambda value: verify_record(contracts, value), value, 'file_measurement_status_conflict')
        else:
            before = deepcopy(value)
            verify_record(contracts, value)
            assert value == before
    elif name == 'unknown_entry_rejected':
        value = manifest()
        value['entry_module'] = 'gene_annotation_episode.unassigned_driver'
        reject(lambda value: validate(contracts, value), value, 'schema:$.entry_module:')
    else:
        current = name.startswith('current') or name == 'mixed_old_entry_rejected'
        value = manifest(NEW if current else OLD)
        if 'missing_driver' in name:
            value['package_files'] = [row for row in value['package_files']
                if not row['relative_path'].endswith('/native_blast_database_driver.py')]
        elif name == 'mixed_current_entry_rejected':
            value['entry_module'] = NEW
        elif name == 'mixed_old_entry_rejected':
            value['entry_module'] = OLD
        if 'missing_driver' in name or name.startswith('mixed_'):
            reject(lambda value: validate(contracts, value), value, 'producer_required_package_file_missing')
        else:
            before = deepcopy(value)
            result = validate(contracts, value)
            assert result == before == value and result is not value
