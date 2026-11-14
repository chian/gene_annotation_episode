"""Closed supplied-data masking jobs and one-command compilation.

The pure core owns Operation and every native parameter definition. These
contracts add custody and paths, never masking calculations or native defaults.
"""
from __future__ import annotations
from pathlib import PurePosixPath
import re
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_blast_contracts import finite_json_copy, native_blast_digest
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.sequence_masking_contracts import sequence_masking_operation_schema, validate_sequence_masking_record
MODES = (('dustmasker', 'mask'), ('segmasker', 'mask'), ('windowmasker', 'mask'), ('windowmasker', 'create_counts'), ('convert2blastmask', 'convert_mask'))
PREFIX = 'native_blast_masking_'
JOB_VERSION = PREFIX + 'job_v1'
OWNER_NAME = '.native-blast-masking-owner.json'
PLAN_NAME = 'blast-masking-plan.json'
RESERVED_ENVIRONMENT = frozenset({'TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME'})
_STR = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\u0000]+$'}
_NULL_STR = {'anyOf': [_STR, {'type': 'null'}]}
_SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
_ABS = {'type': 'string', 'pattern': '^/[^\\u0000\\r\\n]+$'}
_UINT = {'type': 'integer', 'minimum': 0}

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
SOFTWARE_SCHEMA = _object({'executable': _ABS, 'sha256': _SHA, 'engine_version': _NULL_STR})
_STATISTICS_BINDING_SCHEMA = _object({'kind': {'enum': ['generated', 'supplied']}, 'statistics_occurrence_id': _STR, 'reference_occurrence_ids': {'type': 'array', 'uniqueItems': True, 'items': _STR}, 'producer_source_ref': _NULL_STR, 'producer_attempt_id': _NULL_STR, 'provenance': {'enum': ['authenticated_generation', 'caller_declared', 'unknown']}})

def native_blast_masking_job_schema(*, program, mode):
    operation = sequence_masking_operation_schema(program=program, mode=mode)
    output_formats = [*operation['properties']['output_format']['enum'], 'text'] if mode == 'convert_mask' else ['interval', 'fasta', 'ascii_statistics', 'text']
    return _object({'version': {'const': JOB_VERSION}, 'operation': operation, 'software': SOFTWARE_SCHEMA, 'environment': {'type': 'object', 'additionalProperties': {'type': 'string'}}, 'operands': {'type': 'array', 'minItems': 1, 'maxItems': 2, 'items': _object({'role': {'enum': ['sequences', 'reference_sequences', 'statistics']}, 'ordinal': {'type': 'integer', 'const': 0}, 'path': _ABS, 'format': {'enum': ['fasta', 'ascii_statistics']}, 'sha256': _SHA, 'size_bytes': _UINT, 'artifact_ref': _NULL_STR})}, 'operand_bindings': {'type': 'array', 'items': _object({'operand_role': {'enum': ['sequences', 'reference_sequences']}, 'operand_ordinal': {'type': 'integer', 'const': 0}, 'record_ordinal': _UINT, 'source_record_ref': _NULL_STR})}, 'statistics_binding': {'anyOf': [_STATISTICS_BINDING_SCHEMA, {'type': 'null'}]}, 'outputs': {'type': 'array', 'minItems': 3, 'maxItems': 3, 'items': _object({'role': {'enum': ['mask', 'statistics', 'stdout', 'stderr']}, 'format': {'enum': output_formats}, 'relative_path': _STR})}})
NATIVE_BLAST_MASKING_JOB_SCHEMA = {'oneOf': [native_blast_masking_job_schema(program=p, mode=m) for p, m in MODES]}
NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA = _object({'argv': {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'pattern': '^[^\\u0000]*$'}}, 'environment': {'type': 'object', 'additionalProperties': {'type': 'string'}}, 'native_blast_masking': NATIVE_BLAST_MASKING_JOB_SCHEMA})

def _error(code):
    raise ContractError(PREFIX + code)

def _schema(value, schema):
    if next(Draft202012Validator(schema).iter_errors(value), None) is not None:
        _error('schema_mismatch')

def _path(value, *, absolute=False):
    if type(value) is not str or not value or any((c in value for c in '\x00\r\n\\')) or value.startswith('//') or ('..' in value.split('/')) or (value in {'.', '/'}):
        _error('normalized_path_required')
    path = PurePosixPath(value)
    if path.is_absolute() != absolute or str(path) != value:
        _error('normalized_path_required')
    return path

def _output_path(value):
    path = _path(value)
    if path.parts[0] in {'inputs', 'tmp', 'cache', 'bundle.json', OWNER_NAME, PLAN_NAME, 'native.json', 'invoke.json'} or path.parts[0].startswith('.'):
        _error('reserved_output_path')
    return path

def validate_native_blast_masking_job(value):
    job = finite_json_copy(value)
    _schema(job, NATIVE_BLAST_MASKING_JOB_SCHEMA)
    op = validate_sequence_masking_record('Operation', job['operation'])
    _path(job['software']['executable'], absolute=True)
    if op['engine_version'] != job['software']['engine_version']:
        _error('software_version_conflict')
    for key, value in job['environment'].items():
        if re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', key) is None or '\x00' in value:
            _error('environment_invalid')
        if key in RESERVED_ENVIRONMENT:
            _error('reserved_environment')
    expected = {'reference_sequences'} if op['mode'] == 'create_counts' else {'sequences', 'statistics'} if op['program'] == 'windowmasker' else {'sequences'}
    operands = {}
    for row in job['operands']:
        if row['role'] in operands or type(row['ordinal']) is not int or type(row['size_bytes']) is not int:
            _error('operand_identity_invalid')
        operands[row['role']] = row
        _path(row['path'], absolute=True)
        if row['format'] != ('ascii_statistics' if row['role'] == 'statistics' else 'fasta'):
            _error('operand_format_conflict')
    if set(operands) != expected:
        _error('operand_roles_conflict')
    seen = set()
    for row in job['operand_bindings']:
        key = (row['operand_role'], row['record_ordinal'])
        if key in seen or row['operand_role'] not in expected or row['operand_role'] == 'statistics' or (type(row['operand_ordinal']) is not int) or (type(row['record_ordinal']) is not int):
            _error('operand_record_binding_conflict')
        seen.add(key)
    binding = job['statistics_binding']
    if (binding is not None) != ('statistics' in operands):
        _error('statistics_binding_required_or_forbidden')
    if binding is not None:
        validate_sequence_masking_record('StatisticsBinding', binding)
    primary = 'statistics' if op['mode'] == 'create_counts' else 'mask'
    roles, paths = (set(), [])
    for row in job['outputs']:
        if row['role'] in roles:
            _error('duplicate_output_role')
        roles.add(row['role'])
        paths.append(_output_path(row['relative_path']))
        if row['format'] != ('text' if row['role'] in {'stdout', 'stderr'} else op['output_format']):
            _error('output_format_conflict')
    if roles != {primary, 'stdout', 'stderr'}:
        _error('one_selected_output_required')
    for i, path in enumerate(paths):
        if any((path == other or path in other.parents or other in path.parents for other in paths[i + 1:])):
            _error('output_path_overlap')
    return job

def compile_native_blast_masking_job(job, *, input_paths, output_directory):
    job = validate_native_blast_masking_job(job)
    roles = {r['role'] for r in job['operands']}
    if type(input_paths) is not dict or set(input_paths) != roles:
        _error('complete_input_path_mapping_required')
    for path in input_paths.values():
        _path(path, absolute=True)
    root = PurePosixPath('.') if output_directory == '.' else _path(output_directory, absolute=True)
    for row in job['outputs']:
        output = root / row['relative_path']
        if str(output) in set(input_paths.values()) | {r['path'] for r in job['operands']} | {job['software']['executable']}:
            _error('output_aliases_input_or_software')
    op = job['operation']
    argv = [job['software']['executable']]
    if op['mode'] == 'create_counts':
        argv += ['-mk_counts', '-in', input_paths['reference_sequences'], '-infmt', 'fasta', '-sformat', 'ascii', '-fa_list', 'false']
    elif op['mode'] == 'convert_mask':
        argv += ['-in', input_paths['sequences'], '-outfmt', op['output_format']]
        if op['parse_seqids']:
            argv.append('-parse_seqids')
    else:
        if op['program'] == 'windowmasker':
            argv += ['-ustat', input_paths['statistics']]
        argv += ['-in', input_paths['sequences'], '-infmt', 'fasta', '-outfmt', op['output_format']]
        if op['parse_seqids']:
            argv.append('-parse_seqids')
        if op['masking_style'] == 'hard':
            argv.append('-hard_masking')
    schema = sequence_masking_operation_schema(program=op['program'], mode=op['mode'])
    for key in schema['properties']['requested_parameters']['properties']:
        value = op['requested_parameters'][key]
        if value is not None:
            argv.extend(['-' + key, str(value).lower() if type(value) is bool else repr(value) if type(value) is float else str(value)])
    output = next((r for r in job['outputs'] if r['role'] not in {'stdout', 'stderr'}))
    argv += ['-out', str(root / output['relative_path'])]
    return argv

def requested_job_from_native_blast_masking(job):
    job = validate_native_blast_masking_job(job)
    return {'argv': compile_native_blast_masking_job(job, input_paths={r['role']: r['path'] for r in job['operands']}, output_directory='.'), 'environment': job['environment'], 'native_blast_masking': job}

def validate_native_blast_masking_requested_job(value):
    request = finite_json_copy(value)
    _schema(request, NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA)
    if native_blast_digest(request) != native_blast_digest(requested_job_from_native_blast_masking(request['native_blast_masking'])):
        _error('requested_job_compiler_mismatch')
    return request
