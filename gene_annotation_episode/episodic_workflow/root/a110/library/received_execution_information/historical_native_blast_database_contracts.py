"""Pure selected native-database contracts; no discovery, I/O or scoring.

The schemas describe custody and invocation, not numerical result sheets. The
accepted contract is workload 310 (001 plus 002), implemented by workload 313.
All public validators return independent finite JSON values and raise ValueError
with a stable native_blast_database_* code. A valid record proves no deployment.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
_PREFIX = 'native_blast_database_'
_STR = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\x00]+$'}
_SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
_INT = {'type': 'integer', 'minimum': 0}
_BOOL = {'type': 'boolean'}
_ABS = {'type': 'string', 'minLength': 1}
_KEY = {'type': 'string', 'minLength': 1, 'pattern': '^[^/\\\\\\x00]+$'}

def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def _array(items, **extra):
    return {'type': 'array', 'items': items, **extra}
PROVENANCE_SCHEMA = _object({'source_ref': _STR, 'pointer': {'type': 'string'}})
FILE_IDENTITY_SCHEMA = _object({'path': _ABS, 'sha256': _SHA, 'size_bytes': _INT, 'artifact_ref': _nullable(_STR)})
_FILE = _object({'path': _ABS, 'sha256': _SHA, 'size_bytes': _INT})
DATABASE_IDENTITY_SCHEMA = _object({'namespace': _STR, 'value': _STR, 'version': _nullable(_STR), 'release': _nullable(_STR), 'scope': _nullable(_STR), 'preparation_type': {'enum': ['sequence_database', 'rps', 'delta', 'unknown']}, 'source': PROVENANCE_SCHEMA})
PREPARED_DATABASE_SCHEMA = _object({'version': {'const': 'native_blast_prepared_database_manifest_v1'}, 'database_key': _KEY, 'kind': {'enum': ['blast_protein_sequence', 'rps_profile', 'delta_profile', 'vdb']}, 'identity': DATABASE_IDENTITY_SCHEMA, 'native_paths': _array(_ABS, minItems=1, uniqueItems=True), 'files': _array(_FILE, minItems=1), 'preparation': _object({'method': {'enum': ['makeblastdb', 'makeprofiledb', 'publisher_package', 'other_recorded']}, 'preparation_type': {'enum': ['sequence_database', 'rps', 'delta', 'vdb']}, 'software': _object({'name': _STR, 'version': _nullable(_STR), 'executable_sha256': _nullable(_SHA)}), 'argv': _nullable(_array(_STR, minItems=1)), 'source': PROVENANCE_SCHEMA, 'input_manifest': _nullable(FILE_IDENTITY_SCHEMA), 'receipt': FILE_IDENTITY_SCHEMA}), 'metadata_manifests': _array(FILE_IDENTITY_SCHEMA), 'access': _object({'mode': {'const': 'prepared_local'}, 'offline_configuration': _nullable(FILE_IDENTITY_SCHEMA)}), 'inventory_complete': _BOOL})
DATABASE_OPERAND_SCHEMA = _object({'database_key': _KEY, 'role': {'enum': ['target', 'domain']}, 'kind': PREPARED_DATABASE_SCHEMA['properties']['kind'], 'identity': DATABASE_IDENTITY_SCHEMA, 'native_paths': _array(_ABS, minItems=1, uniqueItems=True), 'manifest_file': FILE_IDENTITY_SCHEMA, 'manifest': PREPARED_DATABASE_SCHEMA})

def _fail(code):
    raise ValueError(_PREFIX + code)

def _copy(value, _active=None):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list or (type(value) is dict and all((type(k) is str for k in value))):
        active = set() if _active is None else _active
        identity = id(value)
        if identity in active:
            _fail('finite_json_required')
        active.add(identity)
        try:
            if type(value) is list:
                return [_copy(v, active) for v in value]
            return {k: _copy(v, active) for k, v in value.items()}
        finally:
            active.remove(identity)
    _fail('finite_json_required')

def _digest(value):
    return hashlib.sha256(json.dumps(_copy(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def _schema(value, schema, path='$'):
    """Validate the ordinary JSON-schema subset used by these closed records."""
    if 'anyOf' in schema:
        for candidate in schema['anyOf']:
            try:
                _schema(value, candidate, path)
                return
            except ValueError:
                pass
        _fail('schema:' + path + ':anyOf')
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        _fail('schema:' + path + ':const')
    if 'enum' in schema and (not any((type(value) is type(v) and value == v for v in schema['enum']))):
        _fail('schema:' + path + ':enum')
    kind = schema.get('type')
    types = {'object': (dict,), 'array': (list,), 'string': (str,), 'integer': (int,), 'number': (int, float), 'boolean': (bool,), 'null': (type(None),)}
    if kind and type(value) not in types[kind]:
        _fail('schema:' + path + ':type')
    if kind == 'object':
        properties = schema.get('properties', {})
        if set(schema.get('required', [])) - value.keys():
            _fail('schema:' + path + ':required')
        for key, item in value.items():
            child = properties.get(key, schema.get('additionalProperties', True))
            if child is False:
                _fail('schema:' + path + ':additionalProperties')
            if type(child) is dict:
                _schema(item, child, path + '.' + key)
    if kind == 'array':
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', math.inf):
            _fail('schema:' + path + ':length')
        if schema.get('uniqueItems') and len({_digest(v) for v in value}) != len(value):
            _fail('schema:' + path + ':uniqueItems')
        for index, item in enumerate(value):
            _schema(item, schema.get('items', {}), path + '[' + str(index) + ']')
    if kind == 'string':
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', math.inf) or ('pattern' in schema and re.fullmatch(schema['pattern'], value) is None):
            _fail('schema:' + path + ':string')
    if kind in ('number', 'integer'):
        if value < schema.get('minimum', -math.inf) or value > schema.get('maximum', math.inf) or ('exclusiveMinimum' in schema and value <= schema['exclusiveMinimum']):
            _fail('schema:' + path + ':range')

def _absolute(value):
    if type(value) is not str or not value.startswith('/') or value.startswith('//') or any((c in value for c in ('\x00', '\n', '\r'))) or ('..' in value.split('/')) or (str(PurePosixPath(value)) != value):
        _fail('absolute_normalized_path_required')

def _inside(path, root, *, equal=False):
    p, r = (PurePosixPath(path), PurePosixPath(root))
    return r in p.parents or (equal and p == r)

def _provenance(value):
    _schema(value, PROVENANCE_SCHEMA)
    if value['pointer'] and (not value['pointer'].startswith('/')) or re.search('~(?![01])', value['pointer']):
        _fail('provenance_pointer_invalid')

def _file_identity(value):
    _schema(value, FILE_IDENTITY_SCHEMA)
    _absolute(value['path'])

def _prepared_database_sidecars(manifest):
    return [('preparation_input_manifest', manifest['preparation']['input_manifest']), ('offline_configuration', manifest['access']['offline_configuration'])]

def _database(db):
    _schema(db, DATABASE_OPERAND_SCHEMA)
    manifest = db['manifest']
    for field in ('database_key', 'kind', 'identity', 'native_paths'):
        if db[field] != manifest[field]:
            _fail('database_manifest_operand_mismatch:' + field)
    _prepared_database_relationships(manifest, manifest_file=db['manifest_file'])

def _prepared_database_relationships(manifest, *, manifest_file=None):
    """Shared manifest semantics; an operand can add its retained manifest file."""
    _provenance(manifest['identity']['source'])
    _provenance(manifest['preparation']['source'])
    kind = {'blast_protein_sequence': 'sequence_database', 'rps_profile': 'rps', 'delta_profile': 'delta', 'vdb': 'vdb'}[manifest['kind']]
    if manifest['preparation']['preparation_type'] != kind:
        _fail('database_preparation_type_mismatch')
    method = manifest['preparation']['method']
    if method == 'makeblastdb' and kind != 'sequence_database' or (method == 'makeprofiledb' and kind not in {'rps', 'delta'}):
        _fail('database_preparation_method_mismatch')
    if manifest['identity']['preparation_type'] != ('unknown' if kind == 'vdb' else kind):
        _fail('database_identity_preparation_type_mismatch')
    if not manifest['inventory_complete']:
        _fail('database_complete_inventory_required')
    if manifest['kind'] != 'vdb' and len(manifest['native_paths']) != 1:
        _fail('database_single_prepared_prefix_required')
    for path in manifest['native_paths']:
        _absolute(path)
        if any((c.isspace() for c in path)):
            _fail('database_whitespace_path_forbidden')
    files = set()
    for row in manifest['files']:
        _absolute(row['path'])
        if row['path'] in files:
            _fail('database_inventory_duplicate_path')
        files.add(row['path'])
    for native in manifest['native_paths']:
        if not any((p == native or (manifest['kind'] == 'vdb' and _inside(p, native)) or (manifest['kind'] != 'vdb' and p.startswith(native + '.')) for p in files)):
            _fail('database_native_path_not_in_inventory')
    identities = [*([] if manifest_file is None else [manifest_file]), manifest['preparation']['receipt'], *manifest['metadata_manifests'], *[v for _, v in _prepared_database_sidecars(manifest) if v is not None]]
    by_path = {row['path']: (row['sha256'], row['size_bytes']) for row in manifest['files']}
    for row in identities:
        _file_identity(row)
        identity = (row['sha256'], row['size_bytes'])
        if row['path'] in by_path and by_path[row['path']] != identity:
            _fail('database_file_identity_conflict')
        by_path[row['path']] = identity
    if manifest['kind'] == 'vdb' and manifest['access']['offline_configuration'] is None:
        _fail('offline_configuration_unestablished')

def validate_prepared_blast_database_manifest(value: dict) -> dict:
    """Validate a supplied prepared manifest without inventing a search job.

    This is the same relationship validator used by search operands. It checks
    declared identities and closure only; it does not inspect files or establish
    native compatibility, deployment, or application of offline configuration.
    """
    value = _copy(value)
    _schema(value, PREPARED_DATABASE_SCHEMA)
    _prepared_database_relationships(value)
    return value

def validate_native_blast_database_operand(value: dict) -> dict:
    """Validate the actual selected operand and its retained manifest identity."""
    value = _copy(value)
    _database(value)
    return value
