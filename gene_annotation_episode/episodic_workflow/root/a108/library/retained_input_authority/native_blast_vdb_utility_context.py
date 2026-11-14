"""Authenticate selected VDB request claims against original retained bytes.

The qualifier is pure and supplies claims, not authentication. Only the original
bounded worker reads selected documents. Saved consumers validate its frozen
proof without reopening metadata, acquiring data or constructing a search job.
"""
from __future__ import annotations
from copy import deepcopy
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.blast_utility_contracts import SCHEMAS, validate_blast_utility_record as core
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.blast_preparation_contracts import DATABASE_DEPENDENCY_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_blast_contracts import finite_json_copy
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_blast_database_contracts import DATABASE_OPERAND_SCHEMA as ADDITIONAL_DATABASE_SCHEMA, validate_native_blast_database_operand
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.native_blast_standard_database_contracts import DATABASE_OPERAND_SCHEMA, _database
REQUEST_VERSION = 'native_blast_vdb_utility_context_request_v1'
_STR = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\s\\x00]+$'}
_INT = {'type': 'integer', 'minimum': 0}
_POINTER = {'type': 'string', 'pattern': '^(?:/(?:[^~]|~[01])*)?$'}

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def _array(items):
    return {'type': 'array', 'items': items}

def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}
ORIGIN_SCHEMA = {'anyOf': [_object({'kind': {'const': 'request'}}), _object({'kind': {'const': 'selected_json'}, 'document_key': _STR, 'pointer': _POINTER})]}
SAMPLE_ORIGIN_SCHEMA = {'anyOf': [*deepcopy(ORIGIN_SCHEMA['anyOf']), _object({'kind': {'const': 'dataset_sample'}, 'document_key': _STR, 'dataset_pointer': _POINTER, 'sample_index': _INT})]}
JSON_ADDRESS_SCHEMA = {'anyOf': [_object({'kind': {'const': 'database_manifest'}, 'database_key': _STR}), _object({'kind': {'const': 'database_metadata_manifest'}, 'database_key': _STR, 'manifest_index': _INT}), _object({'kind': {'const': 'database_sidecar'}, 'database_key': _STR, 'role': {'enum': ['preparation_input_manifest', 'preparation_receipt']}})]}
DATABASE_FILE_ADDRESS_SCHEMA = _object({'kind': {'const': 'database_file'}, 'database_key': _STR, 'file_index': _INT})
DEPENDENCY_DECLARATION_SCHEMA = {'anyOf': [*deepcopy(ORIGIN_SCHEMA['anyOf']), _object({'kind': {'const': 'alias_directive'}, 'database_key': _STR, 'file_index': _INT, 'directive': {'enum': ['DBLIST', 'VDBLIST']}, 'directive_row_ordinal': _INT, 'token_ordinal': _INT})]}
LIST_REFERENCE_SCHEMA = {'anyOf': [_object({'kind': {'const': 'input'}, 'input_key': _STR}), _object({'kind': {'const': 'database_list'}, 'list_key': _STR})]}

def _request_schema():
    props = deepcopy(SCHEMAS['VDBUtilityContext']['properties'])
    props['source_inputs']['items']['properties']['source'] = deepcopy(ORIGIN_SCHEMA)
    props['entry_identifier_bindings']['items']['properties']['source'] = deepcopy(ORIGIN_SCHEMA)
    member = props['member_bindings']['items']['properties']
    member['provenance'] = deepcopy(ORIGIN_SCHEMA)
    for key in ('read_identity', 'reference_identity'):
        member[key]['anyOf'][0]['properties']['source'] = deepcopy(ORIGIN_SCHEMA)
    props['sample_links']['items']['properties']['link']['properties']['source'] = deepcopy(SAMPLE_ORIGIN_SCHEMA)
    dep = deepcopy(DATABASE_DEPENDENCY_SCHEMA['properties'])
    del dep['list_occurrence_id']
    dep.update(list_ref=_nullable(LIST_REFERENCE_SCHEMA), declaration=DEPENDENCY_DECLARATION_SCHEMA)
    return _object({'version': {'const': REQUEST_VERSION}, 'documents': _array(_object({'document_key': _STR, 'selection': JSON_ADDRESS_SCHEMA})), **{k: props[k] for k in ('source_inputs', 'entry_identifier_bindings', 'member_bindings', 'sample_links')}, 'dependency_databases': _array({'anyOf': [DATABASE_OPERAND_SCHEMA, ADDITIONAL_DATABASE_SCHEMA]}), 'database_lists': _array(_object({'list_key': _STR, 'selection': DATABASE_FILE_ADDRESS_SCHEMA, 'grammar': {'enum': ['vdb_whitespace_tokens', 'blast_database_lines']}})), 'declared_dependencies': _array(_object(dep))})
REQUEST_SCHEMA = _request_schema()

def _error(code):
    raise ContractError('native_blast_utility_' + code)

def _require(condition, code='supplied_binding_conflict'):
    if not condition:
        _error(code)

def _schema(value, schema):
    _require(next(Draft202012Validator(schema).iter_errors(value), None) is None, 'vdb_context_schema_mismatch')

def vdb_utility_context_request_schema() -> dict:
    return deepcopy(REQUEST_SCHEMA)

def vdb_utility_database_operands(job: dict) -> list[dict]:
    return deepcopy([*job['databases'], *job['vdb_context_request']['dependency_databases']])

def _address(job, address):
    databases = {r['database_key']: r for r in vdb_utility_database_operands(job)}
    _require(address['database_key'] in databases)
    db = databases[address['database_key']]
    kind, manifest = (address['kind'], db['manifest'])
    if kind == 'database_manifest':
        role, descriptor = ('manifest', db['manifest_file'])
    elif kind == 'database_metadata_manifest':
        index = address['manifest_index']
        _require(index < len(manifest['metadata_manifests']))
        role, descriptor = ('metadata_manifest', manifest['metadata_manifests'][index])
    elif kind == 'database_file':
        index = address['file_index']
        _require(index < len(manifest['files']))
        role, descriptor = ('database_file', manifest['files'][index])
    else:
        key = {'preparation_input_manifest': 'input_manifest', 'preparation_receipt': 'receipt'}[address['role']]
        descriptor = manifest['preparation'][key]
        _require(descriptor is not None)
        role = 'input_manifest' if key == 'input_manifest' else 'preparation_receipt'
    return {'database_key': db['database_key'], 'role': role, 'original_path': descriptor['path'], 'identity': deepcopy(descriptor)}

def vdb_utility_document_selections(job: dict) -> list[dict]:
    return [{**deepcopy(row), **_address(job, row['selection'])} for row in job['vdb_context_request']['documents']]

def _fields(record, keys):
    _require(type(record) is dict and set(keys) <= record.keys())
    return deepcopy({key: record[key] for key in keys})

def extract_vdb_dataset_claim(record: dict) -> dict:
    return _fields(record, ('dataset_key', 'dataset_type', 'selected_input', 'snapshot', 'run_identifiers'))

def extract_vdb_identity_claim(record: dict) -> dict:
    return _fields(record, ('namespace', 'value', 'version'))

def extract_vdb_read_identity_claim(record: dict) -> dict:
    return _fields(record, ('native_read_name', 'spot_id', 'read_index'))

def extract_vdb_reference_identity_claim(record: dict) -> dict:
    return _fields(record, ('identifier', 'full_length', 'sequence_sha256'))

def extract_vdb_member_claim(record: dict) -> dict:
    result = _fields(record, ('dataset_key', 'member_kind', 'member_identifier', 'relationship', 'read_identity', 'reference_identity', 'sample_key'))
    identifier = record.get('native_identifier')
    described = record.get('native_description')
    if described is not None:
        _require(type(described) is dict and 'id' in described)
        _require(identifier is None or identifier == described['id'])
        identifier = described['id']
    _require(type(identifier) is str and bool(identifier))
    result['native_identifier'] = identifier
    for key, extract in (('read_identity', extract_vdb_read_identity_claim), ('reference_identity', extract_vdb_reference_identity_claim)):
        if result[key] is not None:
            result[key] = extract(result[key])
    return result

def extract_vdb_sample_claim(record: dict) -> dict:
    result = _fields(record, ('dataset_key', 'link'))
    result['link'] = _fields(result['link'], ('sample_key', 'sample_identifier', 'biosample_identifier'))
    return result

def _claims(request):
    for i, row in enumerate(request['source_inputs']):
        path = f'/source_inputs/{i}'
        yield (path + '/source', path, row['source'], extract_vdb_dataset_claim(row), extract_vdb_dataset_claim)
    for i, row in enumerate(request['entry_identifier_bindings']):
        path = f'/entry_identifier_bindings/{i}'
        yield (path + '/source', path, row['source'], row['identifier'], extract_vdb_identity_claim)
    for i, row in enumerate(request['member_bindings']):
        path = f'/member_bindings/{i}'
        yield (path + '/provenance', path, row['provenance'], extract_vdb_member_claim(row), extract_vdb_member_claim)
        for name, extract in (('read_identity', extract_vdb_read_identity_claim), ('reference_identity', extract_vdb_reference_identity_claim)):
            if row[name] is not None:
                nested = path + '/' + name
                yield (nested + '/source', nested, row[name]['source'], extract(row[name]), extract)
    for i, row in enumerate(request['sample_links']):
        path = f'/sample_links/{i}'
        yield (path + '/link/source', path, row['link']['source'], extract_vdb_sample_claim(row), extract_vdb_sample_claim)

def validate_vdb_utility_context_request(value: dict, *, job: dict) -> dict:
    request = finite_json_copy(value)
    _schema(request, REQUEST_SCHEMA)
    job = {**job, 'vdb_context_request': request}
    op = core('Operation', job['operation'])
    _require(op['version'] == 'blast_utility_operation_v3')
    databases = vdb_utility_database_operands(job)
    _require(len({d['database_key'] for d in databases}) == len(databases))
    for db in databases:
        if db['manifest']['version'] == 'native_blast_prepared_database_manifest_v1':
            validate_native_blast_database_operand(db)
        else:
            _database(db)
    documents = {r['document_key']: r for r in request['documents']}
    _require(len(documents) == len(request['documents']))
    vdb_utility_document_selections(job)
    lists = {r['list_key']: r for r in request['database_lists']}
    _require(len(lists) == len(request['database_lists']))
    addresses = []
    for row in lists.values():
        address = _address(job, row['selection'])
        key = (address['database_key'], address['role'], address['original_path'])
        _require(key not in addresses)
        addresses.append(key)
    for _, _, origin, _, _ in _claims(request):
        if origin['kind'] != 'request':
            _require(origin['document_key'] in documents)
    p = op['parameters']
    original = p['database_selection']['inputs']
    _require(len(request['source_inputs']) == len(original))
    for row, selected in zip(request['source_inputs'], original):
        _require(row['ordinal'] == selected['ordinal'] and row['selected_input'] == {'kind': selected['kind'], 'value': selected['value']} and (row['binding_native_path'] == selected['binding_native_path']))
    selection = p['selection']
    selectors = selection['selectors'] if selection is not None and selection['kind'] == 'entries' else []
    _require([r['selector_ordinal'] for r in request['entry_identifier_bindings']] == [r['ordinal'] for r in selectors])
    for row, selected in zip(request['entry_identifier_bindings'], selectors):
        _require(row['identifier']['value'] == selected['value'])
    if selection is not None and selection['kind'] == 'all_references':
        _require(any((r['dataset_type'] == 'csra' for r in request['source_inputs'])))
    datasets = {r['dataset_key'] for r in request['source_inputs'] if r['dataset_key'] is not None}
    _require(len({r['binding_key'] for r in request['member_bindings']}) == len(request['member_bindings']))
    _require(all((r['dataset_key'] in datasets for r in request['sample_links'])))
    for member in request['member_bindings']:
        _require(member['dataset_key'] in datasets)
        _require(member['read_identity'] is None or member['member_kind'] == 'read')
        _require(member['reference_identity'] is None or member['member_kind'] in {'reference', 'wgs_sequence'})
        if member['sample_key'] is not None:
            links = [extract_vdb_sample_claim(r)['link'] for r in request['sample_links'] if r['dataset_key'] == member['dataset_key'] and r['link']['sample_key'] == member['sample_key']]
            _require(bool(links) and all((r == links[0] for r in links)))
    by_database = {d['database_key']: d for d in databases}
    inputs = {r['input_key']: r for r in job['inputs']}
    _require(len({d['ordinal'] for d in request['declared_dependencies']}) == len(request['declared_dependencies']))
    for dep in request['declared_dependencies']:
        _require(dep['database_key'] in by_database)
        db = by_database[dep['database_key']]
        _require(dep['native_path_index'] < len(db['native_paths']))
        file_source = dep['source'] in {'dblist_file', 'vdblist_file'}
        _require((dep['list_ref'] is not None) == file_source and (dep['list_entry_ordinal'] is not None) == file_source)
        if file_source:
            ref = dep['list_ref']
            _require(ref['input_key'] in inputs and inputs[ref['input_key']]['role'] == 'database_list' if ref['kind'] == 'input' else ref['list_key'] in lists)
        origin = dep['declaration']
        if origin['kind'] == 'selected_json':
            _require(origin['document_key'] in documents)
        elif origin['kind'] == 'alias_directive':
            _address(job, {'kind': 'database_file', 'database_key': origin['database_key'], 'file_index': origin['file_index']})
            _require(dep['source'] == origin['directive'].lower())
        else:
            _require(file_source or dep['source'] == 'db')
        if dep['source'] == 'db':
            _require(origin['kind'] == 'request' and any((r['value'] == dep['native_reference'] and r['binding_native_path'] == db['native_paths'][dep['native_path_index']] for r in original)))
    return request
