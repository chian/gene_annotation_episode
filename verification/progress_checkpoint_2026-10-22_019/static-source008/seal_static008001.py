"""Metadata-only one-time sealing of this new static snapshot and its controls."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import os
import stat
import sys

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / 'snapshot'


def descriptor(path):
    initial = path.lstat()
    assert stat.S_ISREG(initial.st_mode) and initial.st_nlink == 1, path
    data = path.read_bytes()
    final = path.lstat()
    assert (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns,
            initial.st_ctime_ns, initial.st_mode) == (
                final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns,
                final.st_ctime_ns, final.st_mode), path
    assert len(data) == initial.st_size, path
    return {'relative_path': str(path.relative_to(ROOT)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
            'mode': stat.S_IMODE(final.st_mode)}


def write_json(name, value):
    with (ROOT / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def main():
    assert not (ROOT / 'MANIFEST001.json').exists()
    assert not (ROOT / 'SEAL_RESULT001.json').exists()
    manifest = json.loads((ROOT / 'SOURCE_MANIFEST001.json').read_text())
    invocation = json.loads((ROOT / 'INVOCATION001.json').read_text())
    assert invocation['actual_exit_code'] == 0 and invocation['operator_unchanged']
    assert manifest['status'] == 'static_source_snapshot_not_validation'
    assert manifest['file_count'] == 707 and manifest['runtime'] == {
        'file_count': 138,
        'sha256': '6701ad996646c75e3d64d564cf6d79404e0d03a95a0bba463f145359bb254b30',
    }
    expected = {'snapshot/' + item['relative_path']: item for item in manifest['files']}
    actual = [path for path in SNAPSHOT.rglob('*') if path.is_file()]
    assert {str(path.relative_to(ROOT)) for path in actual} == set(expected)
    for path in actual:
        item = descriptor(path)
        saved = expected[item['relative_path']]
        assert (item['bytes'], item['sha256'], item['mode']) == (
            saved['bytes'], saved['sha256'], saved['copied_mode']), path
    dirs = [SNAPSHOT] + [path for path in SNAPSHOT.rglob('*') if path.is_dir()]
    assert len(dirs) == 55
    for path in dirs:
        assert not path.is_symlink() and stat.S_IMODE(path.stat().st_mode) == 0o555, path
    result = {
        'version': 'static_source_snapshot_seal_v1',
        'status': 'static_source_snapshot_not_validation',
        'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'argv': list(sys.argv), 'cwd': os.getcwd(),
        'copied_file_count': 707, 'copied_bytes': sum(item['bytes'] for item in expected.values()),
        'copied_directory_count': 55,
        'copy_mode_counts': dict(collections.Counter(oct(item['copied_mode']) for item in expected.values())),
        'copied_hash_bytes_modes_verified': True,
        'source_hash_stat_membership_equal_during_copy': True,
        'runtime': manifest['runtime'],
        'test_runs_application_imports_database_opens_model_service_native_control_calls': 0,
        'permanent_repo_writes': 0,
    }
    write_json('SEAL_RESULT001.json', result)
    controls = [path for path in ROOT.iterdir() if path != SNAPSHOT]
    for path in controls:
        assert path.is_file() and not path.is_symlink(), path
        os.chmod(path, 0o444)
    all_paths = sorted(path for path in ROOT.rglob('*') if path.is_file())
    members = [descriptor(path) for path in all_paths]
    value = {
        'version': 'static_source_snapshot_outer_manifest_v1',
        'status': 'static_source_snapshot_not_validation',
        'root': str(ROOT), 'self_excluded': 'MANIFEST001.json',
        'member_count': len(members), 'total_file_bytes': sum(item['bytes'] for item in members),
        'snapshot_member_count': 707, 'control_member_count': len(members) - 707,
        'root_and_all_directory_mode': 0o555,
        'runtime': manifest['runtime'],
        'source_manifest': descriptor(ROOT / 'SOURCE_MANIFEST001.json'),
        'current_root_tests': manifest['current_root_tests'],
        'files': members,
        'directories': ['.'] + ['snapshot' if name == '.' else 'snapshot/' + name
                                for name in manifest['directories']],
        'aliases': [],
        'validation_limit': 'Static preservation and byte/mode verification only; no test/app/science execution.',
    }
    write_json('MANIFEST001.json', value)
    os.chmod(ROOT / 'MANIFEST001.json', 0o444)
    # All snapshot directories are already readonly. Seal only this new outer root.
    os.chmod(ROOT, 0o555)
    result_descriptor = descriptor(ROOT / 'MANIFEST001.json')
    assert all(not (path.stat().st_mode & 0o222) for path in ROOT.rglob('*'))
    assert not (ROOT.stat().st_mode & 0o222)
    print(json.dumps({'manifest': result_descriptor,
                      'member_count_excluding_manifest': value['member_count'],
                      'total_files_including_manifest': value['member_count'] + 1,
                      'snapshot_files': 707, 'snapshot_bytes': result['copied_bytes'],
                      'controls_excluding_manifest': value['control_member_count'],
                      'directories_including_outer': len(value['directories']),
                      'status': result['status'], 'runtime': manifest['runtime']}, indent=2))


if __name__ == '__main__':
    main()
