"""Independent, fixed-input, read-only verification of one prepared inactive caller.

Only --output is written, exclusively. No application/test/model/service imports.
SQL is confined to the NEW immutable checkpoint and NEW inactive native registry.
This is preparation evidence, not a scientific launch or episode-behavior proof.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import tomllib

PLAN = Path('/tmp/configured-resource-caller-preparation-20261022-001-U7WRRlHE')
BASELINE = Path('/tmp/configured-literature-caller-plan-20261022-001-vujlt8m4')
RESOURCE_PLAN = Path('/tmp/configured-resource-investigation-plan-20261022-001-DAGmrtaT')
ADOPTED_SCOPE = Path('/home/chia/repos/gene_annotation_episode/docs/CONFIGURED_RESOURCE_CALLER_ACTUAL_SCOPE_2026-10-22_001.md')
ADOPTED_FOCUS = Path('/tmp/configured-resource-caller-scope-20261022-001/FOCUS_ADOPTED001.txt')
PRIOR_VERIFIER = Path('/tmp/configured-literature-actual-verifier-20261022-001-FW9HWYzm/verify_actual_preparation001.py')
PACKET_MANIFEST_SHA = 'PENDING_FINAL_PACKET_MANIFEST_SHA'
PACKET_MEMBER_COUNT = 0
INPUT_MANIFEST_SHA = 'e398322011562a864f56a24ecc1bfa798854e83f78e96b07132ee04ed3db23f1'
ROOT_PREPARATION_EVIDENCE = Path('/tmp/configured-resource-investigation-root-preparation-20261022-001')
ROOT_INVOCATION = ROOT_PREPARATION_EVIDENCE / 'INVOCATION001.json'
ROOT_STDOUT_BASENAME = 'STDOUT001.log'
ROOT_STDERR_BASENAME = 'STDERR001.log'
RUN = Path('/home/chia/gene_annotation_episode_runs/configured_resource_investigation_001')
ENGINEERING = Path('/tmp/configured-resource-investigation-preparation-20261022-001')
CODE = Path('/tmp/gene-annotation-configured-caller-20261022-007')
HERE = Path('/tmp/configured-resource-actual-verifier-20261022-001-BAWpJPut')
WORKSPACE = RUN / 'workspace'
CHECKPOINT = WORKSPACE / 'checkpoint/state.sqlite3'
NATIVE = RUN / 'native-jobs/jobs.sqlite'
PIN = '3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'
FIXED_HASHES = {
    BASELINE / 'MANIFEST_FINAL001.json': 'd1a696d49123fbf6363f8cb9bb46a7dc2fc413ba06b1f9f9f9e81947a51f06ad',
    BASELINE / 'INPUTS001.json': '86bfa0d2f45131195683318241c81c4117431b1cdcf875b45d11096fc3dba9c6',
    RESOURCE_PLAN / 'MANIFEST_FINAL001.json': 'caf0fcfe6c29fcb4e31ddc348ed0d73f0ada022d0d949ecbd8dfeb233038e8c2',
    RESOURCE_PLAN / 'INPUT_DELTAS001.json': '5fa4cb22fc4039283b961d0f3a5f83052e30a03228c44da0bd0436831d241a39',
    ADOPTED_SCOPE: '9224e495eeb891266ed5c7b212598f4b436c4e1d3cb376db4ffe30a187fd82ad',
    ADOPTED_FOCUS: 'b2f718a545a1829b8521f6cd437ff1c0688ad4068b5f739d033e9d8ce151c7bf',
    PRIOR_VERIFIER: 'a00604ade72374e2ca5e6f8ae882fe01efbe7c91d821f49689350fdbf6a81842',
    PLAN / 'MANIFEST_FINAL001.json': PACKET_MANIFEST_SHA,
    PLAN / 'INPUTS001.json': INPUT_MANIFEST_SHA,
    PLAN / 'SCHEMAS004.json': 'b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112',
}
SEEN = {}
CHECKS = []


def require(condition, label):
    if not condition:
        raise ValueError(label)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def no_links(path):
    require(path.is_absolute() and '..' not in path.parts, 'absolute nonescaping path required')
    for member in (path, *path.parents):
        if os.path.lexists(member):
            require(not stat.S_ISLNK(member.lstat().st_mode), 'symlink rejected: ' + str(member))


def metadata(s):
    return {'mode': stat.S_IMODE(s.st_mode), 'mtime_ns': s.st_mtime_ns,
            'inode': s.st_ino, 'device': s.st_dev, 'bytes': s.st_size}


def witness(path):
    path = Path(path)
    no_links(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), 'regular file required: ' + str(path))
        h = hashlib.sha256()
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                h.update(chunk)
        after = os.fstat(fd)
        require(metadata(before) == metadata(after), 'file changed while read: ' + str(path))
        row = {'path': str(path), 'sha256': h.hexdigest(), **metadata(after)}
    finally:
        os.close(fd)
    require(metadata(path.lstat()) == metadata(after), 'path changed while read: ' + str(path))
    if str(path) in SEEN:
        require(SEEN[str(path)] == row, 'input changed: ' + str(path))
    SEEN[str(path)] = row
    return row


def matches(path, descriptor):
    actual = witness(path)
    require(all(actual[k] == descriptor[k] for k in ('sha256', 'bytes')), 'descriptor mismatch: ' + str(path))
    return actual


def raw(path):
    before = witness(path)
    with open(path, 'rb') as handle:
        data = handle.read()
    require(sha(data) == before['sha256'] and len(data) == before['bytes'], 'reread changed: ' + str(path))
    return data


def read(path):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'duplicate JSON key')
            value[key] = item
        return value
    return json.loads(raw(path), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def member(root, name):
    require(isinstance(name, str) and name and not Path(name).is_absolute()
            and '..' not in Path(name).parts, 'invalid relative member')
    path = root / name
    no_links(path)
    return path


def regular_members(root):
    no_links(root)
    found = set()
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in directories:
            path = Path(parent) / name
            require(stat.S_ISDIR(path.lstat().st_mode), 'non-directory tree member')
        for name in files:
            path = Path(parent) / name
            require(stat.S_ISREG(path.lstat().st_mode), 'nonregular tree member')
            found.add(path.relative_to(root).as_posix())
    return found


def verify_manifest(root, name, count):
    manifest = read(root / name)
    rows = manifest['members']
    require(len(rows) == count, 'manifest member count')
    require(regular_members(root) == set(rows) | {name}, 'manifest regular membership')
    for relative, row in rows.items():
        path = member(root, relative)
        require(row['path'] == str(path), 'manifest path identity')
        matches(path, row)
    CHECKS.append({'check': 'exact_manifest', 'path': str(root / name), 'members': count})
    return manifest


def relevant_closed_fields(value, schema, label):
    """Check direct closed keys/constants only; this is not full JSON Schema validation."""
    require(isinstance(value, dict), label + ': object required')
    require(set(schema.get('required', [])) <= set(value), label + ': required fields')
    if schema.get('additionalProperties') is False:
        require(set(value) <= set(schema['properties']), label + ': unexpected fields')
    for key, constraint in schema.get('properties', {}).items():
        if key in value and 'const' in constraint:
            require(canonical(value[key]) == canonical(constraint['const']), label + ': constant ' + key)


def implementation():
    paths = sorted(path for package in ('gene_annotation_episode', 'method_loop')
                   for path in (CODE / package).rglob('*.py'))
    digest = hashlib.sha256()
    for path in paths:
        row = witness(path)
        digest.update(path.relative_to(CODE).as_posix().encode() + b'\0')
        digest.update(bytes.fromhex(row['sha256']))
    require(len(paths) == 137 and digest.hexdigest() == PIN, 'current 137-file source pin')
    return {'sha256': digest.hexdigest(), 'file_count': len(paths)}


def db_counts(path, tables, expected_run=None):
    require(path in (CHECKPOINT, NATIVE), 'SQL path outside exact allowlist')
    before = witness(path)
    for suffix in ('-wal', '-shm'):
        sidecar = Path(str(path) + suffix)
        no_links(sidecar)
        if os.path.lexists(sidecar):
            row = witness(sidecar)
            if suffix == '-wal':
                require(row['bytes'] == 0, 'nonempty NEW database WAL')
    require(all(re.fullmatch('[a-z_]+', table) for table in tables), 'finite SQL table names')
    connection = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        connection.execute('PRAGMA query_only=ON')
        require(connection.execute('PRAGMA query_only').fetchone()[0] == 1, 'query_only not enabled')
        connection.execute('BEGIN')
        counts = {table: connection.execute('SELECT count(*) FROM "' + table + '"').fetchone()[0]
                  for table in tables}
        if expected_run is not None:
            ids = connection.execute('SELECT run_id FROM runtime_runs').fetchall()
            require(ids == [(expected_run,)], 'checkpoint inherited run identity')
    finally:
        connection.close()
    require(witness(path) == before, 'NEW database changed during read-only SQL')
    return counts



def verify_resource_plan():
    manifest = read(RESOURCE_PLAN / 'MANIFEST_FINAL001.json')
    rows = manifest['members']
    require(len(rows) == manifest['member_count'] == 7, 'accepted resource plan count')
    require(regular_members(RESOURCE_PLAN) == {row['path'] for row in rows} | {'MANIFEST_FINAL001.json'}, 'resource plan membership')
    for row in rows:
        path = member(RESOURCE_PLAN, row['path'])
        matches(path, row)
        require(format(stat.S_IMODE(path.lstat().st_mode), '04o') == row['mode'], 'resource plan member mode')
    require(sum(row['bytes'] for row in rows) == manifest['member_bytes'] == 88177, 'resource plan bytes')


def apply_exact_leaves(value, rows, allowed):
    value = json.loads(canonical(value))
    require(len(rows) == len(allowed) and {row['path'] for row in rows} == set(allowed), 'exact adopted leaf allowlist')
    for row in rows:
        keys = row['path'].split('.')
        parent = value
        for key in keys[:-1]:
            parent = parent[key]
        require(canonical(parent[keys[-1]]) == canonical(row['original_value']), 'original leaf differs from accepted baseline')
        parent[keys[-1]] = row['proposed_value']
    return value


def verify_input_derivation():
    deltas = read(RESOURCE_PLAN / 'INPUT_DELTAS001.json')
    require(deltas['proposed_run_directory'] == str(RUN) and deltas['runtime_pin'] == PIN, 'adopted resource destination/pin')
    for row in deltas['baseline_authority_files']:
        path = Path(row['path'])
        require(path.parent == BASELINE, 'baseline authority outside exact packet')
        matches(path, row)
    old_request = read(BASELINE / 'C_REQUEST001.json')
    request = read(PLAN / 'C_REQUEST001.json')
    expected_request = json.loads(canonical(old_request))
    require(deltas['C_request_only_delta'] == {'path': 'destination_workspace',
            'original_value': old_request['destination_workspace'], 'proposed_value': str(WORKSPACE)}, 'single C destination delta')
    expected_request['destination_workspace'] = str(WORKSPACE)
    require(request == expected_request, 'C request has unauthorized differences')
    original_operands = dict(old_request)
    del original_operands['destination_workspace']
    require(sha(canonical(original_operands)) == deltas['C_source_operand_hash']
            == '9ab6a050e725bec75720887960ceda35b1b3bc2cfc80a81db80786189885bdcd', 'C source operand authority')
    require(sha(canonical(request['initial_known_record_refs'])) == deltas['initial_198_list_canonical_sha256']
            == '05d35a200c33e1b4defb0859e0aea70699b49be48a4cc41e55b274ca8f59a860', 'original selected198 list')
    config_paths = {'history', 'workspace', 'local_tools.minimap2_cache_dir',
                    'local_tools.native_receipts_dir', 'public.provider_access_dir'}
    original_config = tomllib.loads(raw(BASELINE / 'config.toml').decode())
    expected_config = apply_exact_leaves(original_config, deltas['changes']['configuration'], config_paths)
    actual_config = tomllib.loads(raw(PLAN / 'config.toml').decode())
    require(actual_config == expected_config, 'exact five configuration relocations')
    parameter_paths = {'services.api_timing.history_path', 'services.api_timing.ledger_path',
                       'services.public_search_registry.registry_ref'}
    expected_template = apply_exact_leaves(read(BASELINE / 'PARAMETER_TEMPLATE001.json'),
        deltas['changes']['parameters'], parameter_paths)
    require(read(PLAN / 'PARAMETER_TEMPLATE001.json') == expected_template, 'exact three parameter leaves')
    require(expected_template['services']['api_timing'] == deltas['API_binding'], 'exact relocated API binding')
    for name in ('EXPECTED_HANDOFF001.json', 'SCHEMAS004.json', 'PUBLICATION_INPUTS001.json'):
        require(raw(PLAN / name) == raw(BASELINE / name), 'unchanged original authority ' + name)
    for copied, original in (('BASELINE_CONFIG001.toml', 'config.toml'),
                             ('BASELINE_C_REQUEST001.json', 'C_REQUEST001.json'),
                             ('BASELINE_PARAMETER_TEMPLATE001.json', 'PARAMETER_TEMPLATE001.json')):
        require(raw(PLAN / copied) == raw(BASELINE / original), 'local baseline authority copy')
    require(raw(PLAN / 'ADOPTED_SCOPE001.md') == raw(ADOPTED_SCOPE)
            and raw(PLAN / 'ADOPTED_INPUT_DELTAS001.json') == raw(RESOURCE_PLAN / 'INPUT_DELTAS001.json'), 'local adopted authority copies')
    inputs = read(PLAN / 'INPUTS001.json')
    require(inputs['version'] == 'configured_resource_caller_preparation_inputs_v1'
            and inputs['adopted_scope_sha256'] == FIXED_HASHES[ADOPTED_SCOPE]
            and inputs['adopted_focus_sha256'] == FIXED_HASHES[ADOPTED_FOCUS], 'resource input authority labels')
    for field, path in (('accepted_plan_manifest', RESOURCE_PLAN / 'MANIFEST_FINAL001.json'),
                        ('input_delta_plan', RESOURCE_PLAN / 'INPUT_DELTAS001.json'),
                        ('parent_preparation_operator', BASELINE / 'prepare_caller001.py')):
        require(inputs[field]['path'] == str(path), 'exact resource input authority path')
        matches(path, inputs[field])
    original_focus = raw(RESOURCE_PLAN / 'FOCUS_DRAFT001.txt')
    old_phrase = b'the existing literature hierarchy and its library are unchanged.'
    new_phrase = b'the existing literature hierarchy is unchanged.'
    require(original_focus.count(old_phrase) == 1 and raw(ADOPTED_FOCUS) == original_focus.replace(old_phrase, new_phrase)
            and raw(PLAN / 'focus.txt') == raw(ADOPTED_FOCUS), 'exact adopted focus phrase correction')
    CHECKS.append({'check': 'exact_adopted_resource_inputs', 'C_destination_leaves': 1,
                   'config_leaves': sorted(config_paths), 'parameter_leaves': sorted(parameter_paths),
                   'deferred_outputs_only': ['policy.scientific_progress.initial_known_record_refs', 'policy.operational.registry_ref'],
                   'focus_sha256': witness(ADOPTED_FOCUS)['sha256']})



def utc_stamp(value):
    require(isinstance(value, str), 'execution timestamp must be string')
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, 'execution timestamp must be UTC')
    return parsed


def verify_execution_receipts(invocation_path):
    require(invocation_path == ROOT_INVOCATION, 'exact root external invocation path')
    invocation = read(invocation_path)
    require(set(invocation) == {'version', 'argv', 'cwd', 'explicit_environment', 'started_at_utc',
        'finished_at_utc', 'exit_code', 'stdout', 'stderr', 'operator', 'input_manifest',
        'source_pin_before', 'source_pin_after', 'status'}, 'closed root invocation fields')
    expected_operator_argv = [str(PLAN / 'prepare_caller001.py'), '--prepare',
                             '--input-manifest-sha256', INPUT_MANIFEST_SHA]
    expected_environment = {'PYTHONPATH': str(CODE), 'PYTHONDONTWRITEBYTECODE': '1'}
    require(invocation['version'] == 'root_configured_resource_preparation_invocation_v1'
            and invocation['status'] == 'exited' and type(invocation['exit_code']) is int
            and invocation['exit_code'] == 0, 'external root subprocess did not exit0')
    require(invocation['argv'] == ['/home/chia/repos/gene_annotation_episode/.venv/bin/python', *expected_operator_argv]
            and invocation['cwd'] == str(CODE) and invocation['explicit_environment'] == expected_environment,
            'exact external preparation argv/cwd/environment')
    for name in ('source_pin_before', 'source_pin_after'):
        require(canonical(invocation[name]) == canonical({'sha256': PIN, 'file_count': 137}), 'external preparation source guards')
    for name, path in (('operator', PLAN / 'prepare_caller001.py'), ('input_manifest', PLAN / 'INPUTS001.json'),
                       ('stdout', ROOT_PREPARATION_EVIDENCE / ROOT_STDOUT_BASENAME),
                       ('stderr', ROOT_PREPARATION_EVIDENCE / ROOT_STDERR_BASENAME)):
        descriptor = invocation[name]
        require(set(descriptor) == {'path', 'sha256', 'bytes'} and descriptor['path'] == str(path),
                'closed exact external descriptor ' + name)
        matches(path, descriptor)  # stdout/stderr are byte-hashed only; no log content interpreted.
    started = read(ENGINEERING / 'OPERATOR_EXECUTION_STARTED001.json')
    finished = read(ENGINEERING / 'OPERATOR_EXECUTION_FINISHED001.json')
    require(set(started) == {'argv', 'cwd', 'explicit_environment', 'started_at_utc', 'operator', 'scope_sha256'}
            and set(finished) == {'started_at_utc', 'finished_at_utc', 'status', 'exit_code', 'last_phase'},
            'closed planned operator execution record fields')
    require(started['argv'] == expected_operator_argv and started['cwd'] == str(CODE)
            and started['explicit_environment'] == expected_environment
            and started['operator'] == invocation['operator']
            and started['scope_sha256'] == FIXED_HASHES[ADOPTED_SCOPE], 'internal execution start authority')
    require(finished['status'] == 'prepared_not_started' and type(finished['exit_code']) is int
            and finished['exit_code'] == 0 and finished['last_phase'] == 'source_after_guard'
            and finished['started_at_utc'] == started['started_at_utc'], 'internal preparation finish is not successful')
    require(utc_stamp(invocation['started_at_utc']) <= utc_stamp(started['started_at_utc'])
            <= utc_stamp(finished['finished_at_utc']) <= utc_stamp(invocation['finished_at_utc']),
            'external/internal execution chronology')
    require(not os.path.lexists(ENGINEERING / 'FAILURE001.json')
            and not os.path.lexists(ENGINEERING / 'SOURCE_AFTER_FAILURE001.json'), 'late preparation failure/partial evidence retained')
    CHECKS.append({'check': 'external_process_receipt_and_operator_records', 'external_receipt': witness(invocation_path),
                   'external_exit_code': 0, 'internal_status': finished['status'],
                   'start_utc': invocation['started_at_utc'], 'finish_utc': invocation['finished_at_utc'],
                   'stdout_stderr': 'exact descriptor bytes hashed only',
                   'one_recorded_subprocess_not_exhaustive_process_census': True})
    return invocation


def verify(preparation_invocation):
    require(len(PACKET_MANIFEST_SHA) == len(INPUT_MANIFEST_SHA) == 64 and PACKET_MEMBER_COUNT > 0, 'final reviewed packet pins required')
    for path, expected_sha in FIXED_HASHES.items():
        require(witness(path)['sha256'] == expected_sha, 'fixed authority identity: ' + str(path))
    verify_manifest(BASELINE, 'MANIFEST_FINAL001.json', 22)
    verify_manifest(PLAN, 'MANIFEST_FINAL001.json', PACKET_MEMBER_COUNT)
    verify_resource_plan()
    verify_input_derivation()
    invocation = verify_execution_receipts(preparation_invocation)
    inputs = read(PLAN / 'INPUTS001.json')
    require(inputs['destination_run_directory'] == str(RUN) and inputs['implementation_root'] == str(CODE)
            and inputs['implementation_sha256'] == PIN and inputs['runtime_file_count'] == 137, 'input execution identity')
    for name, row in inputs['members'].items():
        matches(member(PLAN, name), row)
    provenance_root = Path('/home/chia/repos/gene_annotation_episode/verification/progress_checkpoint_2026-10-22_015')
    for name, row in inputs['source_provenance'].items():
        path = member(provenance_root, name)
        require(row['path'] == str(path), 'sealed provenance path identity')
        matches(path, row)  # JSON/config authorities only; their old DB path strings are never opened.
    source_pin = implementation()
    publication_inputs = read(PLAN / 'PUBLICATION_INPUTS001.json')
    publication_root = CODE / 'research/slotted_process_library/publications/2026-10-21-001'
    require(publication_inputs['root'] == str(publication_root), 'fixed publication root')
    for name, row in publication_inputs['members'].items():
        path = member(publication_root, name)
        require(row['path'] == str(path), 'static publication member path')
        matches(path, row)
    arguments = read(PLAN / 'C_REQUEST001.json')
    expected = read(PLAN / 'EXPECTED_HANDOFF001.json')
    schemas = read(PLAN / 'SCHEMAS004.json')['$defs']
    output_schema = read(PLAN / 'OPERATOR_OUTPUT_SCHEMA001.json')
    result_path = RUN / 'caller-inputs/PREPARATION_RESULT001.json'
    result_bytes = raw(result_path)
    require(result_bytes == raw(ENGINEERING / 'RESULTS001.json'), 'closed resource result copies differ')
    require(not os.path.lexists(ENGINEERING / 'FAILURE001.json'), 'preparation failure evidence exists')
    result = read(result_path)
    relevant_closed_fields(result, output_schema['$defs']['result'], 'closed preparation result')
    require(result['version'] == 'configured_resource_investigation_preparation_result_v1'
            and result['status'] == 'prepared_not_started' and result['execution_implementation_sha256'] == PIN
            and result['run_directory'] == str(RUN) and result['workspace'] == str(WORKSPACE), 'prepared destination identity')
    require(result['inherited_refs'] == 200 and result['model_http_native_calls'] == 0
            and result['new_scientific_runs_started'] == 0 and result['source_guards_unchanged'] is True, 'recorded preparation-only counts')
    descriptor_paths = {
        'case_launch': RUN / 'case-launch.json', 'config': RUN / 'caller-inputs/config.toml',
        'custody_result': RUN / 'caller-inputs/C_RESULT001.json', 'focus': RUN / 'caller-inputs/focus.txt',
        'parameters': RUN / 'caller-inputs/parameters.json', 'receipt': WORKSPACE / 'scientific-checkpoint-fork.json',
        'working_database_after_prepare': WORKSPACE / 'state.sqlite3',
        'policy_source': CODE / 'gene_annotation_episode/api_planning_case_policy.py',
    }
    for key, path in descriptor_paths.items():
        require(result[key]['path'] == str(path), 'closed descriptor path: ' + key)
        matches(path, result[key])
    custody = read(descriptor_paths['custody_result'])
    receipt = read(descriptor_paths['receipt'])
    relevant_closed_fields(custody, schemas['result'], 'C result')
    relevant_closed_fields(receipt, schemas['receipt'], 'C receipt')
    require(custody['status'] == 'published' and custody['destination_workspace'] == str(WORKSPACE)
            and receipt['destination_workspace'] == str(WORKSPACE), 'custody destination')
    require(custody['receipt'] == result['receipt'] and receipt['fixed_identity'] == expected['fixed_identity'], 'custody fixed identity')
    source = receipt['source']
    for key, operand in (('workspace', 'source_workspace'), ('run_directory', 'source_run_directory'),
                         ('implementation_root', 'source_implementation_root'), ('run_id', 'source_run_id'),
                         ('implementation_sha256', 'expected_source_implementation_sha256')):
        require(source[key] == arguments[operand], 'custody source identity: ' + key)
    require(source['pending']['request_raw_utf8_sha256'] == arguments['expected_pending_request_sha256']
            and source['pending']['call_index'] == 179 and source['pending']['response'] is None
            and source['pending']['selected_action_at_call'] is False, 'inherited pending request identity')
    require(source['counts'] == expected['source_counts'] and receipt['preserved_counts'] == expected['preserved_counts'], 'inherited source counts')
    require(receipt['verification'] and all(value is True for value in receipt['verification'].values()), 'recorded C verification flags')
    selected = arguments['initial_known_record_refs']
    final = custody['initial_known_record_refs']
    lineage = custody['lineage_source_refs']
    require(len(selected) == len(set(selected)) == 198 and len(final) == len(set(final)) == 200, '198 selected / 200 final unique refs')
    require(set(lineage) == {'index', 'observations'} and len(set(lineage.values())) == 2
            and set(lineage.values()).isdisjoint(selected)
            and final == sorted(set(selected) | set(lineage.values())), 'fresh 198+2 sorted union')
    require(receipt['caller_initial_known_record_refs'] == selected and receipt['initial_known_record_refs'] == final
            and sha(canonical(final)) == receipt['initial_known_record_refs_sha256'], 'receipt final refs identity')
    require(lineage == {'index': receipt['lineage']['index_source_ref'], 'observations': receipt['lineage']['observation_source_ref']}, 'lineage source mapping')
    old_receipt = read(provenance_root / 'actual-custody-receipt.json')
    require(receipt['fork_id'] != old_receipt['fork_id']
            and set(lineage.values()).isdisjoint({old_receipt['lineage']['index_source_ref'], old_receipt['lineage']['observation_source_ref']}), 'fresh custody/lineage identities')
    checkpoint_paths = {}
    for key, row in receipt['checkpoint'].items():
        require(row == expected['checkpoint_descriptors'][key], 'checkpoint descriptor authority: ' + key)
        path = member(WORKSPACE, row['path'])
        matches(path, row)
        checkpoint_paths[key] = path
    require(checkpoint_paths['database'] == CHECKPOINT, 'exact checkpoint SQL path')
    require(source['authority_files'] == expected['source_authorities'], 'copied authority list')
    for row in source['authority_files']:
        matches(member(WORKSPACE, row['checkpoint_relative_path']), row)
    require(source['implementation_file_manifest'] == expected['source_implementation_manifest'], 'old source manifest authority')
    implementation_manifest = read(member(WORKSPACE, source['implementation_file_manifest']['path']))
    matches(member(WORKSPACE, source['implementation_file_manifest']['path']), source['implementation_file_manifest'])
    require(len(implementation_manifest['files']) == 122
            and implementation_manifest['implementation_sha256'] == source['implementation_sha256'], 'inherited 122-file implementation manifest')
    committed = read(checkpoint_paths['committed_reference_manifest'])
    refs = {row['reference'] for row in committed['records']}
    native_refs = sorted(row['reference'] for row in committed['records'] if row['record_type'] == 'native_execution')
    require(len(committed['records']) == len(refs) == 193 and refs <= set(selected)
            and committed['input_count'] == 1 and committed['record_count'] == 192
            and native_refs == expected['original_native_receipts'], '193 inherited refs / four native receipts')
    artifacts = read(checkpoint_paths['artifact_manifest'])
    require(artifacts['count'] == len(artifacts['artifacts']) == 144 and artifacts['total_bytes'] == 4201310, 'artifact inventory counts')
    for row in artifacts['artifacts']:
        require(row['id'] == 'artifact_' + row['sha256'], 'artifact content identity')
        matches(member(WORKSPACE, row['relative_path']), row)
    require(sum(row['bytes'] for row in artifacts['artifacts']) == artifacts['total_bytes'], 'artifact bytes sum')
    def lineage_artifact(ref):
        require(re.fullmatch('artifact_[a-f0-9]{64}', ref) is not None, 'lineage artifact ref')
        checksum = ref[9:]
        path = member(WORKSPACE, 'artifacts/' + checksum[:2] + '/' + checksum)
        require(witness(path)['sha256'] == checksum, 'lineage artifact content hash')
        return path
    index = read(lineage_artifact(receipt['lineage']['index_artifact_ref']))
    stream = raw(lineage_artifact(receipt['lineage']['observation_artifact_ref']))
    relevant_closed_fields(index, schemas['observation_index'], 'lineage index')
    require(index['record_count'] == len(index['rows']) == receipt['lineage']['original_observation_count'] == 175
            and index['observation_source_ref'] == lineage['observations']
            and index['observation_artifact_ref'] == receipt['lineage']['observation_artifact_ref']
            and index['source_run_id'] == source['run_id'] and index['source_episode_id'] == source['episode_id'], '175 inherited observation index identity')
    require(sha(stream) == index['observation_artifact_sha256'] and len(stream) == index['observation_artifact_bytes'], 'raw lineage stream identity')
    offset = 0
    for ordinal, row in enumerate(index['rows']):
        end = offset + row['raw_text_utf8_bytes']
        require(row['unit_index'] == ordinal and row['raw_text_utf8_offset'] == offset
                and row['run_id'] == source['run_id'] and row['episode_id'] == source['episode_id']
                and sha(stream[offset:end]) == row['raw_text_utf8_sha256']
                and row['delimiter_bytes'] == 1 and row['delimiter_hex'] == '0a' and stream[end:end + 1] == b'\n', 'raw observation index row')
        offset = end + 1
    require(offset == len(stream), 'raw lineage trailing bytes')
    working = result['working_database_after_prepare']
    publication = receipt['workspace_database_at_publication']
    require(publication['path'] == 'state.sqlite3', 'historical working publication relative path')
    checkpoint_stat, working_stat = CHECKPOINT.lstat(), (WORKSPACE / 'state.sqlite3').lstat()
    require((checkpoint_stat.st_dev, checkpoint_stat.st_ino) != (working_stat.st_dev, working_stat.st_ino), 'checkpoint and working share inode')
    guard_names = ['SOURCE_BEFORE001.json', 'SOURCE_AFTER_C001.json', 'SOURCE_AFTER_PREPARE001.json']
    guards = [raw(ENGINEERING / name) for name in guard_names]
    require(guards[0] == guards[1] == guards[2], 'three NEW recorded source guards not byte identical')
    guard = read(ENGINEERING / guard_names[0])
    require(guard['implementation']['sha256'] == source['implementation_sha256']
            and guard['implementation']['file_count'] == 122 and len(guard['files']) == 160, 'recorded source guard shape')
    for row in [expected['source_database'], expected['source_native_database'], *expected['source_authorities']]:
        original_path = row.get('source_path', row.get('path'))
        require(all(guard['files'][original_path][k] == row[k] for k in ('sha256', 'bytes')), 'recorded original witness mismatch')
    for name in ('C_REQUEST001.json', 'SCHEMAS004.json', 'EXPECTED_HANDOFF001.json', 'PARAMETER_TEMPLATE001.json', 'config.toml', 'focus.txt'):
        require(raw(RUN / 'caller-inputs' / name) == raw(PLAN / name), 'prepared caller input copy: ' + name)
    configuration = tomllib.loads(raw(PLAN / 'config.toml').decode())
    configuration['local_jobs']['wall_seconds'] = None
    launch = read(RUN / 'case-launch.json')
    require(launch == read(RUN / 'caller-inputs/PREPARE_RESULT001.json')
            and launch['configuration'] == configuration and launch['focus'] == raw(PLAN / 'focus.txt').decode(), 'exact ordinary prepared configuration/focus')
    require(launch['run_dir'] == str(RUN) and launch['case_dir'] == inputs['case_directory']
            and all(launch[k] == expected['fixed_identity'][k] for k in ('problem_ref', 'target_ref', 'target_sequence_sha256')), 'prepared case identity')
    native_configuration = read(RUN / 'native-jobs/configuration.json')
    native_ref = native_configuration['registry_ref']
    require(native_configuration == launch['registry_configuration'] and native_ref == result['native_registry_ref']
            and re.fullmatch('execution_registry_[a-f0-9]{32}', native_ref) is not None, 'new native configuration identity')
    inherited_native = read(WORKSPACE / 'checkpoint/authority/native-jobs/configuration.json')['registry_ref']
    require(native_ref not in (inherited_native, expected['retained_active_native_registry_ref'],
            'execution_registry_d0dbd700ba854b2d83c0c5c57ca7c598'), 'native registry equals retained source/active/historical caller identity')
    parameters = read(RUN / 'caller-inputs/parameters.json')
    template = read(PLAN / 'PARAMETER_TEMPLATE001.json')
    template['policy']['scientific_progress']['initial_known_record_refs'] = final
    template['policy']['operational']['registry_ref'] = native_ref
    require(parameters == template, 'exact two-field parameter derivation')
    remainder = json.loads(canonical(parameters['policy']))
    del remainder['scientific_progress']['initial_known_record_refs']
    del remainder['operational']['registry_ref']
    require(sha(canonical(remainder)) == expected['static_policy_remainder_sha256'], 'static numerical policy remainder')
    public_ref = parameters['services']['public_search_registry']['registry_ref']
    require(public_ref == inputs['public_search_registry_ref'] == result['public_search_registry_ref']
            and public_ref == 'execution_registry_1411c4378f584a40b65ed74178e1cb05'
            and public_ref != expected['retained_active_public_registry_ref']
            and public_ref != 'execution_registry_9d451c293fb649cea87d48ab2f5ea4d2'
            and public_ref != native_ref, 'fresh public registry identity')
    absent_bindings = ['run.json', 'policy-binding.json', 'episode-execution-binding.json']
    for name in absent_bindings:
        require(not os.path.lexists(RUN / name), 'unexpected new runtime binding: ' + name)
    table_manifest = read(checkpoint_paths['table_manifest'])
    table_counts = {row['name']: row['row_count'] for row in table_manifest['tables']}
    require(len(table_counts) == len(table_manifest['tables']) == 45, 'checkpoint table inventory')
    checkpoint_counts = db_counts(CHECKPOINT, sorted(table_counts), source['run_id'])
    require(checkpoint_counts == table_counts, 'checkpoint SQL counts differ from pinned table manifest')
    inherited_runtime = {name: checkpoint_counts[name] for name in ('runtime_runs', 'runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls')}
    require(inherited_runtime == result['preserved_old_runtime_counts'] == {'runtime_runs': 1, 'runtime_episodes': 1, 'runtime_actions': 179, 'runtime_observations': 175, 'runtime_model_calls': 180}, 'inherited runtime count relationship')
    native_counts = db_counts(NATIVE, ['orders', 'handoffs', 'samples'])
    require(native_counts == result['native_registry_counts'] == {'orders': 0, 'handoffs': 0, 'samples': 0}, 'NEW inactive native registry not empty')
    operator_inputs = read(RUN / 'caller-inputs/OPERATOR_INPUTS001.json')
    require(operator_inputs['execution_implementation_sha256'] == PIN and operator_inputs['model_http_native_calls'] == 0
            and operator_inputs['argv'] == [str(PLAN / 'prepare_caller001.py'), '--prepare',
                '--input-manifest-sha256', INPUT_MANIFEST_SHA]
            and operator_inputs['cwd'] == str(CODE), 'recorded exact resource preparation operator input')
    matches(PLAN / 'INPUTS001.json', operator_inputs['input_manifest'])
    require(operator_inputs['input_manifest']['path'] == str(PLAN / 'INPUTS001.json')
            and operator_inputs['operator']['path'] == str(PLAN / 'prepare_caller001.py'), 'operator recorded operand paths')
    matches(PLAN / 'prepare_caller001.py', operator_inputs['operator'])
    CHECKS.extend([
        {'check': 'fresh_reference_union', 'selected': 198, 'fresh_lineage': lineage, 'final': 200, 'final_sha256': receipt['initial_known_record_refs_sha256']},
        {'check': 'inherited_custody', 'committed_refs': 193, 'native_receipts': native_refs, 'artifacts': 144, 'artifact_bytes': 4201310, 'indexed_observations': 175},
        {'check': 'unchanged_source_guard_evidence', 'sha256': sha(guards[0]), 'source_files': 160, 'independent_original_DB_opens': 0},
        {'check': 'exact_parameters_and_configuration', 'static_policy_remainder_sha256': sha(canonical(remainder)), 'native_registry_ref': native_ref, 'public_registry_ref': public_ref},
        {'check': 'NEW_checkpoint_SQL', 'table_counts': checkpoint_counts, 'meaning': 'inherited stopped-source history; not new work'},
        {'check': 'NEW_native_registry_SQL', 'counts': native_counts},
        {'check': 'working_file_hash_only', 'current_post_prepare': working, 'historical_custody_publication': publication,
         'hashes_equal': working['sha256'] == publication['sha256'], 'independent_working_SQL': False,
         'working_runtime_counts': 'operator-recorded only; agrees with independently counted inherited checkpoint'},
        {'check': 'new_runtime_binding_files_absent', 'names': absent_bindings},
    ])
    # Rehash every selected input after all checks. This does not dereference paths contained inside guard JSON.
    before = dict(SEEN)
    for path, row in before.items():
        require(witness(Path(path)) == row, 'selected input guard changed: ' + path)
    return {'version': 'independent_resource_preparation_verification_v1', 'status': 'verified_prepared_not_started',
            'source_pin': source_pin, 'checks': CHECKS, 'selected_inputs_unchanged': True,
            'external_preparation_process_receipt': witness(preparation_invocation),
            'external_preparation_exit_code': invocation['exit_code'],
            'witnesses': [SEEN[path] for path in sorted(SEEN)],
            'limits': ['exact relevant closed fields/relationships checked; full JSON Schema validation is recorded operator evidence',
                       'no application imports, preparation, episode/model/HTTP/native/test calls',
                       'SQL only NEW immutable checkpoint and NEW inactive native registry; every connection explicitly closed',
                       'NEW working database SQL not performed; its preserved counts remain recorded operator evidence',
                       'NEW working record-resolution assertions remain C producer evidence; immutable checkpoint rows are independently hashed/counted',
                       'NEW statistics history is not queried; this preparation review does not claim an observed prospective forecast',
                       'original/active databases and private provider logs never opened',
                       'raw inherited observations hashed by index only; no new observations or credit inferred',
                       'historical custody working hash and current post-prepare working hash are distinct witnesses even when equal',
                       'preparation does not demonstrate scientific child/parent behavior or whole-goal completion']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preparation-invocation', type=Path, required=True)
    arguments = parser.parse_args()
    sys.dont_write_bytecode = True
    output = arguments.output
    no_links(output)
    require(output.parent.is_dir() and all(not output.is_relative_to(root) for root in (PLAN, BASELINE, RESOURCE_PLAN, RUN, ENGINEERING, ROOT_PREPARATION_EVIDENCE, CODE)), 'output must be new and outside inputs')
    require(not os.path.lexists(output), 'exclusive new output required')
    try:
        report = verify(arguments.preparation_invocation)
        exit_code = 0
    except Exception as error:
        report = {'version': 'independent_resource_preparation_verification_v1', 'status': 'verification_failed',
                  'error_type': type(error).__name__, 'error': str(error), 'completed_checks': CHECKS,
                  'witnesses': [SEEN[path] for path in sorted(SEEN)], 'no_application_calls': True}
        exit_code = 1
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(canonical(report) + b'\n')
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({'status': report['status'], 'output': str(output), 'sha256': sha(canonical(report) + b'\n')}))
    raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
