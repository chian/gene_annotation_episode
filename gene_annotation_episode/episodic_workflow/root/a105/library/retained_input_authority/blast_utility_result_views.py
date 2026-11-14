"""Pure requested views of retained BLAST utility records.

The shared utility records own native values and their validation. These views
copy selected values; they do not parse, calculate, read files or grant access
to artifacts merely mentioned by a provenance relationship.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.blast_utility_contracts import SCHEMAS, validate_blast_utility_record as core, blast_utility_schema_for_version
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_blast_standard_database_contracts import _copy, _schema
PREFIX = 'native_blast_utility_'
FACT_PREFIX = 'execution.blast_utility_'
IDENTIFIER_NAMESPACES = (PREFIX + 'record', PREFIX + 'occurrence', PREFIX + 'path_record', PREFIX + 'path_section')
SEQUENCE_FIELDS = ('original_sequence', 'normalized_sequence')
VDB_RECORD_FIELDS = ('native_oid', 'native_identifier', 'native_accession', 'native_reported_length', 'native_length_basis', 'returned_symbol_count', 'molecule', 'requested_range', 'effective_range')
VDB_DATABASE_FIELDS = ('vdb_selected_inputs', 'vdb_resolved_paths', 'vdb_sequence_count', 'vdb_total_unclipped_bases', 'vdb_longest_sequence_bases', 'vdb_average_sequence_bases', 'vdb_csra_inputs', 'vdb_reference_sequence_count', 'vdb_reference_total_bases')
VDB_PATH_KINDS = ('vdb', 'vdb_alias', 'blast_db_alias')
DATABASE_FIELDS = tuple((branch['properties']['field_name']['const'] for branch in SCHEMAS['NativeField']['anyOf']))
INTEGRITY_FIELDS = ('observed_checked_count', 'observed_population_count', 'observed_sampled_oids', 'realized_seed', 'diagnostics')
PREPARATION_FIELDS = ('identity', 'software', 'argv', 'native_paths', 'dependencies', 'inventory_complete', 'detail', 'compatibility')
PREPARATION_V2_FIELDS = (*PREPARATION_FIELDS, 'kind', 'database_bindings', 'materializations')
RESULT_VERSIONS = ('blast_sequence_extraction_v1', 'blast_database_inspection_v1', 'blast_database_integrity_v1', 'blast_database_artifact_set_v1', 'blast_database_inspection_v2', 'blast_database_artifact_set_v2')
PREPARED_DATABASE_VERSION = 'native_blast_standard_prepared_database_manifest_v1'
PREPARED_DATABASE_VERSIONS = (PREPARED_DATABASE_VERSION, 'native_blast_prepared_database_manifest_v1')
_STR = {'type': 'string', 'minLength': 1}
_UINT = {'type': 'integer', 'minimum': 0}
_BOOL = {'type': 'boolean'}
_SOURCE = {**_STR, 'format': 'reference', 'x-reference-namespace': 'execution_result'}
_ARTIFACT = {**_STR, 'format': 'reference', 'x-reference-namespace': 'artifact'}
_RECORD = {**_STR, 'format': 'reference', 'x-reference-namespace': IDENTIFIER_NAMESPACES[0]}
_OCCURRENCE = {**_STR, 'format': 'reference', 'x-reference-namespace': IDENTIFIER_NAMESPACES[1]}

def _object(properties, *, required=None):
    return {'type': 'object', 'properties': deepcopy(properties), 'required': list(properties) if required is None else list(required), 'additionalProperties': False}

def _array(items, *, unique=False, **kwargs):
    return {'type': 'array', 'items': deepcopy(items), **({'uniqueItems': True} if unique else {}), **kwargs}

def _nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}

def _enum(values):
    return {'enum': list(values)}

def _with_source(schema, **extra):
    return _object({'source_ref': _SOURCE, **extra, **schema['properties']})
_SLOT_SCHEMA = _object({key: SCHEMAS['ArtifactOccurrence']['properties'][key] for key in ('direction', 'role', 'ordinal')})
_SLOT_SCHEMA['properties']['ordinal'] = {**_nullable(_UINT), 'description': 'Select one original ordinal, or null explicitly for all occurrences of this direction and role.'}
STATUS_SCHEMA = _object({'source_ref': _SOURCE, 'state': _enum(('complete', 'partial', 'failed', 'unavailable')), 'native_state': SCHEMAS['NativeOutcome']['properties']['state'], 'writer_closed': _BOOL, 'inventory_complete': _BOOL, 'result_completeness': _nullable(_enum(('complete_selection', 'partial_selection', 'complete', 'partial', 'unknown')))})
_EXTRACTION_ROW = blast_utility_schema_for_version('blast_sequence_extraction_v1')['properties']['records']['items']['properties']
_SEQUENCE_KEYS = tuple((key for key in _EXTRACTION_ROW if key not in {'record_key', 'matched_selector_ordinals', *SEQUENCE_FIELDS, 'checks', 'failures'}))
SEQUENCE_SCHEMA = _object({'source_ref': _SOURCE, 'database_key': _STR, 'record_key': _RECORD, 'occurrence_id': _OCCURRENCE, 'selector_ordinals': _array(_UINT, unique=True, minItems=1), **{key: _EXTRACTION_ROW[key] for key in _SEQUENCE_KEYS}, 'sequences': _object({key: _EXTRACTION_ROW[key] for key in SEQUENCE_FIELDS}, required=[])})
_INSPECTION_V2 = blast_utility_schema_for_version('blast_database_inspection_v2')['properties']
DATABASE_FIELD_SCHEMA = {'anyOf': [*[_with_source(branch, database_key=_STR) for branch in SCHEMAS['NativeField']['anyOf']], *[_with_source(branch, subject=_INSPECTION_V2['subject']) for branch in SCHEMAS['NativeField']['anyOf']]]}
_INTEGRITY = blast_utility_schema_for_version('blast_database_integrity_v1')['properties']
INTEGRITY_SCHEMA = _object({'source_ref': _SOURCE, 'database_key': _STR, 'scope': _INTEGRITY['scope'], 'fields': _object({key: _INTEGRITY[key] for key in INTEGRITY_FIELDS}, required=[])})
_PREPARATION = blast_utility_schema_for_version('blast_database_artifact_set_v1')['properties']
_PREPARATION_V2 = blast_utility_schema_for_version('blast_database_artifact_set_v2')['anyOf']
PREPARATION_SCHEMA = {'anyOf': [_object({'source_ref': _SOURCE, 'database_key': _STR, 'fields': _object({key: _PREPARATION[key] for key in PREPARATION_FIELDS}, required=[])}), *[_object({'source_ref': _SOURCE, 'database_key': _STR, 'fields': _object({key: branch['properties'][key] for key in PREPARATION_V2_FIELDS}, required=[])}) for branch in _PREPARATION_V2]]}
PREPARED_DATABASE_SCHEMA = _with_source(SCHEMAS['PreparedDatabaseProjection'], database_key=_STR)
CHECK_SCHEMA = _with_source(SCHEMAS['ValidationObservation'])
FAILURE_SCHEMA = _with_source(SCHEMAS['UtilityFailure'])
ARTIFACT_SCHEMA = _with_source(SCHEMAS['ArtifactOccurrence'])
ARTIFACT_SCHEMA['properties']['occurrence_id'] = deepcopy(_OCCURRENCE)
ARTIFACT_SCHEMA['properties']['artifact_ref'] = deepcopy(_ARTIFACT)
SAVED_DATA_SCHEMA = _object({'source_ref': _SOURCE, 'kind': _enum(('result', 'prepared_database')), 'artifact_ref': _ARTIFACT, 'sha256': SCHEMAS['ArtifactOccurrence']['properties']['sha256'], 'size_bytes': _UINT, 'schema': _enum((*RESULT_VERSIONS, *PREPARED_DATABASE_VERSIONS))})
_MISSING_REQUESTS = {'sequence_selector': {'ordinal': _UINT}, 'database_field': {'field_name': _enum(DATABASE_FIELDS)}, 'integrity': {}, 'preparation': {}, 'prepared_database': {}, 'checks': {}, 'artifact': {'slot': _SLOT_SCHEMA}, 'saved_data': {'kind': _enum(('result', 'prepared_database'))}}
MISSING_SCHEMA = _object({'source_ref': _SOURCE, 'request': {'anyOf': [_object({'type': {'const': kind}, **fields}) for kind, fields in _MISSING_REQUESTS.items()]}, 'reason': _enum(('result_unavailable', 'selection_unavailable', 'field_unavailable', 'artifact_unavailable', 'saved_data_unavailable', 'prepared_database_unavailable'))})
_FACT_SCHEMAS = {'status': STATUS_SCHEMA, 'sequences': SEQUENCE_SCHEMA, 'database_fields': DATABASE_FIELD_SCHEMA, 'integrity': INTEGRITY_SCHEMA, 'preparation': PREPARATION_SCHEMA, 'prepared_database': PREPARED_DATABASE_SCHEMA, 'checks': CHECK_SCHEMA, 'failures': FAILURE_SCHEMA, 'missing': MISSING_SCHEMA, 'artifacts': ARTIFACT_SCHEMA, 'saved_data': SAVED_DATA_SCHEMA}
_VDB_EXTRACTION = blast_utility_schema_for_version('blast_sequence_extraction_v2')['properties']
_VDB_ROW = _VDB_EXTRACTION['records']['items']['properties']
_VDB_INSPECTION = blast_utility_schema_for_version('blast_database_inspection_v3')['properties']
_QUALIFICATION = _object({'pointer': {'type': 'string', 'pattern': '^(?:/(?:[^~/]|~[01])*)*$'}, 'reason': _enum(('not_supplied', 'not_applicable', 'native_not_reported', 'native_row_invalid', 'sequence_symbol_invalid', 'sequence_length_conflict', 'supplied_binding_conflict', 'member_unresolved'))})
_QUALIFICATIONS = _array(_QUALIFICATION, unique=True)
_SAMPLE_LINK = SCHEMAS['VDBUtilityContext']['properties']['sample_links']['items']
SEQUENCE_V2_SCHEMA = _object({'version': {'const': PREFIX + 'sequence_fact_v2'}, 'source_ref': _SOURCE, 'database_key': _STR, 'record_key': _RECORD, 'occurrence_id': _OCCURRENCE, 'native_row_ordinal': _UINT, 'line_number': _VDB_ROW['line_number'], 'selector_ordinals': _array(_UINT, unique=True), 'scope': _VDB_EXTRACTION['scope'], 'association': _VDB_ROW['association'], 'completeness': _VDB_ROW['completeness'], 'fields': _object({key: _VDB_ROW[key] for key in VDB_RECORD_FIELDS}, required=[]), 'sequences': _object({key: _VDB_ROW[key] for key in SEQUENCE_FIELDS}, required=[]), 'field_qualifications': _QUALIFICATIONS, 'vdb_identity': _object({'member': _nullable(SCHEMAS['VDBMember']), 'sample_links': _array(_SAMPLE_LINK), 'qualifications': _QUALIFICATIONS})}, required=('version', 'source_ref', 'database_key', 'record_key', 'occurrence_id', 'native_row_ordinal', 'line_number', 'selector_ordinals', 'scope', 'association', 'completeness', 'fields', 'sequences', 'field_qualifications'))
PATH_SCHEMA = _object({'source_ref': _SOURCE, 'database_key': _STR, 'occurrence_id': _OCCURRENCE, 'path_ref': {**_STR, 'format': 'reference', 'x-reference-namespace': IDENTIFIER_NAMESPACES[2]}, **_VDB_INSPECTION['path_records']['items']['properties']})
PATH_SECTION_SCHEMA = _object({'source_ref': _SOURCE, 'database_key': _STR, 'occurrence_id': _OCCURRENCE, 'section_ref': {**_STR, 'format': 'reference', 'x-reference-namespace': IDENTIFIER_NAMESPACES[3]}, 'section_ordinal': _UINT, **_VDB_INSPECTION['path_sections']['items']['properties']})
VDB_CONTEXT_SCHEMA = _object({'source_ref': _SOURCE, 'database_key': _STR, 'context': SCHEMAS['VDBUtilityContext'], 'qualifications': _QUALIFICATIONS})
_VDB_MISSING_REQUESTS = {**{key: value for key, value in _MISSING_REQUESTS.items() if key not in {'integrity', 'preparation', 'prepared_database'}}, 'database_field': {'field_name': _enum(VDB_DATABASE_FIELDS)}, 'saved_data': {'kind': {'const': 'result'}}, 'native_row': {'ordinal': _UINT}, 'native_enumeration': {}, 'path_row': {'ordinal': _UINT}, 'path_population': {'kind': _enum(VDB_PATH_KINDS)}, 'path_section': {'kind': _enum(VDB_PATH_KINDS)}, 'vdb_context': {}}
MISSING_V2_SCHEMA = _object({'version': {'const': PREFIX + 'missing_fact_v2'}, 'source_ref': _SOURCE, 'request': {'anyOf': [_object({'type': {'const': kind}, **fields}) for kind, fields in _VDB_MISSING_REQUESTS.items()]}, 'reason': MISSING_SCHEMA['properties']['reason']})
_VDB_SAVED_DATA_SCHEMA = _object({**SAVED_DATA_SCHEMA['properties'], 'kind': {'const': 'result'}, 'schema': _enum(('blast_sequence_extraction_v2', 'blast_database_inspection_v3'))})
_FACT_SCHEMAS = {**_FACT_SCHEMAS, 'sequences': {'anyOf': [deepcopy(SEQUENCE_SCHEMA), deepcopy(SEQUENCE_V2_SCHEMA)]}, 'missing': {'anyOf': [deepcopy(MISSING_SCHEMA), deepcopy(MISSING_V2_SCHEMA)]}, 'saved_data': {'anyOf': [deepcopy(SAVED_DATA_SCHEMA), _VDB_SAVED_DATA_SCHEMA]}, 'paths': PATH_SCHEMA, 'path_sections': PATH_SECTION_SCHEMA, 'vdb_context': VDB_CONTEXT_SCHEMA}

def _error(code):
    raise ContractError(PREFIX + code)

def _require(condition, code):
    if not condition:
        _error(code)

def _validated(value, schema):
    try:
        value = _copy(value)
        _schema(value, schema)
    except (ValueError, RecursionError) as error:
        raise ContractError(PREFIX + 'result_schema_invalid') from error
    return value

def _text(value):
    _require(type(value) is str and bool(value) and ('\x00' not in value), 'result_reference_invalid')

def _artifact_identity(row):
    _require(row['artifact_ref'] == 'artifact_' + row['sha256'], 'result_artifact_identity_conflict')

def blast_utility_fact_sources() -> dict:
    meanings = {'status': 'Requested delivery, original native outcome and capture completeness are distinct.', 'sequences': 'Selected original extracted identities, sequences, native lengths and returned coordinates.', 'database_fields': 'Requested native database fields with exact source locators, units and qualifications.', 'integrity': 'Requested observed native integrity scope and measurements, never inferred coverage.', 'preparation': 'Requested original database preparation facts, without scientific confidence.', 'prepared_database': 'Explicitly requested existing prepared database manifest or qualified unavailability.', 'checks': 'Selected and relevant global original utility validation observations.', 'failures': 'Original typed utility failures and necessary qualifications.', 'missing': 'Exact requested selections unavailable from the retained utility result.', 'artifacts': 'Only explicitly selected original artifact occurrences and their byte identities.', 'saved_data': 'Only explicitly selected retained utility result or available prepared manifest artifacts.', 'paths': 'Selected literal native path rows and declared dependency ordinals; paths confer no byte access.', 'path_sections': 'Selected original path sections distinguish reported empty populations from absent reports.', 'vdb_context': 'Explicitly selected supplied VDB context and missing identity qualifications, without metadata byte grants.'}
    return {FACT_PREFIX + name: {'type': 'array', 'meaning': meanings[name], 'report_schema': {**_array(schema), 'x-source': FACT_PREFIX + name}} for name, schema in _FACT_SCHEMAS.items()}
FACT_SOURCES = blast_utility_fact_sources()

def validate_blast_utility_fact_values(source: str, values: list) -> list:
    """Validate closed typed facts; the return reader authenticates custody."""
    _require(type(source) is str and source in FACT_SOURCES, 'unknown_fact_source')
    rows = _validated(values, FACT_SOURCES[source]['report_schema'])
    name = source.removeprefix(FACT_PREFIX)
    for row in rows:
        _text(row['source_ref'])
        if name in {'checks', 'failures', 'artifacts'}:
            kind = {'checks': 'ValidationObservation', 'failures': 'UtilityFailure', 'artifacts': 'ArtifactOccurrence'}[name]
            core(kind, {key: value for key, value in row.items() if key != 'source_ref'})
        if name in {'artifacts', 'saved_data'}:
            _artifact_identity(row)
        if name == 'saved_data':
            _require((row['kind'] == 'prepared_database') == (row['schema'] in PREPARED_DATABASE_VERSIONS), 'saved_data_schema_conflict')
        elif name == 'database_fields':
            core('NativeField', {key: value for key, value in row.items() if key not in {'source_ref', 'database_key', 'subject'}})
        elif name == 'sequences':
            _require(row['record_key'] == row['occurrence_id'] + '#/records/' + str(row['native_row_ordinal']), 'sequence_record_identity_conflict')
            if row.get('version') == PREFIX + 'sequence_fact_v2':
                _validate_vdb_sequence_fact(row)
            else:
                _require(row['association'] in {'exact', 'explicit'}, 'sequence_association_unresolved')
        elif name == 'paths':
            _require(row['path_ref'] == row['occurrence_id'] + '#/path_records/' + str(row['native_path_ordinal']), 'path_record_identity_conflict')
            _require(row['native_path'].strip() != 'None' and (not any((c in row['native_path'] for c in '\x00\n\r'))), 'path_record_value_invalid')
            _require(row['section_ordinal'] < len(VDB_PATH_KINDS), 'path_section_identity_conflict')
        elif name == 'path_sections':
            _require(row['section_ref'] == row['occurrence_id'] + '#/path_sections/' + str(row['section_ordinal']), 'path_section_identity_conflict')
            _require((row['header_line_number'] is None) == (row['presence'] == 'not_reported'), 'path_section_presence_conflict')
            _require(row['section_ordinal'] < len(VDB_PATH_KINDS), 'path_section_identity_conflict')
        elif name == 'vdb_context':
            from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.blast_vdb_utility_contracts import validate_vdb_context_relationships
            validate_vdb_context_relationships(row['context'])
            _require(row['qualifications'] == _context_qualifications(row['context']), 'context_qualification_conflict')
        elif name == 'prepared_database':
            projection = core('PreparedDatabaseProjection', {key: row[key] for key in ('status', 'manifest', 'failures')})
            _require(projection['manifest'] is None or projection['manifest']['database_key'] == row['database_key'], 'prepared_database_key_conflict')
        elif name == 'status':
            _require(not row['inventory_complete'] or row['writer_closed'], 'status_inventory_conflict')
    return rows

def _unique(rows):
    result = []
    for row in rows:
        if row not in result:
            result.append(row)
    return result

def _qualifications(rows):
    return sorted(_unique(rows), key=lambda row: (row['pointer'], row['reason']))

def _qualification(pointer, reason='not_supplied'):
    return {'pointer': pointer, 'reason': reason}

def _identity_qualifications(identity, pointer):
    return [_qualification(pointer + '/version')] if identity['version'] is None else []

def _member_qualifications(member, pointer, *, unknown=False):
    result = _identity_qualifications(member['member_identifier'], pointer + '/member_identifier')
    if unknown and member['member_kind'] == 'unknown':
        result.append(_qualification(pointer + '/member_kind'))
    for key, kinds in (('read_identity', {'read'}), ('reference_identity', {'reference', 'wgs_sequence'})):
        detail = member[key]
        prefix = pointer + '/' + key
        if detail is None:
            result.append(_qualification(prefix, 'not_supplied' if member['member_kind'] in kinds else 'not_applicable'))
        elif key == 'read_identity':
            result.extend((_qualification(prefix + '/' + name) for name in ('spot_id', 'read_index') if detail[name] is None))
        else:
            result.extend(_identity_qualifications(detail['identifier'], prefix + '/identifier'))
            result.extend((_qualification(prefix + '/' + name) for name in ('full_length', 'sequence_sha256') if detail[name] is None))
    if member['sample_key'] is None:
        result.append(_qualification(pointer + '/sample_key'))
    return result

def _sample_qualifications(rows, pointer):
    result = []
    for index, row in enumerate(rows):
        prefix, link = (pointer + '/' + str(index) + '/link', row['link'])
        result.extend(_identity_qualifications(link['sample_identifier'], prefix + '/sample_identifier'))
        if link['biosample_identifier'] is None:
            result.append(_qualification(prefix + '/biosample_identifier'))
        else:
            result.extend(_identity_qualifications(link['biosample_identifier'], prefix + '/biosample_identifier'))
    return result

def _context_qualifications(context):
    result = []
    for index, row in enumerate(context['source_inputs']):
        prefix = '/source_inputs/' + str(index)
        if row['dataset_key'] is None:
            result.append(_qualification(prefix + '/dataset_key'))
        if row['dataset_type'] == 'unknown':
            result.append(_qualification(prefix + '/dataset_type'))
        result.extend((_qualification(prefix + '/snapshot/' + key) for key, value in row['snapshot'].items() if value is None))
        for n, identity in enumerate(row['run_identifiers']):
            result.extend(_identity_qualifications(identity, prefix + '/run_identifiers/' + str(n)))
    if context['selection_kind'] is None:
        result.append(_qualification('/selection_kind', 'not_applicable'))
    for index, binding in enumerate(context['entry_identifier_bindings']):
        result.extend(_identity_qualifications(binding['identifier'], '/entry_identifier_bindings/' + str(index) + '/identifier'))
    for index, member in enumerate(context['member_bindings']):
        result.extend(_member_qualifications(member, '/member_bindings/' + str(index), unknown=True))
    result.extend(_sample_qualifications(context['sample_links'], '/sample_links'))
    for index, binding in enumerate(context['dependency_database_bindings']):
        for key in ('version', 'release'):
            if binding['identity'][key] is None:
                result.append(_qualification('/dependency_database_bindings/' + str(index) + '/identity/' + key))
    for index, dependency in enumerate(context['declared_dependencies']):
        for key in ('list_occurrence_id', 'list_entry_ordinal'):
            if dependency[key] is None:
                result.append(_qualification('/declared_dependencies/' + str(index) + '/' + key, 'not_applicable'))
    return _qualifications(result)

def _vdb_identity(member, links, *, member_reason='not_supplied'):
    if member is None:
        qualifications = [_qualification('/member', member_reason), _qualification('/sample_links', 'member_unresolved')]
    else:
        qualifications = _member_qualifications(member, '/member')
        if not links:
            qualifications.append(_qualification('/sample_links'))
        qualifications.extend(_sample_qualifications(links, '/sample_links'))
    return {'member': deepcopy(member), 'sample_links': deepcopy(links), 'qualifications': _qualifications(qualifications)}

def _field_qualifications(fields, length_reason=None):
    reasons = {'native_oid': 'native_not_reported', 'native_accession': 'native_not_reported', 'native_reported_length': 'native_row_invalid', 'requested_range': 'not_applicable', 'effective_range': 'not_applicable', 'returned_symbol_count': length_reason}
    result = []
    for name, value in fields.items():
        if value is None:
            _require(reasons.get(name) is not None, 'sequence_null_qualification_required')
            result.append(_qualification('/fields/' + name, reasons[name]))
    return _qualifications(result)

def _validate_vdb_sequence_fact(row):
    _require(row['line_number'] == row['native_row_ordinal'] + 1, 'sequence_native_location_conflict')
    entries = row['scope']['kind'] == 'selected_entries'
    _require(entries and bool(row['selector_ordinals']) and (row['association'] in {'exact', 'explicit'}) or (not entries and (not row['selector_ordinals']) and (row['association'] == 'not_applicable')), 'sequence_association_unresolved')
    fields = row['fields']
    _require('native_reported_length' not in fields or 'native_length_basis' in fields, 'sequence_native_length_basis_required')
    count_reasons = [q['reason'] for q in row['field_qualifications'] if q['pointer'] == '/fields/returned_symbol_count']
    if 'returned_symbol_count' in fields and fields['returned_symbol_count'] is None:
        _require(len(count_reasons) == 1 and count_reasons[0] in {'native_row_invalid', 'sequence_symbol_invalid', 'sequence_length_conflict'}, 'sequence_null_qualification_required')
    _require(row['field_qualifications'] == _field_qualifications(fields, count_reasons[0] if count_reasons else None), 'sequence_field_qualification_conflict')
    if 'vdb_identity' in row:
        identity = row['vdb_identity']
        member, links = (identity['member'], identity['sample_links'])
        reason = 'not_supplied'
        if member is None:
            reasons = [q['reason'] for q in identity['qualifications'] if q['pointer'] == '/member']
            _require(len(reasons) == 1 and reasons[0] in {'not_supplied', 'supplied_binding_conflict'} and (not links), 'sequence_member_qualification_conflict')
            reason = reasons[0]
        else:
            core('VDBMember', member)
            _require(member['sample_key'] is None and (not links) or (member['sample_key'] is not None and bool(links)), 'sequence_sample_link_conflict')
            _require(all((link['dataset_key'] == member['dataset_key'] and link['link']['sample_key'] == member['sample_key'] for link in links)), 'sequence_sample_link_conflict')
            if links:
                identities = [{k: item['link'][k] for k in ('sample_identifier', 'biosample_identifier')} for item in links]
                _require(all((item == identities[0] for item in identities)), 'sequence_sample_link_conflict')
        _require(identity == _vdb_identity(member, links, member_reason=reason), 'sequence_identity_qualification_conflict')
