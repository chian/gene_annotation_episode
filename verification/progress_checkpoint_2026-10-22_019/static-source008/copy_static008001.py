"""One stdlib-only static preservation invocation; imports no application code."""
from __future__ import annotations

import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import traceback

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/tmp/gene-annotation-configured-caller-20261022-008')
SNAPSHOT = ROOT / 'snapshot'
BASELINE_NAME = 'GENERATION_BASELINE_008.json'
BASELINE_SHA256 = 'c46d6e002b7e33e86aeb22af11aca7e3553b03974ce19d105393aac5ffb8e94b'
SOURCE_SHA256 = '6701ad996646c75e3d64d564cf6d79404e0d03a95a0bba463f145359bb254b30'
OMIT = {'__pycache__', '.pytest_cache'}
EXTRAS = {
    BASELINE_NAME,
    'gene_annotation_episode/direct_hmmer_timing.py',
    'tests/test_direct_hmmer_operation_ports.py',
    'tests/test_direct_hmmer_timing_binding.py',
    'tests/test_direct_hmmer_timing_connected.py',
    'tests/test_direct_hmmer_timing_reconstruction.py',
    'tests/test_direct_hmmer_timing_tools.py',
}
ROOT_TESTS = [
    'tests/test_direct_hmmer_timing_connected.py',
    'tests/test_direct_hmmer_timing_reconstruction.py',
]
SCOPE = Path('/home/chia/repos/gene_annotation_episode/docs/DIRECT_HMMER_TIMING_SCOPE_2026-10-22_001.md')
SCOPE_SHA256 = '1e25a91697a4949bd03d49f3d117b7347e20328beed8311b37ce89cccd7713be'
CONTRACT = Path('/tmp/direct-hmmer-timing-contract-R-20261022-hci0ry6b/CONTRACT001.md')
CONTRACT_SHA256 = '7192312bc549d6fab55d619406f7548b25d34a75ee59ec1959bbf5de4cfbe034'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def metadata(value):
    # atime is deliberately excluded: a read can update it without modifying bytes.
    return {
        'device': value.st_dev,
        'inode': value.st_ino,
        'mode': stat.S_IMODE(value.st_mode),
        'size': value.st_size,
        'mtime_ns': value.st_mtime_ns,
        'ctime_ns': value.st_ctime_ns,
        'nlink': value.st_nlink,
    }


def read_checked(path):
    initial = path.lstat()
    if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
        raise RuntimeError(f'nonregular_or_aliased_file:{path}')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if metadata(initial) != metadata(opened):
            raise RuntimeError(f'open_identity_changed:{path}')
        blocks = []
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            blocks.append(block)
        data = b''.join(blocks)
        final = os.fstat(fd)
    finally:
        os.close(fd)
    if metadata(initial) != metadata(final) or metadata(initial) != metadata(path.lstat()):
        raise RuntimeError(f'file_changed_during_read:{path}')
    if len(data) != initial.st_size:
        raise RuntimeError(f'file_length_changed:{path}')
    return data, metadata(initial)


def inventory(directory, *, omit):
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError(f'invalid_inventory_root:{directory}')
    files = []
    directories = ['.']
    omitted = []
    for base, dirs, names in os.walk(directory, followlinks=False):
        base = Path(base)
        kept = []
        for name in sorted(dirs):
            child = base / name
            relative = str(child.relative_to(directory))
            item = child.lstat()
            if not stat.S_ISDIR(item.st_mode):
                raise RuntimeError(f'non_directory_or_symlink:{child}')
            if name in omit:
                omitted.append(relative)
            else:
                directories.append(relative)
                kept.append(name)
        dirs[:] = kept
        for name in sorted(names):
            child = base / name
            relative = str(child.relative_to(directory))
            item = child.lstat()
            if not stat.S_ISREG(item.st_mode) or item.st_nlink != 1:
                raise RuntimeError(f'nonregular_or_aliased_file:{child}')
            files.append(relative)
    return sorted(files), sorted(directories), sorted(omitted)


def write_new(path, data, *, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(data)
            stream.flush()
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path, value):
    write_new(path, (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())


def pin(rows):
    value = hashlib.sha256()
    selected = [row for row in rows if row['relative_path'].endswith('.py')
                and row['relative_path'].split('/')[0] in {'gene_annotation_episode', 'method_loop'}]
    for row in sorted(selected, key=lambda item: item['relative_path']):
        value.update(row['relative_path'].encode() + b'\0')
        value.update(bytes.fromhex(row['sha256']))
    return {'file_count': len(selected), 'sha256': value.hexdigest()}


def main():
    started = now()
    baseline_bytes, _ = read_checked(SOURCE / BASELINE_NAME)
    if digest(baseline_bytes) != BASELINE_SHA256:
        raise RuntimeError('baseline_digest_mismatch')
    baseline = json.loads(baseline_bytes)
    originals = {item['relative_path'] for item in baseline['files']}
    if len(originals) != 700 or originals & EXTRAS:
        raise RuntimeError('baseline_inventory_mismatch')
    expected = originals | EXTRAS
    if len(expected) != 707:
        raise RuntimeError('expected_inventory_mismatch')
    before_names, before_dirs, before_omitted = inventory(SOURCE, omit=OMIT)
    if set(before_names) != expected:
        raise RuntimeError('source_membership_mismatch')
    before = []
    for name in before_names:
        data, facts = read_checked(SOURCE / name)
        before.append({'relative_path': name, 'bytes': len(data), 'sha256': digest(data), 'stat': facts})
    runtime = pin(before)
    if runtime != {'file_count': 138, 'sha256': SOURCE_SHA256}:
        raise RuntimeError('runtime_source_pin_mismatch')
    write_json(ROOT / 'SOURCE_BEFORE001.json', {
        'version': 'static_source_guard_v1', 'directory': str(SOURCE),
        'files': before, 'directories': before_dirs, 'omitted_directories': before_omitted,
        'runtime': runtime,
    })
    # Preserve complete adopted engineering scope/contract as controls, separate
    # from the exact 707 checkout files. No active run or fixture is consulted.
    authorities = []
    for source, expected_hash, name in [
        (SCOPE, SCOPE_SHA256, 'ADOPTED_SCOPE001.md'),
        (CONTRACT, CONTRACT_SHA256, 'ADOPTED_CONTRACT001.md'),
    ]:
        data, source_stat = read_checked(source)
        if digest(data) != expected_hash:
            raise RuntimeError(f'authority_digest_mismatch:{source}')
        write_new(ROOT / name, data)
        authorities.append({'source_path': str(source), 'copy_path': name,
                            'bytes': len(data), 'sha256': digest(data), 'source_stat': source_stat})
    os.mkdir(SNAPSHOT, 0o700)
    for name in before_dirs:
        if name != '.':
            (SNAPSHOT / name).mkdir(mode=0o700)
    copies = []
    for item in before:
        name = item['relative_path']
        data, source_stat = read_checked(SOURCE / name)
        if source_stat != item['stat'] or digest(data) != item['sha256']:
            raise RuntimeError(f'source_changed_before_copy:{name}')
        target = SNAPSHOT / name
        write_new(target, data)
        # Preserve original executable bits; never write permission or special bits.
        copied_mode = (item['stat']['mode'] & 0o111) | 0o444
        os.chmod(target, copied_mode)
        copied_data, copied_stat = read_checked(target)
        if digest(copied_data) != item['sha256'] or len(copied_data) != item['bytes']:
            raise RuntimeError(f'copy_verification_failed:{name}')
        if copied_stat['mode'] != copied_mode or copied_stat['inode'] == item['stat']['inode']:
            raise RuntimeError(f'copy_mode_or_identity_mismatch:{name}')
        copies.append({**item, 'source_path': str(SOURCE / name),
                       'copied_relative_path': 'snapshot/' + name,
                       'copied_stat': copied_stat, 'copied_mode': copied_mode})
    after_names, after_dirs, after_omitted = inventory(SOURCE, omit=OMIT)
    if before_names != after_names or before_dirs != after_dirs:
        raise RuntimeError('source_membership_changed_during_copy')
    after = []
    for name in after_names:
        data, facts = read_checked(SOURCE / name)
        after.append({'relative_path': name, 'bytes': len(data), 'sha256': digest(data), 'stat': facts})
    if before != after:
        raise RuntimeError('source_hash_or_stat_changed_during_copy')
    write_json(ROOT / 'SOURCE_AFTER001.json', {
        'version': 'static_source_guard_v1', 'directory': str(SOURCE),
        'files': after, 'directories': after_dirs, 'omitted_directories': after_omitted,
        'runtime': pin(after),
    })
    copy_names, copy_dirs, copy_omitted = inventory(SNAPSHOT, omit=set())
    if copy_names != before_names or copy_dirs != before_dirs or copy_omitted:
        raise RuntimeError('copied_membership_mismatch')
    for name in sorted(copy_dirs, key=lambda value: (value.count('/'), value), reverse=True):
        os.chmod(SNAPSHOT if name == '.' else SNAPSHOT / name, 0o555)
    for name in copy_dirs:
        if stat.S_IMODE((SNAPSHOT if name == '.' else SNAPSHOT / name).stat().st_mode) != 0o555:
            raise RuntimeError(f'copied_directory_mode_mismatch:{name}')
    originals_by_name = {item['relative_path']: item for item in baseline['files']}
    changes = [{'relative_path': item['relative_path'],
                'baseline_sha256': originals_by_name[item['relative_path']]['sha256'],
                'current_sha256': item['sha256']}
               for item in before if item['relative_path'] in originals_by_name
               and item['sha256'] != originals_by_name[item['relative_path']]['sha256']]
    manifests = {
        'version': 'direct_hmmer_008_static_source_snapshot_v1',
        'status': 'static_source_snapshot_not_validation',
        'source_directory': str(SOURCE), 'snapshot_directory': str(SNAPSHOT),
        'started_at_utc': started, 'finished_at_utc': now(),
        'baseline': {'path': str(SOURCE / BASELINE_NAME), 'sha256': BASELINE_SHA256,
                     'original_file_count': 700},
        'runtime': runtime, 'file_count': len(copies),
        'total_file_bytes': sum(item['bytes'] for item in copies),
        'directory_count': len(copy_dirs), 'copied_directory_mode': 0o555,
        'copied_file_mode_counts': dict(collections.Counter(str(item['copied_mode']) for item in copies)),
        'expected_additions': sorted(EXTRAS), 'changed_originals': changes,
        'files': copies, 'directories': copy_dirs,
        'current_root_tests': [item for item in before if item['relative_path'] in ROOT_TESTS],
        'new_direct_tests': [item for item in before if item['relative_path'] in EXTRAS
                             and item['relative_path'].startswith('tests/')],
        'source_before_after_hash_stat_and_membership_equal': True,
        'source_stat_fields': list(before[0]['stat']),
        'atime_compared': False,
        'atime_limit': 'Read access may update atime; byte/stat checks exclude atime only.',
        'source_mutations_or_chmod': 0, 'application_imports_or_calls': 0,
        'database_opens': 0, 'test_runs': 0, 'model_service_native_control_calls': 0,
        'aliases_or_special_files': [], 'omitted_directory_names': sorted(OMIT),
        'before_observed_omitted_directories': before_omitted,
        'after_observed_omitted_directories': after_omitted,
        'authorities': authorities,
        'validation_limit': 'This preserves static source only. Separate test results are not established by copying.',
        'external_root_result_reference': {
            'json': '/tmp/direct-hmmer-root008-evidence-20261022-001/invocation-004/RESULTS.json',
            'xml': '/tmp/direct-hmmer-root008-evidence-20261022-001/invocation-004/results.xml',
            'status': 'separately_reported_not_reexecuted_or_adjudicated_here',
        },
    }
    write_json(ROOT / 'SOURCE_MANIFEST001.json', manifests)
    print(json.dumps({key: manifests[key] for key in (
        'status', 'snapshot_directory', 'runtime', 'file_count', 'total_file_bytes',
        'directory_count', 'copied_file_mode_counts', 'current_root_tests',
        'source_before_after_hash_stat_and_membership_equal')}, sort_keys=True), flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        failure = {
            'version': 'static_source_snapshot_failure_v1',
            'status': 'failed_partial_preserved', 'at_utc': now(),
            'exception_type': type(error).__name__, 'error': str(error),
            'traceback': traceback.format_exc(), 'snapshot': str(SNAPSHOT),
            'source_mutations_or_chmod': 0,
        }
        try:
            write_json(ROOT / 'FAILURE001.json', failure)
        finally:
            traceback.print_exc()
        raise SystemExit(1)
