"""Copy only fixed review metadata; never dereference paths inside JSON."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

SOURCE = Path('/tmp/configured-resource-actual-verifier-20261022-001-BAWpJPut')
BUNDLE = Path('/tmp/configured-resource-preparation-independent-review-20261022-001-laR09p2B')
CHECKER_SHA = 'f0ade39294e56454002a86c2df3b4aeb0e6ad8aa6d9f8ec80c311b7965423eff'
RESULT_SHA = '764be765e71d3354ca64aa8372f71b7592629b2c9512b5257a38378c765d7964'
PIN = '3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'


def require(value, message):
    if not value:
        raise ValueError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def meta(s):
    return {'mode': format(stat.S_IMODE(s.st_mode), '04o'), 'bytes': s.st_size,
            'mtime_ns': s.st_mtime_ns, 'inode': s.st_ino, 'device': s.st_dev}


def no_links(path):
    require(path.is_absolute() and '..' not in path.parts, 'fixed absolute path required')
    for p in (path, *path.parents):
        require(not p.is_symlink(), 'symlink rejected: ' + str(p))


def read_regular(path):
    no_links(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), 'regular file required')
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            data = handle.read()
        after = os.fstat(fd)
        require(meta(before) == meta(after), 'file changed while read')
    finally:
        os.close(fd)
    require(meta(path.lstat()) == meta(after), 'path changed while read')
    return data, {'sha256': sha(data), **meta(after)}


def snapshot(root):
    no_links(root)
    regular, directories = {}, {}
    root_meta = meta(root.lstat())

    def visit(parent):
        with os.scandir(parent) as entries:
            rows = sorted(entries, key=lambda entry: entry.name)
        for entry in rows:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            mode = entry.stat(follow_symlinks=False).st_mode
            if stat.S_ISDIR(mode):
                directories[relative] = meta(path.lstat())
                visit(path)
            elif stat.S_ISREG(mode):
                regular[relative] = read_regular(path)[1]
            else:
                raise ValueError('nonregular/symlink member rejected without following: ' + relative)

    visit(root)
    return {'root': root_meta, 'directories': directories, 'regular_members': regular, 'aliases': []}


def save(path, value, mode=0o444):
    data = value if isinstance(value, bytes) else canonical(value) + b'\n'
    no_links(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, mode)
    return read_regular(path)[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args()
    require(args.source == SOURCE and args.bundle == BUNDLE, 'exact fixed metadata roots required')
    require({p.name for p in BUNDLE.iterdir()} == {'SEAL_METADATA001.py'}, 'fresh bundle required')
    started = utc()
    before = snapshot(SOURCE)
    require(len(before['regular_members']) == 16 and set(before['directories']) == {'history'}, 'exact authoring tree')
    require(before['regular_members']['verify_resource_preparation001.py']['sha256'] == CHECKER_SHA,
            'held checker identity')
    require(before['regular_members']['VERIFICATION_ACTUAL001.json']['sha256'] == RESULT_SHA,
            'root actual result identity')
    target = BUNDLE / 'authoring'
    target.mkdir(mode=0o700)
    for relative in sorted(before['directories'], key=lambda name: (name.count('/'), name)):
        (target / relative).mkdir(mode=0o700)
    copies = []
    for relative, row in before['regular_members'].items():
        data, current = read_regular(SOURCE / relative)
        require(current == row, 'source changed before copy')
        mode = int(row['mode'], 8) & ~0o222
        copied = save(target / relative, data, mode)
        require(copied['sha256'] == row['sha256'] and copied['bytes'] == row['bytes'], 'copy bytes differ')
        copies.append({'source': str(SOURCE / relative), 'member': 'authoring/' + relative,
                       'sha256': row['sha256'], 'bytes': row['bytes'],
                       'source_mode': row['mode'], 'copied_mode': copied['mode'],
                       'byte_copy_equal': True, 'only_write_mode_bits_removed': True})
    result_bytes, _ = read_regular(target / 'VERIFICATION_ACTUAL001.json')
    result = json.loads(result_bytes)
    require(result['status'] == 'verified_prepared_not_started'
            and result['source_pin'] == {'sha256': PIN, 'file_count': 137}
            and result['external_preparation_exit_code'] == 0
            and result['selected_inputs_unchanged'] is True and len(result['witnesses']) == 688,
            'actual saved result does not match root handoff')
    checks = {row['check']: row for row in result['checks']}
    require(checks['fresh_reference_union']['selected'] == 198
            and checks['fresh_reference_union']['final'] == 200
            and checks['NEW_native_registry_SQL']['counts'] == {'orders': 0, 'handoffs': 0, 'samples': 0},
            'saved prepared-state relationships differ')
    after = snapshot(SOURCE)
    require(before == after, 'original authoring tree changed')
    argv = ['/usr/bin/python3', '-B', str(SOURCE / 'verify_resource_preparation001.py'),
            '--preparation-invocation', '/tmp/configured-resource-investigation-root-preparation-20261022-001/INVOCATION001.json',
            '--output', str(SOURCE / 'VERIFICATION_ACTUAL001.json')]
    save(BUNDLE / 'SCOPE001.md', b'''This new standalone review bundle contains only byte copies of the independent resource preparation verifier authoring tree and root's saved successful verifier result, plus sealing metadata. Original authoring files remain unchanged. No database, application, model, provider, service, native program or test is invoked or reopened. JSON witness paths are retained as strings and never traversed by this sealer. The checker execution was root-owned; this seal is metadata custody, not a new verification or scientific execution.\n''')
    save(BUNDLE / 'ROOT_EXECUTION001.json', {
        'version': 'root_resource_verifier_execution_message_attestation_v1',
        'execution_owner': '/root', 'provenance': 'explicit root collaboration messages',
        'root_reported_execution_count': 1, 'argv': argv,
        'cwd': '/home/chia/repos/gene_annotation_episode', 'exit_code': 0,
        'status': 'verified_prepared_not_started', 'checker_sha256': CHECKER_SHA,
        'result_sha256': RESULT_SHA, 'result_member': 'authoring/VERIFICATION_ACTUAL001.json',
        'initial_message_abbreviated_checker_basename': 'verify_resource_preparation001.py',
        'root_explicit_correction': 'Actual argv used the absolute checker path and cwd shown above; the initial message was an abbreviation.',
        'start_finish_timestamps': None, 'timestamp_limit': 'Root did not supply checker subprocess start/finish timestamps.',
        'independent_checker_process_receipt_supplied': False,
        'limit': 'Execution count/argv/cwd/exit are root attestation; result hash/status are independently checked in copied JSON. No exhaustive process census inferred.'})
    save(BUNDLE / 'COPY_CONTROLS001.json', {
        'version': 'resource_verifier_review_exact_copy_controls_v1', 'source_root': str(SOURCE),
        'destination_prefix': 'authoring/', 'before': before, 'after': after,
        'original_tree_unchanged': True, 'copies': copies, 'copied_regular_members': len(copies),
        'copied_regular_bytes': sum(row['bytes'] for row in copies), 'aliases': [],
        'mode_policy': 'Remove write bits in copies only; preserve all original modes in before/after controls. Original files receive no writes or chmod.',
        'external_paths_inside_JSON': 'Retained as uninterpreted strings, never opened or followed.'})
    save(BUNDLE / 'RESULTS_FINAL001.json', {
        'version': 'sealed_independent_resource_preparation_review_v1',
        'status': 'root_verified_prepared_not_started_metadata_sealed',
        'execution_owner': '/root', 'root_reported_checker_executions': 1,
        'sealer_checker_executions': 0, 'sealer_SQL_connections': 0,
        'checker_sha256': CHECKER_SHA, 'actual_result_sha256': RESULT_SHA,
        'result_member': 'authoring/VERIFICATION_ACTUAL001.json', 'source_pin': result['source_pin'],
        'actual_result_witnesses': len(result['witnesses']), 'actual_result_selected_inputs_unchanged': True,
        'fresh_reference_union': checks['fresh_reference_union'],
        'native_registry_counts_at_root_review': checks['NEW_native_registry_SQL']['counts'],
        'inherited_runtime_counts_at_root_review': {key: checks['NEW_checkpoint_SQL']['table_counts'][key]
            for key in ('runtime_runs', 'runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls')},
        'static_policy_remainder_sha256': checks['exact_parameters_and_configuration']['static_policy_remainder_sha256'],
        'authoring_note_classification': 'Future output absence assertion raced with root creating actual result; not preparation/checker failure. Original note and preconfirmation handoff remain unchanged.',
        'copy_regular_members': len(copies), 'copy_regular_bytes': sum(row['bytes'] for row in copies),
        'original_authoring_tree_unchanged': True,
        'limits': result['limits'] + [
            'Sealing only reads authoring files and saved result JSON; no recorded database or external witness path is reopened.',
            'Bundle contains checker/result/authoring provenance; external raw caller inputs and databases are described by the saved result, not recopied.',
            'Prepared-state evidence is historical at root review time; no present liveness or launch-state assertion is added.',
            'Root execution attestation is explicit; this seal does not independently observe the subprocess or rerun verification.']})
    save(BUNDLE / 'README001.md', b'''Root ran the held final f0ade verifier once and reported exit0/verified_prepared_not_started. Its exact result764be is copied unchanged under authoring/, together with the complete checker, scope, preserved drafts, diffs, finite static readset and authoring metadata. ROOT_EXECUTION001.json retains root's explicit correction from abbreviated basename to actual absolute argv and cwd. Initial AUTHORING_READY/FINAL_REVIEW were written before execution confirmation and remain historical; ROOT_EXECUTION/RESULTS_FINAL give the confirmed execution ownership. AUTHORING_NOTE records only a metadata assertion when root's output already existed. It is not an application/checker failure.\n\nCOPY_CONTROLS001 records exact source before/after hashes, bytes, modes, mtime, inode and device plus byte-equal copies. Only copy write bits are removed. The original authoring tree is unchanged. No external path contained in JSON is followed. No database or application call occurs during sealing. Saved179/175/180 counts are inherited custody, while native0 is the root review snapshot; preparation is not scientific behavior or whole-goal completion.\n''')
    save(BUNDLE / 'SEAL_EXECUTION001.json', {
        'version': 'resource_verifier_metadata_seal_execution_v1', 'status': 'completed_metadata_only',
        'argv': [sys.executable, '-B', str(BUNDLE / 'SEAL_METADATA001.py'), *sys.argv[1:]],
        'cwd': str(Path.cwd()), 'started_at_utc': started, 'finished_at_utc': utc(),
        'original_regular_members': len(copies), 'original_after_equal_before': True,
        'SQL_connections': 0, 'checker_executions': 0, 'application_calls': 0,
        'original_json_witness_paths_dereferenced': 0})
    # Seal only new bundle paths. Source modes and bytes remain untouched.
    for parent, directories, files in os.walk(BUNDLE, topdown=False):
        for name in files:
            path = Path(parent) / name
            os.chmod(path, stat.S_IMODE(path.lstat().st_mode) & ~0o222)
        for name in directories:
            os.chmod(Path(parent) / name, 0o555)
    members, directories = [], []
    for path in sorted(BUNDLE.rglob('*')):
        relative = path.relative_to(BUNDLE).as_posix()
        if path.is_dir():
            directories.append({'path': relative, 'mode': format(stat.S_IMODE(path.lstat().st_mode), '04o')})
        else:
            data, row = read_regular(path)
            members.append({'path': relative, 'sha256': row['sha256'], 'bytes': row['bytes'], 'mode': row['mode']})
    manifest = {
        'version': 'sealed_resource_preparation_independent_review_manifest_v1',
        'root': str(BUNDLE), 'root_mode': '0555', 'regular_members': members,
        'regular_member_count': len(members), 'regular_member_bytes': sum(row['bytes'] for row in members),
        'directories': directories, 'aliases': [], 'alias_count': 0,
        'self_excluded': 'MANIFEST_FINAL001.json', 'source_originals_unchanged': True,
        'checker_sha256': CHECKER_SHA, 'actual_result_sha256': RESULT_SHA}
    manifest_row = save(BUNDLE / 'MANIFEST_FINAL001.json', manifest)
    os.chmod(BUNDLE, 0o555)
    expected = {row['path'] for row in members} | {'MANIFEST_FINAL001.json'}
    require({path.relative_to(BUNDLE).as_posix() for path in BUNDLE.rglob('*') if path.is_file()} == expected,
            'final bundle regular membership')
    for row in members:
        _, actual = read_regular(BUNDLE / row['path'])
        require(all(actual[key] == row[key] for key in ('sha256', 'bytes', 'mode')), 'final bundle changed')
    require(snapshot(SOURCE) == before, 'original authoring tree changed before seal completed')
    print(json.dumps({'bundle': str(BUNDLE), 'manifest_sha256': manifest_row['sha256'],
        'regular_members_excluding_manifest': len(members), 'regular_bytes_excluding_manifest': manifest['regular_member_bytes'],
        'copied_regular_members': len(copies), 'copied_regular_bytes': sum(row['bytes'] for row in copies),
        'result_sha256': RESULT_SHA, 'checker_sha256': CHECKER_SHA, 'aliases': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
