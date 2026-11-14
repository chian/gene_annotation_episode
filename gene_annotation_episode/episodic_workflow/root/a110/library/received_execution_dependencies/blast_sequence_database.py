from __future__ import annotations
import json
import re
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_database_grader import _DESCRIPTION_BINDING_FIELDS, _SEQUENCE_BINDING_FIELDS, _calculation_context, _binding_fields_valid, _validate_record_locators
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.blast_database_population_associations import validate_blast_database_population_context
SHEET_SCHEMA = 'blast_sequence_database_result_sheet_v1'
SHEET_SCHEMA_V2 = 'blast_sequence_database_result_sheet_v2'
SHEET_SCHEMA_V3 = 'blast_sequence_database_result_sheet_v3'
_SHEET_FIELDS = {'schema', 'search', 'report_source', 'search_binding', 'query_binding', 'reference_metadata', 'description_bindings', 'sequence_identity_bindings', 'target_context', 'database_profile'}
_SEARCH_FIELDS = {'search_key', 'program_context', 'stage', 'iteration', 'normalized', 'row_map', 'operand_binding', 'reporting', 'native', 'issues'}
_KEY_FIELDS = {'artifact_key', 'member_ordinal', 'report_index', 'search_pointer'}
_OPERAND_FIELDS = {'role', 'artifact_key', 'record_ordinal', 'native_id', 'native_title', 'subject_ref', 'molecule', 'length', 'selected_interval', 'identity'}
_CONTEXT_FIELDS = {'execution_program', 'reported_program', 'scientific_mode', 'query_kind', 'reference_kind', 'native_version', 'geometry_program'}

def _keys(value, keys, code):
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(code)

def _text(value):
    return isinstance(value, str) and bool(value.strip())

def _int(value, minimum=0):
    return type(value) is int and value >= minimum

def _pointer(value):
    return isinstance(value, str) and (value == '' or value.startswith('/')) and (re.search('~(?![01])', value) is None)

def _digest(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None

def _provenance(value):
    _keys(value, {'source_ref', 'pointer'}, 'blast_sequence_database_provenance_fields_invalid')
    if not _text(value['source_ref']) or not _pointer(value['pointer']):
        raise ValueError('blast_sequence_database_provenance_invalid')

def _search_key(value):
    _keys(value, _KEY_FIELDS, 'blast_sequence_database_search_key_fields_invalid')
    if not _text(value['artifact_key']) or not _int(value['report_index']) or (value['member_ordinal'] is not None and (not _int(value['member_ordinal']))) or (not _pointer(value['search_pointer'])):
        raise ValueError('blast_sequence_database_search_key_invalid')

def _operand(value):
    _keys(value, _OPERAND_FIELDS, 'blast_sequence_database_operand_fields_invalid')
    if value['role'] not in ('query', 'subject', 'database', 'profile', 'msa', 'checkpoint') or value['molecule'] not in ('dna', 'rna', 'protein', 'unknown') or any((value[key] is not None and (not _text(value[key])) for key in ('artifact_key', 'subject_ref'))) or any((value[key] is not None and (not isinstance(value[key], str)) for key in ('native_id', 'native_title'))) or (value['record_ordinal'] is not None and (not _int(value['record_ordinal']))) or (value['length'] is not None and (not _int(value['length'], 1))):
        raise ValueError('blast_sequence_database_operand_invalid')
    interval = value['selected_interval']
    if interval is not None and (not isinstance(interval, list) or len(interval) != 2 or (not _int(interval[0])) or (not _int(interval[1], 1)) or (interval[0] >= interval[1]) or (value['length'] is not None and interval[1] > value['length'])):
        raise ValueError('blast_sequence_database_operand_interval_invalid')
    identity = value['identity']
    if identity is not None:
        _keys(identity, {'namespace', 'value', 'version'}, 'blast_sequence_database_operand_identity_fields_invalid')
        if not _text(identity['namespace']) or not _text(identity['value']) or (identity['version'] is not None and (not _text(identity['version']))):
            raise ValueError('blast_sequence_database_operand_identity_invalid')

def _validate(sheet):
    version = sheet.get('schema') if isinstance(sheet, dict) else None
    fields = _SHEET_FIELDS | {'database_population_associations'} if version == SHEET_SCHEMA_V3 else _SHEET_FIELDS
    _keys(sheet, fields, 'blast_sequence_database_sheet_fields_invalid')
    if sheet['schema'] not in (SHEET_SCHEMA, SHEET_SCHEMA_V2, SHEET_SCHEMA_V3):
        raise ValueError('blast_sequence_database_sheet_required')
    association_version = 2 if sheet['schema'] in (SHEET_SCHEMA_V2, SHEET_SCHEMA_V3) else 1
    search = sheet['search']
    _keys(search, _SEARCH_FIELDS, 'blast_sequence_database_search_fields_invalid')
    _search_key(search['search_key'])
    if version == SHEET_SCHEMA_V3:
        validate_blast_database_population_context(dict(schema='blast_database_population_context_v1', search_key=search['search_key'], associations=sheet['database_population_associations']))
    _keys(search['program_context'], _CONTEXT_FIELDS, 'blast_sequence_database_program_context_fields_invalid')
    context = search['program_context']
    if any((not _text(context[field]) for field in ('execution_program', 'scientific_mode', 'query_kind', 'reference_kind'))) or any((context[field] is not None and (not _text(context[field])) for field in ('reported_program', 'native_version', 'geometry_program'))):
        raise ValueError('blast_sequence_database_program_context_invalid')
    if search['program_context']['scientific_mode'] != 'database':
        raise ValueError('blast_sequence_database_mode_required')
    normalized = search['normalized']
    _keys(normalized, {'schema', 'mode', 'resource', 'format', 'query', 'search', 'hits', 'native', 'issues'}, 'blast_sequence_database_normalized_fields_invalid')
    if not isinstance(normalized, dict) or normalized.get('schema') != 'blast_normalized_result_v1' or (not isinstance(normalized.get('query'), dict)) or (not isinstance(normalized.get('search'), dict)) or (not isinstance(normalized.get('hits'), list)) or (not isinstance(normalized.get('native'), dict)) or (not isinstance(search['native'], dict)) or (not isinstance(search['issues'], list)):
        raise ValueError('blast_sequence_database_normalized_search_invalid')
    _keys(normalized['query'], {'id', 'title', 'length'}, 'blast_sequence_database_native_query_fields_invalid')
    if any((normalized['query'][field] is not None and (not isinstance(normalized['query'][field], str)) for field in ('id', 'title'))) or (normalized['query']['length'] is not None and (not _int(normalized['query']['length'], 1))):
        raise ValueError('blast_sequence_database_native_query_invalid')
    _keys(normalized['search'], {'program', 'version', 'database', 'parameters', 'statistics', 'request', 'hit_array_present', 'reported_hit_count'}, 'blast_sequence_database_normalized_search_fields_invalid')
    if not isinstance(normalized['search']['request'], dict):
        raise ValueError('blast_sequence_database_native_request_object_required')
    if search['operand_binding'] is not None:
        _operand(search['operand_binding'])
    source = sheet['report_source']
    source_fields = {'artifact_key', 'artifact_ref', 'member_ordinal', 'member_sha256'}
    if version == SHEET_SCHEMA_V3 and isinstance(source, dict) and ('source_ref' in source):
        source_fields.add('source_ref')
    _keys(source, source_fields, 'blast_sequence_database_report_source_fields_invalid')
    if not _text(source['artifact_key']) or not _text(source['artifact_ref']) or ('source_ref' in source and (not _text(source['source_ref']))) or (source['member_ordinal'] is not None and (not _int(source['member_ordinal']))) or (source['member_sha256'] is not None and (not _digest(source['member_sha256']))) or ((source['member_ordinal'] is None) != (source['member_sha256'] is None)):
        raise ValueError('blast_sequence_database_report_source_invalid')
    binding = sheet['search_binding']
    _keys(binding, {'search_key', 'stage', 'biological_round', 'database_identity', 'input_pssm_key', 'provenance'}, 'blast_sequence_database_search_binding_fields_invalid')
    _search_key(binding['search_key'])
    if binding['stage'] not in (None, 'sequence_database', 'domain_database') or (binding['biological_round'] is not None and (not _int(binding['biological_round'], 1))) or (binding['input_pssm_key'] is not None and (not _text(binding['input_pssm_key']))):
        raise ValueError('blast_sequence_database_search_binding_invalid')
    if binding['provenance'] is not None:
        _provenance(binding['provenance'])
    _calculation_context({'reporting': search['reporting'], 'database_identity': binding['database_identity']})
    query = sheet['query_binding']
    if query is not None:
        _keys(query, {'operand', 'axis_kind', 'full_length', 'coordinate_unit', 'sequence_sha256', 'pssm_key', 'master_mapping_ref'}, 'blast_sequence_database_query_binding_fields_invalid')
        _operand(query['operand'])
        if query['axis_kind'] not in ('sequence', 'pssm_master', 'msa_master') or not _int(query['full_length'], 1) or query['coordinate_unit'] not in ('aa', 'nt') or (query['sequence_sha256'] is not None and (not _digest(query['sequence_sha256']))) or (query['pssm_key'] is not None and (not _text(query['pssm_key']))):
            raise ValueError('blast_sequence_database_query_binding_invalid')
        if query['master_mapping_ref'] is not None:
            _provenance(query['master_mapping_ref'])
    if not isinstance(sheet['reference_metadata'], list) or any((not isinstance(row, dict) for row in sheet['reference_metadata'])):
        raise ValueError('blast_sequence_database_metadata_records_required')
    for field in ('target_context', 'database_profile'):
        if sheet[field] is not None and (not isinstance(sheet[field], dict)):
            raise ValueError('blast_sequence_database_' + field + '_object_required')
    for name, fields, locator_field in (('description_bindings', _DESCRIPTION_BINDING_FIELDS, 'metadata_record_locator'), ('sequence_identity_bindings', _SEQUENCE_BINDING_FIELDS, 'record_locator')):
        if not isinstance(sheet[name], list):
            raise ValueError('blast_sequence_database_binding_list_required')
        seen = set()
        for link in sheet[name]:
            _keys(link, {'search_key', 'binding'}, 'blast_sequence_database_link_fields_invalid')
            _search_key(link['search_key'])
            if not _binding_fields_valid(link['binding'], fields, locator_field, association_version):
                raise ValueError('blast_sequence_database_inner_binding_fields_invalid')
            serialized = json.dumps(link, sort_keys=True)
            if serialized in seen:
                raise ValueError('blast_sequence_database_duplicate_source_binding')
            seen.add(serialized)
    _validate_record_locators(sheet['reference_metadata'], [row['binding'] for row in sheet['description_bindings']], [row['binding'] for row in sheet['sequence_identity_bindings']], association_version=association_version)
