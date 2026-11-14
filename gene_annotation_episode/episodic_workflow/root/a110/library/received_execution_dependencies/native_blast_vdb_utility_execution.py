from __future__ import annotations
from pathlib import PurePosixPath
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_contracts import finite_json_copy
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_contracts import _absolute
VERSION = 'native_blast_vdb_offline_execution_v1'
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
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_contracts import database_file_selections
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
