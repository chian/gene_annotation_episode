"""Copy an explicit metadata allowlist; never open a SQLite database or app."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import stat

HERE = Path(__file__).resolve().parent
RUN = Path('/home/chia/gene_annotation_episode_runs/configured_resource_investigation_001')
OPERATOR = Path('/tmp/configured-resource-investigation-preparation-20261022-001')
ROOT = Path('/tmp/configured-resource-investigation-root-preparation-20261022-001')
STATIC = Path('/tmp/configured-resource-caller-preparation-20261022-001-U7WRRlHE')

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def read_bytes(path):
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('symlink_source')
    if path.suffix in {'.sqlite', '.sqlite3', '.db'} or path.name.endswith(('-wal', '-shm')):
        raise ValueError('database_or_sidecar_excluded')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode):
            raise ValueError('regular_file_required')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read()
        return raw, {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw), 'mode': oct(stat.S_IMODE(s.st_mode)),
            'device': s.st_dev, 'inode': s.st_ino}
    finally:
        os.close(fd)

def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def main():
    start = datetime.now(timezone.utc).isoformat()
    mapping = {}
    caller = ['C_REQUEST001.json', 'C_RESULT001.json', 'C_VERIFICATION001.json',
        'EXPECTED_HANDOFF001.json', 'OPERATOR_INPUTS001.json', 'PARAMETER_TEMPLATE001.json',
        'PREPARATION_RESULT001.json', 'PREPARE_RESULT001.json', 'SCHEMAS004.json',
        'config.toml', 'focus.txt', 'parameters.json']
    for name in caller:
        mapping['run/caller-inputs/' + name] = RUN / 'caller-inputs' / name
    for name in ['case-launch.json', 'workspace/scientific-checkpoint-fork.json',
            'workspace/checkpoint/tables.json', 'workspace/checkpoint/artifacts.json',
            'workspace/checkpoint/committed-references.json',
            'workspace/checkpoint/source-implementation-files.json',
            'native-jobs/configuration.json']:
        mapping['run/' + name] = RUN / name
    for name in ['OPERATOR_EXECUTION_FINISHED001.json', 'OPERATOR_EXECUTION_STARTED001.json',
            'RESULTS001.json', 'SOURCE_AFTER_C001.json', 'SOURCE_AFTER_PREPARE001.json',
            'SOURCE_BEFORE001.json']:
        mapping['operator-evidence/' + name] = OPERATOR / name
    for name in ['INVOCATION001.json', 'SCOPE001.md', 'STARTED001.json', 'STDERR001.log',
            'STDOUT001.log', 'invoke_once001.py']:
        mapping['root-invocation/' + name] = ROOT / name
    for name in ['MANIFEST_FINAL001.json', 'INPUTS001.json', 'README001.md', 'READSET001.json']:
        mapping['static-packet/' + name] = STATIC / name

    # No application/SQLite import. These comparisons qualify copied metadata,
    # never re-project credit or independently assert the database row contents.
    result = json.loads(read_bytes(OPERATOR / 'RESULTS001.json')[0])
    invocation = json.loads(read_bytes(ROOT / 'INVOCATION001.json')[0])
    finished = json.loads(read_bytes(OPERATOR / 'OPERATOR_EXECUTION_FINISHED001.json')[0])
    assert invocation['exit_code'] == 0 and invocation['status'] == 'exited'
    assert invocation['input_manifest']['sha256'] == 'e398322011562a864f56a24ecc1bfa798854e83f78e96b07132ee04ed3db23f1'
    assert invocation['operator']['sha256'] == '97fb06e0523cb50fefc5c8691819942226668ce2252276cf099089960bde9827'
    assert finished['exit_code'] == 0 and finished['status'] == 'prepared_not_started'
    assert not (OPERATOR / 'FAILURE001.json').exists()
    assert result == json.loads(read_bytes(RUN / 'caller-inputs/PREPARATION_RESULT001.json')[0])
    copied = []
    for relative, original in sorted(mapping.items()):
        raw, before = read_bytes(original)
        save(HERE / relative, raw)
        after_raw, after = read_bytes(original)
        assert after == before and after_raw == raw
        saved, derivative = read_bytes(HERE / relative)
        assert saved == raw
        copied.append({'original': before, 'copied_relative_path': relative,
            'copy_sha256': derivative['sha256'], 'copy_bytes': derivative['bytes'],
            'original_after_equal': True})

    output = {'version': 'configured_resource_preparation_metadata_copy_v1',
        'status': 'copied_metadata_only_no_database_reverification',
        'started_at_utc': start, 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_files': copied, 'copied_files': len(copied),
        'root_actual_preparation_invocation_sha256': read_bytes(ROOT / 'INVOCATION001.json')[1]['sha256'],
        'operator_reported_status': result['status'],
        'operator_reported_inherited_refs': result['inherited_refs'],
        'operator_reported_receipt_sha256': result['receipt']['sha256'],
        'operator_reported_parameters_sha256': result['parameters']['sha256'],
        'operator_reported_native_registry_ref': result['native_registry_ref'],
        'operator_reported_public_search_registry_ref': result['public_search_registry_ref'],
        'SQLite_connections': 0, 'application_imports': 0, 'constructors': 0,
        'model_service_native_calls': 0, 'database_backups': 0,
        'original_or_other_active_workspace_files_opened': 0,
        'limits': ['exact_metadata_copies_only', 'no_independent_database_or_credit_verification',
            'no_original_path_reference_rewriting', 'no_relocated_workspace_resumability',
            'working_database_hash_is_only_the_historical_preparation_descriptor',
            'root_independent_verifier_result_not_in_this_copy', 'no_scientific_launch_or_behavior_proved']}
    save(HERE / 'COPY_RESULT001.json', canonical(output) + b'\n')
    print(json.dumps({'status': output['status'], 'copied_files': len(copied),
        'root': str(HERE), 'SQLite_connections': 0, 'application_imports': 0}, sort_keys=True))

if __name__ == '__main__':
    main()
