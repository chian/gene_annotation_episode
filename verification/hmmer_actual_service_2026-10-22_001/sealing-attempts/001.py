"""Seal this new partial credential-free evidence generation, without execution.

Only stdlib file reads, comparisons and writes to this publication are used.
No application imports, SQLite connection, service request or phase is performed.
The private cookie is compared in memory and is never printed or persisted.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat


ROOT = Path(__file__).resolve().parent
LIVE = ROOT.parent.parent
REPORT = LIVE / 'docs/HMMER_ACTUAL_SERVICE_VERIFICATION_2026-10-22_001.md'
PIN = '9007ce019b0df13f122cdc53772b45e56684a39755b2e79c9027de2a451fbd1c'
COMMAND = ('/home/chia/repos/gene_annotation_episode/.venv/bin/python -B '
           'verification/hmmer_actual_service_2026-10-22_001/seal_publication.py')


def descriptor(path):
    body = path.read_bytes()
    return {'sha256': hashlib.sha256(body).hexdigest(), 'size': len(body)}


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def files(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        assert not path.is_symlink(), 'A publication/custody symlink was found'
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = descriptor(path)
    return result


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)


def redact_headers(value):
    forbidden = {'set-cookie', 'cookie', 'authorization', 'proxy-authorization'}
    if isinstance(value, dict):
        return {key: '<omitted sensitive header>' if key.lower() in forbidden
                else redact_headers(item) for key, item in value.items()}
    if isinstance(value, list):
        if len(value) == 2 and isinstance(value[0], str) and value[0].lower() in forbidden:
            return [value[0], '<omitted sensitive header>']
        return [redact_headers(item) for item in value]
    return value


def main():
    assert ROOT.name == 'hmmer_actual_service_2026-10-22_001'
    assert not (ROOT / 'MANIFEST.json').exists(), 'Already sealed'
    assert REPORT.read_bytes() == (ROOT / 'REPORT.md').read_bytes()
    phase_copy = load(ROOT / 'PHASE_COPY.json')
    phase_source = Path(phase_copy['source'])
    assert files(ROOT / 'phase-evidence') == phase_copy['files']
    assert {name: descriptor(phase_source / name) for name in phase_copy['files']} == phase_copy['files']
    excluded = {row['path']: {key: row[key] for key in ('sha256', 'size')}
                for row in phase_copy['excluded']}
    assert files(phase_source) == {**phase_copy['files'], **excluded}
    assert not list(ROOT.rglob('*.pyc')) and not list(ROOT.rglob('__pycache__'))

    custody = load(ROOT / 'WORKING_CUSTODY.json')
    working = Path(custody['source'])
    safe = {row['path']: {key: row[key] for key in ('sha256', 'size')}
            for row in custody['safe_original_files']}
    assert files(ROOT / 'working-safe') == safe
    # Hashing original files does not open SQLite or create reader sidecars.
    current_working = files(working)
    assert current_working == custody['after'], 'Working custody changed after its recorded read-only inspection'
    omitted = {row['path']: {key: row[key] for key in ('sha256', 'size')}
               for row in custody['intentionally_omitted']}
    assert custody['before'] == {**safe, **omitted}
    for name in omitted:
        assert not (ROOT / 'working-safe' / name).exists()
    assert all(not path.read_bytes().startswith(b'SQLite format 3\x00')
               for path in ROOT.rglob('*') if path.is_file()), 'A raw SQLite file was published'

    private_values = set()
    for row in custody['derived_files']:
        original = working / row['original_path']
        original_body = original.read_bytes()
        original_value = json.loads(original_body)
        derived = ROOT / row['derived_path']
        value = load(derived)
        assert descriptor(original)['sha256'] == row['original_sha256']
        assert descriptor(derived) == {'sha256': row['derived_sha256'], 'size': row['derived_size']}
        assert value['original_relative_path'] == row['original_path']
        assert value['original_sha256'] == row['original_sha256']
        assert value['original_size'] == len(original_body)
        assert value['derived_value'] == redact_headers(original_value)
        assert value['version'] == 'credential_free_transport_derivative_v1'
        assert descriptor(derived)['sha256'] != row['original_sha256']
        for text in strings(original_value):
            for match in re.finditer(r'(?:^|;\s*)sessionid=([^;]+)', text, flags=re.I):
                private_values.add(match.group(1).encode())
    assert len(private_values) == 1, 'Expected one observed private session value'

    def privacy_scan():
        paths = [path for path in ROOT.rglob('*') if path.is_file()] + [REPORT]
        leaks = [str(path) for path in paths
                 if any(secret in path.read_bytes() for secret in private_values)]
        assert not leaks, 'A private session value was found in a publication output'
        return len(paths)

    scanned = privacy_scan()
    source = load(ROOT / 'SOURCE_IDENTITIES.json')
    checkout = Path(source['checkout'])
    current_sources = {path.relative_to(checkout).as_posix(): descriptor(path)['sha256']
                       for path in sorted((checkout / 'gene_annotation_episode').rglob('*.py'))}
    assert current_sources == source['source_files'] and len(current_sources) == 128
    digest = hashlib.sha256()
    for name, sha in sorted(current_sources.items()):
        digest.update(name.encode())
        digest.update(b'\0')
        digest.update(bytes.fromhex(sha))
    assert digest.hexdigest() == PIN == source['implementation_sha256']
    assert descriptor(ROOT / 'source-identities/ROOT_RESULT_STATE_INPUTS_001.json')['sha256'] == source['frozen_manifest_sha256']
    assert (ROOT / 'scope015.md').read_bytes() == (LIVE / 'docs/HMMER_API_RESOURCE_SCOPE_2026-10-22_015.md').read_bytes()
    validation = load(ROOT / 'VALIDATION.json')
    assert validation['submit_replay_exact'] and validation['all_six_source_guards_match']
    assert validation['public_operation_receipt_count'] == validation['public_capture_count'] == 3
    assert validation['publication_witness_rows'] == 6 and validation['published_record_reference_count'] == 11
    assert validation['raw_result_hits'] == 2 and validation['raw_domains_by_hit'] == [3, 1]
    assert validation['additional_phase_http_model_native_or_scoring_calls_during_publication'] == 0
    save(ROOT / 'PUBLICATION_CHECK.json', {
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'command': COMMAND,
        'command_cwd': str(LIVE),
        'application_imports_sqlite_connections_http_or_phase_calls': 0,
        'report_copy_identical': True,
        'phase_originals_and_copies_verified': len(phase_copy['files']),
        'phase_original_bytes': sum(row['size'] for row in phase_copy['files'].values()),
        'safe_workspace_originals_and_copies_verified': len(safe),
        'safe_workspace_original_bytes': sum(row['size'] for row in safe.values()),
        'intentionally_omitted_preexisting_workspace_files': len(omitted),
        'intentionally_omitted_preexisting_workspace_bytes': sum(row['size'] for row in omitted.values()),
        'redacted_transport_derivatives_verified': len(custody['derived_files']),
        'all_original_private_workspace_bytes_match_recorded_after_inventory': True,
        'private_session_values_compared_in_memory': len(private_values),
        'private_value_emitted_or_persisted': False,
        'outputs_scanned_before_check_and_manifest_creation': scanned,
        'final_full_tree_and_manifest_privacy_scan_required_by_sealing_script': True,
        'published_private_value_occurrences': 0,
        'raw_sqlite_and_compiled_cache_published': False,
        'public_contract_001_metadata_copied': False,
        'source_count_verified': len(current_sources),
        'runtime_implementation_pin_verified': digest.hexdigest(),
        'readonly_publication_file_mode': '0444',
        'readonly_publication_directory_mode': '0555',
        'partial_credential_free_evidence': True,
        'complete_raw_replay_capsule': False,
    })

    members = {name: {**row, 'mode': '0444'} for name, row in files(ROOT).items()}
    manifest = {
        'version': 'hmmer_actual_service_credential_free_publication_v1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'publication_kind': 'Partial credential-free derived evidence',
        'self_excluded_from_members': True,
        'member_count': len(members),
        'member_bytes': sum(row['size'] for row in members.values()),
        'members': members,
        'external_report': {'path': str(REPORT), **descriptor(REPORT), 'mode': '0444'},
        'runtime_implementation_sha256': PIN,
        'source_file_count': 128,
        'private_omissions_and_original_hashes': 'WORKING_CUSTODY.json',
        'derived_transport_original_hash_mapping': 'WORKING_CUSTODY.json',
        'compiled_cache_exclusion': 'PHASE_COPY.json',
        'logical_validation': 'VALIDATION.json',
        'publication_validation': 'PUBLICATION_CHECK.json',
        'limits': [
            'One explicitly selected engineering public phmmer/pdb job; parameters empty; page size two',
            'Only page one of reported two pages acquired and published',
            'Three retained selected public-operation receipts/captures; no server-side physical request count',
            'No configured model, episode/controller, scoring, annotation or biological interpretation',
            'Raw database and credential-bearing originals intentionally omitted; private original references preserved',
            'Not a byte-identical complete database or self-contained replay capsule',
            'Source correction capsule/report002 separately owned and not bundled here',
        ],
    }
    save(ROOT / 'MANIFEST.json', manifest)
    privacy_scan()  # Includes final check and manifest, with no cookie emitted.
    for path in ROOT.rglob('*'):
        if path.is_file():
            path.chmod(0o444)
    REPORT.chmod(0o444)
    for path in sorted((path for path in ROOT.rglob('*') if path.is_dir()),
                       key=lambda path: len(path.parts), reverse=True):
        path.chmod(0o555)
    ROOT.chmod(0o555)
    actual = files(ROOT)
    assert set(actual) == set(members) | {'MANIFEST.json'}
    assert {name: actual[name] for name in members} == {
        name: {key: row[key] for key in ('sha256', 'size')} for name, row in members.items()}
    assert all(stat.S_IMODE(path.stat().st_mode) == (0o555 if path.is_dir() else 0o444)
               for path in [ROOT, *ROOT.rglob('*')])
    assert stat.S_IMODE(REPORT.stat().st_mode) == 0o444
    privacy_scan()
    print(json.dumps({
        'manifest': descriptor(ROOT / 'MANIFEST.json'),
        'report': descriptor(REPORT),
        'member_count_excluding_manifest': len(members),
        'member_bytes_excluding_manifest': manifest['member_bytes'],
        'publication_file_count_including_manifest': len(actual),
        'publication_bytes_including_manifest': sum(row['size'] for row in actual.values()),
        'all_manifest_hashes_sizes_and_readonly_modes_verified': True,
        'private_session_value_occurrences': 0,
        'additional_public_requests_or_phase_calls': 0,
    }, indent=2))


if __name__ == '__main__':
    main()
