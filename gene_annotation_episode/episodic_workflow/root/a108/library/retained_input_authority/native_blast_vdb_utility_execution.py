"""One caller-selected bwrap invocation at original absolute VDB paths.

The wrapper supplies an isolated filesystem/PID/network namespace. Its status
records qualify the attempted command; they are not syscall-trace evidence or a
scientific result. All runtime files are selected beforehand, never discovered.
"""
from __future__ import annotations
import json
from pathlib import PurePosixPath
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_blast_contracts import finite_json_copy
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_blast_database_contracts import _absolute
VERSION = 'native_blast_vdb_offline_execution_v1'
RECEIPT_VERSION = 'native_blast_vdb_offline_receipt_v1'
OFFLINE_FAILURE_CODES = frozenset({'offline_launcher_unavailable', 'offline_runtime_identity_mismatch', 'offline_setup_failed', 'offline_status_unavailable', 'offline_configuration_conflict', 'offline_child_exec_failed'})
_FILE = {'type': 'object', 'properties': {'path': {'type': 'string', 'minLength': 1}, 'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'size_bytes': {'type': 'integer', 'minimum': 0}}, 'required': ['path', 'sha256', 'size_bytes'], 'additionalProperties': False}
OFFLINE_EXECUTION_SCHEMA = {'type': 'object', 'properties': {'version': {'const': VERSION}, 'launcher': _FILE, 'runtime_files': {'type': 'array', 'items': _FILE}, 'runtime_aliases': {'type': 'array', 'items': {'type': 'object', 'properties': {'path': {'type': 'string', 'minLength': 1}, 'target_path': {'type': 'string', 'minLength': 1}}, 'required': ['path', 'target_path'], 'additionalProperties': False}}, 'system_interface_profile': {'const': 'blast_vdb_bwrap_local_v1'}}, 'required': ['version', 'launcher', 'runtime_files', 'runtime_aliases', 'system_interface_profile'], 'additionalProperties': False}
OFFLINE_ENVIRONMENT_SCHEMA = {'type': 'object', 'properties': {'NCBI_VDB_CONFIG': {'type': 'string', 'minLength': 1}, 'BLAST_USAGE_REPORT': {'const': 'false'}, 'NCBI_USAGE_REPORT_ENABLED': {'const': 'false'}, 'DO_NOT_TRACK': {'const': '1'}, 'LC_ALL': {'const': 'C'}}, 'required': ['NCBI_VDB_CONFIG', 'BLAST_USAGE_REPORT', 'NCBI_USAGE_REPORT_ENABLED', 'DO_NOT_TRACK', 'LC_ALL'], 'additionalProperties': False}

def _error(code):
    raise ContractError('native_blast_utility_' + code)

def _require(value, code='offline_configuration_conflict'):
    if not value:
        _error(code)

def _overlap(a, b):
    a, b = (PurePosixPath(a), PurePosixPath(b))
    return a == b or a in b.parents or b in a.parents

def _runtime_files(job):
    rows, known = ([], {})
    selected = job['offline_execution']
    for row in [selected['launcher'], *selected['runtime_files']]:
        previous = known.get(row['path'])
        _require(previous is None or previous == row)
        if previous is None:
            rows.append(row)
            known[row['path']] = row
    return rows

def validate_vdb_offline_execution(value: dict, *, job: dict) -> dict:
    value = finite_json_copy(value)
    _require(next(Draft202012Validator(OFFLINE_EXECUTION_SCHEMA).iter_errors(value), None) is None)
    job = {**job, 'offline_execution': value}
    from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_blast_utility_contracts import database_file_selections
    _require(next(Draft202012Validator(OFFLINE_ENVIRONMENT_SCHEMA).iter_errors(job['environment']), None) is None)
    config = job['databases'][0]['manifest']['access']['offline_configuration']
    _require(config is not None and job['environment']['NCBI_VDB_CONFIG'] == config['path'])
    selected = value['runtime_files']
    _require(len({r['path'] for r in selected}) == len(selected))
    helper = [r for r in selected if r['path'] == job['software']['executable']]
    _require(len(helper) == 1 and helper[0]['sha256'] == job['software']['sha256'])
    runtime = _runtime_files(job)
    paths = {r['path'] for r in runtime}
    data = database_file_selections(job)
    identities = {}
    for row in data:
        identity = (row['expected_sha256'], row['expected_size_bytes'])
        _require(row['original_path'] not in identities or identities[row['original_path']] == identity)
        identities[row['original_path']] = identity
    aliases = value['runtime_aliases']
    _require(len({r['path'] for r in aliases}) == len(aliases))
    for row in aliases:
        _require(row['target_path'] in paths and row['path'] not in paths)
    mounts = [*paths, *[r['path'] for r in aliases], *identities]
    for path in mounts:
        _absolute(path)
        _require(path != '/' and (not any((_overlap(path, forbidden) for forbidden in ('/proc', '/dev', '/sys')))))
    for i, path in enumerate(mounts):
        _require(not any((_overlap(path, other) for other in mounts[i + 1:])))
    return value

def compile_vdb_offline_argv(job: dict, *, attempt_directory: str, native_argv: list[str], status_fd: int) -> list[str]:
    validate_vdb_offline_execution(job['offline_execution'], job=job)
    from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_blast_utility_contracts import compile_native_blast_utility_job, database_file_selections, native_environment, realized_path_maps
    _absolute(attempt_directory)
    _require(type(status_fd) is int and status_fd >= 0)
    _require(native_argv == compile_native_blast_utility_job(job, **realized_path_maps(job, attempt_directory), output_directory=attempt_directory))
    root = PurePosixPath(attempt_directory)
    writable = [str(root / name) for name in ('tmp', 'cache', 'work')]
    data = [r['original_path'] for r in database_file_selections(job)]
    staged = list(realized_path_maps(job, attempt_directory)['input_paths'].values())
    runtime = [r['path'] for r in job['offline_execution']['runtime_files']]
    files = list(dict.fromkeys([*runtime, *data, *staged]))
    aliases = job['offline_execution']['runtime_aliases']
    destinations = [*files, *[r['path'] for r in aliases]]
    _require(not any((_overlap(path, target) for path in destinations for target in writable)))
    _require(not any((_overlap(path, str(root)) for path in [*runtime, *data, *[r['path'] for r in aliases]])))
    directories = {str(root)}
    for path in [*destinations, *writable]:
        directories.update((str(p) for p in PurePosixPath(path).parents if str(p) != '/'))
    args = [job['offline_execution']['launcher']['path'], '--unshare-user', '--unshare-pid', '--unshare-net', '--new-session', '--clearenv', '--json-status-fd', str(status_fd), '--tmpfs', '/']
    for path in sorted(directories, key=lambda p: (len(PurePosixPath(p).parts), p)):
        args += ['--dir', path]
    for path in files:
        args += ['--ro-bind', path, path]
    for alias in aliases:
        args += ['--symlink', alias['target_path'], alias['path']]
    for path in writable:
        args += ['--bind', path, path]
    args += ['--proc', '/proc', '--dev', '/dev', '--chdir', str(root)]
    for key, value in sorted(native_environment(job, str(root)).items()):
        args += ['--setenv', key, value]
    args += ['--remount-ro', '/proc', '--remount-ro', '/dev', '--remount-ro', '/', '--', *native_argv]
    return args

def vdb_offline_native_outcome(receipt):
    """Return confirmed helper outcome only; raw wrapper facts remain separate."""
    unavailable = {'offline_launcher_unavailable', 'offline_setup_failed', 'offline_status_unavailable', 'offline_child_exec_failed', 'offline_configuration_conflict'}
    before_matches = all(((r['before_sha256'], r['before_size_bytes']) == (r['expected_sha256'], r['expected_size_bytes']) for r in receipt['runtime_files']))
    if not before_matches or receipt['child_pid'] is None or receipt['child_exit_code'] is None or (receipt['launcher_returncode'] != receipt['child_exit_code']) or any((r['code'] in unavailable for r in receipt['failures'])):
        return (False, None)
    return (True, receipt['child_exit_code'])

def validate_vdb_offline_receipt(value, *, job, attempt_directory):
    receipt = finite_json_copy(value)
    fields = {'version', 'launcher_argv', 'status_fd', 'status_records', 'launcher_returncode', 'child_pid', 'child_exit_code', 'runtime_files', 'failures'}
    _require(type(receipt) is dict and set(receipt) == fields and (receipt['version'] == RECEIPT_VERSION))
    _require(type(receipt['status_fd']) is int and receipt['status_fd'] >= 0)
    _require(type(receipt['status_records']) is list and all((type(r) is dict for r in receipt['status_records'])))
    for key in ('launcher_returncode', 'child_pid', 'child_exit_code'):
        _require(receipt[key] is None or type(receipt[key]) is int)
    _require(receipt['child_pid'] is None or receipt['child_pid'] > 0)
    from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_blast_utility_contracts import compile_native_blast_utility_job, measurement_pair, realized_path_maps, producer_failure
    if receipt['launcher_argv']:
        native = compile_native_blast_utility_job(job, **realized_path_maps(job, attempt_directory), output_directory=attempt_directory)
        _require(receipt['launcher_argv'] == compile_vdb_offline_argv(job, attempt_directory=attempt_directory, native_argv=native, status_fd=receipt['status_fd']))
    else:
        _require(receipt['launcher_returncode'] is None and (not receipt['status_records']))
    expected = _runtime_files(job)
    _require(type(receipt['runtime_files']) is list and len(receipt['runtime_files']) == len(expected))
    for row, original in zip(receipt['runtime_files'], expected):
        _require(type(row) is dict and set(row) == {'path', 'expected_sha256', 'expected_size_bytes', 'before_sha256', 'before_size_bytes', 'final_sha256', 'final_size_bytes'})
        _require(row['path'] == original['path'] and measurement_pair(row, 'expected_') == (original['size_bytes'], original['sha256']))
        for prefix in ('before_', 'final_'):
            pair = measurement_pair(row, prefix)
            if pair != measurement_pair(row, 'expected_'):
                _require(producer_failure('offline_runtime_identity_mismatch') in receipt['failures'] or (row['path'] == job['offline_execution']['launcher']['path'] and producer_failure('offline_launcher_unavailable') in receipt['failures']))
        if measurement_pair(row, 'before_') != measurement_pair(row, 'expected_'):
            _require(not receipt['launcher_argv'])
    _require(type(receipt['failures']) is list and len({json.dumps(r, sort_keys=True) for r in receipt['failures']}) == len(receipt['failures']))
    for row in receipt['failures']:
        _require(row.get('code') in OFFLINE_FAILURE_CODES and row == producer_failure(row['code']))
    pids = [r['child-pid'] for r in receipt['status_records'] if 'child-pid' in r]
    exits = [r['exit-code'] for r in receipt['status_records'] if 'exit-code' in r]
    expected_pid = pids[0] if len(pids) == 1 and type(pids[0]) is int and (pids[0] > 0) else None
    expected_exit = exits[0] if len(exits) == 1 and type(exits[0]) is int else None
    _require(receipt['child_pid'] == expected_pid and receipt['child_exit_code'] == expected_exit)
    if receipt['launcher_argv'] and (expected_pid is None or expected_exit is None or receipt['launcher_returncode'] != expected_exit):
        _require(any((r['code'] in {'offline_launcher_unavailable', 'offline_setup_failed', 'offline_child_exec_failed', 'offline_status_unavailable'} for r in receipt['failures'])))
    return receipt
