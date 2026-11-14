"""Pure selected native-database contracts; no discovery, I/O or scoring.

The schemas describe custody and invocation, not numerical result sheets. The
accepted contract is workload 327/001, producer boundary N (331).
All public validators return independent finite JSON values and raise ValueError
with a stable native_blast_standard_database_* code. A valid record proves no deployment.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
_PREFIX = 'native_blast_standard_database_'
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
DATABASE_IDENTITY_SCHEMA = _object({'namespace': _STR, 'value': _STR, 'version': _nullable(_STR), 'release': _nullable(_STR), 'scope': _nullable(_STR), 'preparation_type': {'const': 'sequence_database'}, 'source': PROVENANCE_SCHEMA})
SOFTWARE_SCHEMA = _object({'executable': _ABS, 'sha256': _SHA, 'engine_version': _nullable(_STR)})
PREPARED_DATABASE_SCHEMA = _object({'version': {'const': 'native_blast_standard_prepared_database_manifest_v1'}, 'database_key': _KEY, 'kind': {'enum': ['blast_protein_sequence', 'blast_nucleotide_sequence']}, 'identity': DATABASE_IDENTITY_SCHEMA, 'native_paths': _array(_ABS, minItems=1, uniqueItems=True), 'files': _array(_FILE, minItems=1), 'preparation': _object({'method': {'enum': ['makeblastdb', 'publisher_package', 'other_recorded']}, 'preparation_type': {'const': 'sequence_database'}, 'software': _object({'name': _STR, 'version': _nullable(_STR), 'executable_sha256': _nullable(_SHA)}), 'argv': _nullable(_array(_STR, minItems=1)), 'source': PROVENANCE_SCHEMA, 'input_manifest': _nullable(FILE_IDENTITY_SCHEMA), 'receipt': FILE_IDENTITY_SCHEMA}), 'metadata_manifests': _array(FILE_IDENTITY_SCHEMA), 'access': _object({'mode': {'const': 'prepared_local'}, 'offline_configuration': _nullable(FILE_IDENTITY_SCHEMA)}), 'inventory_complete': _BOOL})
DATABASE_OPERAND_SCHEMA = _object({'database_key': _KEY, 'role': {'const': 'target'}, 'kind': PREPARED_DATABASE_SCHEMA['properties']['kind'], 'identity': DATABASE_IDENTITY_SCHEMA, 'native_paths': _array(_ABS, minItems=1, uniqueItems=True), 'manifest_file': FILE_IDENTITY_SCHEMA, 'manifest': PREPARED_DATABASE_SCHEMA})

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
        if kind == 'number':
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                _fail('schema:' + path + ':finite_number')
        if value < schema.get('minimum', -math.inf) or value > schema.get('maximum', math.inf) or ('exclusiveMinimum' in schema and value <= schema['exclusiveMinimum']):
            _fail('schema:' + path + ':range')

def _absolute(value):
    if type(value) is not str or not value.startswith('/') or value.startswith('//') or any((c in value for c in ('\x00', '\n', '\r'))) or ('..' in value.split('/')) or (str(PurePosixPath(value)) != value):
        _fail('absolute_normalized_path_required')

def _relative(value):
    if type(value) is not str or not value or value.startswith('/') or any((c in ('.', '..') for c in value.split('/'))) or any((ord(c) < 32 or ord(c) == 127 for c in value)) or (str(PurePosixPath(value)) != value):
        _fail('confined_relative_path_required')

def _provenance(value):
    _schema(value, PROVENANCE_SCHEMA)
    if value['pointer'] and (not value['pointer'].startswith('/')) or re.search('~(?![01])', value['pointer']):
        _fail('provenance_pointer_invalid')

def _file_identity(value):
    _schema(value, FILE_IDENTITY_SCHEMA)
    _absolute(value['path'])

def _database(db):
    _schema(db, DATABASE_OPERAND_SCHEMA)
    manifest = db['manifest']
    for field in ('database_key', 'kind', 'identity', 'native_paths'):
        if db[field] != manifest[field]:
            _fail('database_manifest_operand_mismatch:' + field)
    _prepared_database_relationships(manifest, extra_identities=[db['manifest_file']])

def _prepared_database_relationships(manifest, *, extra_identities=()):
    """Shared existing manifest relationships, independent of a search operand."""
    _provenance(manifest['identity']['source'])
    _provenance(manifest['preparation']['source'])
    if manifest['preparation']['preparation_type'] != 'sequence_database':
        _fail('database_preparation_type_mismatch')
    if not manifest['inventory_complete']:
        _fail('database_complete_inventory_required')
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
        if not any((p.startswith(native + '.') for p in files)):
            _fail('database_native_path_not_in_inventory')
    identities = [*extra_identities, manifest['preparation']['receipt'], *manifest['metadata_manifests'], *[v for v in (manifest['preparation']['input_manifest'], manifest['access']['offline_configuration']) if v is not None]]
    by_path = {row['path']: (row['sha256'], row['size_bytes']) for row in manifest['files']}
    for row in identities:
        _file_identity(row)
        identity = (row['sha256'], row['size_bytes'])
        if row['path'] in by_path and by_path[row['path']] != identity:
            _fail('database_file_identity_conflict')
        by_path[row['path']] = identity

def validate_standard_prepared_blast_database_manifest(manifest: dict) -> dict:
    """Validate supplied prepared-manifest facts without constructing a search.

    The returned manifest is a detached finite-JSON copy. This reuses the same
    manifest relationships as the original database-operand validator. It neither
    supplies an identity for an unsaved manifest nor checks native file contents.
    """
    manifest = _copy(manifest)
    _schema(manifest, PREPARED_DATABASE_SCHEMA)
    _prepared_database_relationships(manifest)
    return manifest
