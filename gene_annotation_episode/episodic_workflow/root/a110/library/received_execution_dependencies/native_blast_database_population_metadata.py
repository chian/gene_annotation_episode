from __future__ import annotations
from copy import deepcopy
import json
import math
import re
SEQUENCE_POPULATION_METADATA_SCHEMA = 'native_blast_database_sequence_metadata_v3'
_PREFIX = 'blast_database_population_'
_RECORD_FIELDS = {'source_ref', 'artifact_ref', 'sha256', 'size_bytes', 'pointer', 'value'}

def _fail(suffix):
    raise ValueError(_PREFIX + suffix)

def _copy(value, active=None):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list or (type(value) is dict and all((type(k) is str for k in value))):
        active = set() if active is None else active
        if id(value) in active:
            _fail('finite_json_required')
        active.add(id(value))
        try:
            return [_copy(v, active) for v in value] if type(value) is list else {k: _copy(v, active) for k, v in value.items()}
        finally:
            active.remove(id(value))
    _fail('finite_json_required')

def _token(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def _pointer(value):
    return type(value) is str and (not value or value.startswith('/')) and (re.search('~(?![01])', value) is None)

def _at(value, pointer):
    if not _pointer(pointer):
        raise ValueError('pointer_invalid')
    for part in pointer.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        if type(value) is list:
            if re.fullmatch('0|[1-9][0-9]*', part) is None:
                raise ValueError('pointer_index_invalid')
            value = value[int(part)]
        else:
            value = value[part]
    return value

def _records(value):
    value = _copy(value)
    if type(value) is not list:
        _fail('context_fields_invalid')
    for row in value:
        if type(row) is not dict or set(row) != _RECORD_FIELDS or any((type(row[k]) is not str or not row[k] or '\x00' in row[k] for k in ('source_ref', 'artifact_ref'))) or (type(row['sha256']) is not str) or (re.fullmatch('[a-f0-9]{64}', row['sha256']) is None) or (type(row['size_bytes']) is not int) or (row['size_bytes'] < 0) or (not _pointer(row['pointer'])):
            _fail('context_fields_invalid')
    return value

def native_blast_database_sequence_population_metadata_schema() -> dict:
    """The exact v2 record-locator fields plus required per-search assertions."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_database_metadata import _SEQUENCE_SCHEMA_V2, _TOKEN, _PROV, _object, _array
    schema = deepcopy(_SEQUENCE_SCHEMA_V2)
    schema['properties']['schema'] = {'enum': [SEQUENCE_POPULATION_METADATA_SCHEMA]}
    unit = schema['properties']['searches']['items']
    association = _object(association_key=_TOKEN, database_key=_TOKEN, assertion_source=_PROV, census_source=_PROV)
    association['x-wire'] = 'population_association'
    unit['properties']['database_population_associations'] = _array(association)
    unit['required'].append('database_population_associations')
    profile = unit['properties']['database_profile']['anyOf'][0]
    profile['properties']['source'] = {**_TOKEN, 'x-wire': 'population_source'}
    return schema

def _job(prepared):
    request = prepared['invocation']['request']
    keys = [k for k in ('native_blast_standard_database', 'native_blast_database') if k in request]
    if len(keys) != 1:
        _fail('context_fields_invalid')
    return (keys[0], request[keys[0]])

def _bundle(prepared, records):
    key, _ = _job(prepared)
    version = key + '_bundle_v1'
    rows = [r for r in records if r['pointer'] == '' and type(r['value']) is dict and (r['value'].get('version') == version) and (r['value'].get('requested_job') == prepared['invocation']['request'])]
    rows = list({_token(r): r for r in rows}.values())
    return rows[0] if len(rows) == 1 else None

def _selected(prepared, records, database_key):
    job_key, job = _job(prepared)
    bundle_record = _bundle(prepared, records)
    selected = [d for d in job['databases'] if d['database_key'] == database_key]
    if bundle_record is None or len(selected) != 1:
        return None
    db, bundle = (selected[0], bundle_record['value'])
    if db['role'] != 'target' or db['identity']['preparation_type'] != 'sequence_database':
        return None
    index = job['databases'].index(db)
    pointer = f'/requested_job/{job_key}/databases/{index}'
    custody = [r for r in prepared['source_relations'] if r['pointer'] == pointer and (job_key != 'native_blast_standard_database' or r.get('kind') == 'database')]
    captures = [r for r in bundle.get('database_manifest', []) if r['database_key'] == database_key]
    if len(custody) != 1 or custody[0]['status'] != 'available' or len(captures) != 1:
        return None
    capture = captures[0]
    artifacts = [r for r in bundle['artifacts'] if r['artifact_key'] == capture['manifest_artifact_key']]
    if len(artifacts) != 1 or artifacts[0]['role'] != 'database_manifest' or artifacts[0]['database_key'] != database_key or (capture['native_paths'] != db['native_paths']) or any((artifacts[0][k] != db['manifest_file'][k] for k in ('sha256', 'size_bytes'))) or (len(capture['checks']) != len(db['manifest']['files'])) or any((r['status'] != 'verified' or r['observed_sha256'] != r['expected_sha256'] for r in capture['checks'])) or (sorted(((r['path'], r['expected_sha256'], r['size_bytes']) for r in capture['checks'])) != sorted(((r['path'], r['sha256'], r['size_bytes']) for r in db['manifest']['files']))):
        return None
    manifests = [r for r in records if r['pointer'] == '' and r['value'] == db['manifest'] and all((r[k] == db['manifest_file'][k] for k in ('sha256', 'size_bytes')))]
    manifests = list({_token(r): r for r in manifests}.values())
    if len(manifests) != 1:
        return None
    argv, requested = (bundle.get('realized_argv', []), prepared['invocation']['request'].get('argv', []))
    if argv.count('-db') != 1 or requested.count('-db') != 1:
        return None
    try:
        operand = argv[argv.index('-db') + 1]
        original = requested[requested.index('-db') + 1]
    except IndexError:
        return None
    if operand != original or operand != ' '.join(db['native_paths']):
        return None
    return dict(native_database_operand=operand, native_paths=deepcopy(db['native_paths']), identity=deepcopy(db['identity']), manifest_sha256=manifests[0]['sha256'], manifest_size_bytes=manifests[0]['size_bytes'], invocation_source=dict(source_ref=bundle_record['source_ref'], pointer=f'/requested_job/{job_key}'), manifest_source=dict(source_ref=manifests[0]['source_ref'], pointer='/identity'))

def _provenance(original, declaration, document):
    source = document['source_ref'] if document is not None else declaration['artifact']['source_ref'] if declaration is not None and declaration['artifact']['kind'] == 'received' else original['source_ref']
    return dict(source_ref=source, pointer=original['pointer'])

def _record(records, document, provenance):
    if document is None or document['format'] != 'json':
        return None
    rows = [r for r in records if all((r[k] == document[k] for k in ('source_ref', 'artifact_ref', 'sha256', 'size_bytes'))) and r['pointer'] == provenance['pointer']]
    rows = list({_token(r): r for r in rows}.values())
    return rows[0] if len(rows) == 1 else None

def _validate_retained_records(validation):
    """Check the saved record envelope internally, without decoding any bytes."""
    records = _records(validation['population_source_records'])
    for record in records:
        roots = [r for r in records if r['pointer'] == '' and all((r[k] == record[k] for k in ('source_ref', 'artifact_ref', 'sha256', 'size_bytes')))]
        if not roots or any((_token(r['value']) != _token(roots[0]['value']) for r in roots)):
            _fail('saved_relation_conflict')
        try:
            value = _at(roots[0]['value'], record['pointer'])
        except (KeyError, IndexError, TypeError, ValueError):
            _fail('saved_relation_conflict')
        if _token(value) != _token(record['value']):
            _fail('saved_relation_conflict')
    if validation['status'] != 'valid':
        return records
    payload = validation['payload']
    owners = [r for r in records if r['artifact_ref'] == validation['artifact_ref'] and r['pointer'] == '']
    if not owners or any((r['sha256'] != validation['sha256'] or r['value'] != payload for r in owners)):
        _fail('saved_relation_conflict')
    documents = {d['document_key']: d for d in validation['normalized']['documents']}
    for ui, unit in enumerate(payload['searches']):
        for ai, row in enumerate(unit['database_population_associations']):
            for field in ('assertion_source', 'census_source'):
                prov = row[field]
                doc = documents.get(prov['source_ref'])
                if doc is None or doc['format'] != 'json':
                    continue
                root = _record(records, doc, dict(source_ref=doc['source_ref'], pointer=''))
                if root is None:
                    address = f'/searches/{ui}/database_population_associations/{ai}/{field}'
                    if not any((i['pointer'] == address and i['document_key'] == doc['document_key'] and (i['detail_code'] == _PREFIX + 'source_record_invalid') for i in validation['issues'])):
                        _fail('saved_relation_conflict')
                    continue
                try:
                    original = _at(root['value'], prov['pointer'])
                except (KeyError, IndexError, TypeError, ValueError):
                    continue
                actual = _record(records, doc, dict(source_ref=doc['source_ref'], pointer=prov['pointer']))
                if actual is None or _token(actual['value']) != _token(original):
                    _fail('saved_relation_conflict')
    return records

def _checked_records(prepared, source_records):
    supplied = _records(source_records)
    retained = []
    for validation in prepared['metadata']:
        if validation['schema_id'] == SEQUENCE_POPULATION_METADATA_SCHEMA:
            retained.extend(_validate_retained_records(validation))
        elif 'population_source_records' in validation:
            _fail('context_fields_invalid')
    if {_token(r) for r in retained} != {_token(r) for r in supplied}:
        _fail('saved_relation_conflict')
    _validate_population_documents(prepared, supplied)
    return supplied

def _validate_population_documents(prepared, records):
    """Check resolved source addresses against the original wire selections."""
    _, job = _job(prepared)
    bundle_record = _bundle(prepared, records)
    bundle = None if bundle_record is None else bundle_record['value']
    for validation in prepared['metadata']:
        if validation['schema_id'] != SEQUENCE_POPULATION_METADATA_SCHEMA or validation['status'] != 'valid':
            continue
        declarations = {d['document_key']: d for d in validation['payload']['documents']}
        documents = {d['document_key']: d for d in validation['normalized']['documents']}
        if len(documents) != len(validation['normalized']['documents']):
            _fail('saved_relation_conflict')
        selected_keys = {row[field]['source_ref'] for unit in validation['payload']['searches'] for row in unit['database_population_associations'] for field in ('assertion_source', 'census_source')}
        for key in selected_keys:
            original, document = (declarations.get(key), documents.get(key))
            if document is None:
                if original is not None and original['artifact']['kind'] == 'received' and any((r['pointer'] == '' and all((r[k] == original['artifact'][k] for k in ('source_ref', 'artifact_ref', 'sha256', 'size_bytes'))) for r in records)):
                    _fail('saved_relation_conflict')
                continue
            if original is None or any((document[k] != original[k] for k in ('document_key', 'artifact', 'format'))) or set(document) != {'document_key', 'artifact', 'format', 'artifact_key', 'source_ref', 'artifact_ref', 'sha256', 'size_bytes'}:
                _fail('saved_relation_conflict')
            address, expected, captured_key = (original['artifact'], None, None)
            kind = address['kind']
            if kind == 'received':
                if document['artifact_key'] is not None or any((document[k] != address[k] for k in ('source_ref', 'artifact_ref', 'sha256', 'size_bytes'))):
                    _fail('saved_relation_conflict')
                continue
            if bundle is None:
                continue
            try:

                def one(rows):
                    if len(rows) != 1:
                        _fail('saved_relation_conflict')
                    return rows[0]
                if kind == 'input':
                    expected = one([d for d in job['inputs'] if d['input_key'] == address['input_key']])
                    capture = one([d for d in bundle['input_manifest'] if d['input_key'] == address['input_key']])
                    if capture['original_path'] != expected['path']:
                        _fail('saved_relation_conflict')
                    captured_key = capture['artifact_key']
                elif kind == 'output':
                    capture = one([d for d in bundle['output_manifest'] if d['output_key'] == address['output_key']])
                    artifact = one([d for d in bundle['artifacts'] if d['artifact_key'] in capture['artifact_keys'] and d['relative_path'] == address['relative_path']])
                    expected, captured_key = (artifact, artifact['artifact_key'])
                else:
                    database = one([d for d in job['databases'] if d['database_key'] == address['database_key']])
                    capture = one([d for d in bundle['database_manifest'] if d['database_key'] == address['database_key']])
                    if kind == 'database_manifest':
                        expected, captured_key = (database['manifest_file'], capture['manifest_artifact_key'])
                    elif kind == 'database_metadata_manifest':
                        expected = database['manifest']['metadata_manifests'][address['manifest_index']]
                        slot = capture['metadata_manifest_artifacts'][address['manifest_index']]
                        if slot['identity'] != expected:
                            _fail('saved_relation_conflict')
                        captured_key = slot['artifact_key']
                    else:
                        expected = database['manifest']['preparation']['input_manifest'] if address['role'] == 'preparation_input_manifest' else database['manifest']['access']['offline_configuration']
                        slot = one([d for d in capture['sidecar_artifacts'] if d['role'] == address['role']])
                        if slot['identity'] != expected:
                            _fail('saved_relation_conflict')
                        captured_key = slot['artifact_key']
                if document['artifact_key'] != captured_key or expected is None or any((document[k] != expected[k] for k in ('sha256', 'size_bytes'))):
                    _fail('saved_relation_conflict')
            except (KeyError, IndexError, TypeError):
                _fail('saved_relation_conflict')

def _population_search_units(search, prepared, records):
    """Find original selected v3 units even if another field could not lower."""
    bundle = _bundle(prepared, records)
    report_keys = {} if bundle is None else {r['output_key']: r['artifact_keys'] for r in bundle['value']['output_manifest']}
    key = search['search_key']
    for validation in prepared['metadata']:
        if validation['schema_id'] != SEQUENCE_POPULATION_METADATA_SCHEMA or validation['status'] != 'valid' or validation['normalized'] is None:
            continue
        payload, normalized = (validation['payload'], validation['normalized'])
        for ui, unit in enumerate(payload['searches']):
            original_pointer = f'/searches/{ui}'
            mappings = [r for r in validation['normalization_map'] if r['payload_pointer'] == original_pointer]
            wire = unit['search_key']
            same_slots = all((wire[k] == key[k] for k in ('member_ordinal', 'report_index', 'search_pointer')))
            matches = same_slots and (report_keys.get(wire['output_key']) == [key['artifact_key']] if bundle is not None else bool(mappings and _at(normalized, mappings[0]['normalized_pointer'])['search_key'] == key))
            if not matches:
                continue
            yield (validation, original_pointer, unit)

def _declarations(search, prepared, records):
    """Yield original metadata row addresses, preserving order and duplicates."""
    for validation, original_pointer, unit in _population_search_units(search, prepared, records):
        payload, normalized = (validation['payload'], validation['normalized'])
        documents = {r['document_key']: r for r in normalized['documents']}
        declared = {r['document_key']: r for r in payload['documents']}
        owners = [r for r in records if r['pointer'] == '' and r['artifact_ref'] == validation['artifact_ref'] and (r['sha256'] == validation['sha256']) and (r['value'] == payload)]
        owners = list({_token(r): r for r in owners}.values())
        if not owners:
            _fail('source_record_unavailable')
        for ai, assertion in enumerate(unit['database_population_associations']):
            pointer = original_pointer + f'/database_population_associations/{ai}'
            for owner in owners:
                yield (validation, pointer, assertion, dict(source_ref=owner['source_ref'], pointer=pointer), declared, documents)

def validate_native_blast_database_population_associations(association_inputs, *, search, prepared_inputs, source_records, database_profile) -> list[dict]:
    """Compare saved association fields to original declarations and records."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_database_population_associations import validate_blast_database_population_context
    prepared, search = (_copy(prepared_inputs), _copy(search))
    records = _checked_records(prepared, source_records)
    profiles = [u['database_profile'] for v in prepared['metadata'] if v['consumer'] == 'sequence_database' and v['status'] == 'valid' and (v['normalized'] is not None) for u in v['normalized']['searches'] if u['search_key'] == search['search_key'] and u['database_profile'] is not None]
    if _job(prepared)[0] == 'native_blast_standard_database':
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_standard_database_metadata import _search_status
        if _search_status(search, prepared)[0] != 'available':
            profiles = []
    unique_profiles = {_token(p): p for p in profiles}
    if database_profile != (next(iter(unique_profiles.values())) if len(unique_profiles) == 1 else None):
        _fail('saved_relation_conflict')
    context = validate_blast_database_population_context(dict(schema='blast_database_population_context_v1', search_key=search['search_key'], associations=association_inputs))
    rows = context['associations']
    declarations = list(_declarations(search, prepared, records))
    if len(rows) != len(declarations):
        _fail('saved_relation_conflict')
    for row, (_, _, declaration, owner, declared, documents) in zip(rows, declarations):
        if row['metadata_source'] != owner or row['association_key'] != declaration['association_key'] or row['database_key'] != declaration['database_key'] or (row['search_key'] != search['search_key']) or (row['selected_database'] != _selected(prepared, records, declaration['database_key'])):
            _fail('saved_relation_conflict')
        for name in ('assertion', 'census'):
            original = declaration[name + '_source']
            document = documents.get(original['source_ref'])
            provenance = _provenance(original, declared.get(original['source_ref']), document)
            if row[name + '_source'] != provenance or row[name + '_record'] != _record(records, document, provenance):
                _fail('saved_relation_conflict')
    return rows
