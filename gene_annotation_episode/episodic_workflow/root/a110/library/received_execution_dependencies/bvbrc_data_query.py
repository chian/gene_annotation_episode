from __future__ import annotations
from copy import deepcopy as _deepcopy
import math as _math
from jsonschema import Draft202012Validator as _Draft202012Validator
from jsonschema import ValidationError as _ValidationError
from jsonschema.validators import extend as _extend_validator
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError as _ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_fields import FIELD_REGISTRY as _FIELD_REGISTRY
_SCHEMA_DEFS = {'Sort': {'type': 'object', 'properties': {'field': {'$ref': '#/$defs/Field'}, 'direction': {'type': 'string', 'enum': ['asc', 'desc']}}, 'required': ['field', 'direction'], 'additionalProperties': False}, 'Predicate': {'oneOf': [{'type': 'object', 'properties': {'field': {'$ref': '#/$defs/Field'}, 'operator': {'const': 'eq'}, 'value': {'type': ['string', 'number', 'boolean']}}, 'required': ['field', 'operator', 'value'], 'additionalProperties': False}, {'type': 'object', 'properties': {'field': {'$ref': '#/$defs/Field'}, 'operator': {'const': 'in'}, 'value': {'type': 'array', 'items': {'type': ['string', 'number', 'boolean']}, 'minItems': 1}}, 'required': ['field', 'operator', 'value'], 'additionalProperties': False}, {'type': 'object', 'properties': {'field': {'$ref': '#/$defs/Field'}, 'operator': {'const': 'range'}, 'lower': {'anyOf': [{'type': 'number'}, {'type': 'null'}]}, 'lower_inclusive': {'type': 'boolean'}, 'upper': {'anyOf': [{'type': 'number'}, {'type': 'null'}]}, 'upper_inclusive': {'type': 'boolean'}}, 'required': ['field', 'operator', 'lower', 'lower_inclusive', 'upper', 'upper_inclusive'], 'additionalProperties': False}, {'type': 'object', 'properties': {'field': {'$ref': '#/$defs/Field'}, 'operator': {'const': 'exists'}, 'present': {'type': 'boolean'}}, 'required': ['field', 'operator', 'present'], 'additionalProperties': False}]}, 'FacetRequest': {'type': 'object', 'properties': {'field': {'$ref': '#/$defs/Field'}, 'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1}, 'min_count': {'type': 'integer', 'minimum': 0}, 'sort': {'type': 'string', 'enum': ['count', 'index']}, 'include_missing': {'type': 'boolean'}}, 'required': ['field', 'offset', 'limit', 'min_count', 'sort', 'include_missing'], 'additionalProperties': False}, 'DataQuery': {'type': 'object', 'properties': {'version': {'const': 'bvbrc_data_request_v2'}, 'collection': {'type': 'string', 'enum': ['genome', 'genome_feature', 'genome_sequence', 'feature_sequence', 'protein_family_ref', 'protein_feature', 'sequence_feature', 'sequence_feature_vt', 'structured_assertion', 'id_ref', 'taxonomy', 'pathway', 'pathway_ref', 'subsystem', 'subsystem_ref', 'enzyme_class_ref', 'gene_ontology_ref', 'protein_structure', 'ppi', 'experiment', 'bioset', 'bioset_result']}, 'mode': {'type': 'string', 'enum': ['page', 'count', 'facet']}, 'filters': {'type': 'array', 'items': {'$ref': '#/$defs/Predicate'}}, 'fields': {'type': 'array', 'items': {'$ref': '#/$defs/Field'}, 'minItems': 1, 'uniqueItems': True}, 'sort': {'type': 'array', 'items': {'$ref': '#/$defs/Sort'}}, 'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 25000}, 'facet': {'$ref': '#/$defs/FacetRequest'}}, 'required': ['version', 'collection', 'mode', 'filters'], 'additionalProperties': False}, 'EffectiveQuery': {'type': 'object', 'properties': {'version': {'const': 'bvbrc_data_effective_query_v2'}, 'collection': {'type': 'string', 'enum': ['genome', 'genome_feature', 'genome_sequence', 'feature_sequence', 'protein_family_ref', 'protein_feature', 'sequence_feature', 'sequence_feature_vt', 'structured_assertion', 'id_ref', 'taxonomy', 'pathway', 'pathway_ref', 'subsystem', 'subsystem_ref', 'enzyme_class_ref', 'gene_ontology_ref', 'protein_structure', 'ppi', 'experiment', 'bioset', 'bioset_result']}, 'mode': {'type': 'string', 'enum': ['page', 'count', 'facet']}, 'filters': {'type': 'array', 'items': {'$ref': '#/$defs/Predicate'}}, 'fields': {'type': 'array', 'items': {'$ref': '#/$defs/Field'}, 'uniqueItems': True}, 'sort': {'type': 'array', 'items': {'$ref': '#/$defs/Sort'}}, 'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 0, 'maximum': 25000}, 'facet': {'anyOf': [{'$ref': '#/$defs/FacetRequest'}, {'type': 'null'}]}}, 'required': ['version', 'collection', 'mode', 'filters', 'fields', 'sort', 'offset', 'limit', 'facet'], 'additionalProperties': False}, 'QueryPopulation': {'type': 'object', 'properties': {'version': {'const': 'bvbrc_data_population_v1'}, 'base_url': {'type': 'string'}, 'collection': {'type': 'string', 'enum': ['genome', 'genome_feature', 'genome_sequence', 'feature_sequence', 'protein_family_ref', 'protein_feature', 'sequence_feature', 'sequence_feature_vt', 'structured_assertion', 'id_ref', 'taxonomy', 'pathway', 'pathway_ref', 'subsystem', 'subsystem_ref', 'enzyme_class_ref', 'gene_ontology_ref', 'protein_structure', 'ppi', 'experiment', 'bioset', 'bioset_result']}, 'filters': {'type': 'array', 'items': {'$ref': '#/$defs/Predicate'}}, 'visibility': {'const': 'public_unauthenticated'}, 'compiler_version': {'const': 'bvbrc_solr_compiler_v1'}, 'field_contract_version': {'const': 'bvbrc_data_fields_2026_10_24_v1'}, 'population_key': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}}, 'required': ['version', 'base_url', 'collection', 'filters', 'visibility', 'compiler_version', 'field_contract_version', 'population_key'], 'additionalProperties': False}, 'Header': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'value': {'type': 'string'}}, 'required': ['name', 'value'], 'additionalProperties': False}, 'PageSelector': {'type': 'object', 'properties': {'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 25000}}, 'required': ['offset', 'limit'], 'additionalProperties': False}, 'PreparedQuery': {'type': 'object', 'properties': {'version': {'const': 'bvbrc_data_prepared_v2'}, 'service': {'const': 'bvbrc_data'}, 'original_request': {'$ref': '#/$defs/DataQuery'}, 'page_selector': {'anyOf': [{'$ref': '#/$defs/PageSelector'}, {'type': 'null'}]}, 'effective_request': {'$ref': '#/$defs/EffectiveQuery'}, 'query_population': {'$ref': '#/$defs/QueryPopulation'}, 'field_selection': {'type': 'object', 'properties': {'requested_fields': {'anyOf': [{'type': 'array', 'items': {'$ref': '#/$defs/Field'}, 'minItems': 1, 'uniqueItems': True}, {'type': 'null'}]}, 'defaulted_fields': {'type': 'array', 'items': {'$ref': '#/$defs/Field'}, 'uniqueItems': True}, 'custody_added_fields': {'type': 'array', 'items': {'$ref': '#/$defs/Field'}, 'uniqueItems': True}}, 'required': ['requested_fields', 'defaulted_fields', 'custody_added_fields'], 'additionalProperties': False}, 'sort_selection': {'type': 'object', 'properties': {'requested_sort': {'anyOf': [{'type': 'array', 'items': {'$ref': '#/$defs/Sort'}}, {'type': 'null'}]}, 'defaulted_sort': {'type': 'array', 'items': {'$ref': '#/$defs/Sort'}}, 'tie_breaker_added': {'anyOf': [{'$ref': '#/$defs/Sort'}, {'type': 'null'}]}}, 'required': ['requested_sort', 'defaulted_sort', 'tie_breaker_added'], 'additionalProperties': False}, 'request_profile': {'const': 'solr_query_solr_json_v1'}, 'native_request': {'type': 'object', 'properties': {'method': {'const': 'GET'}, 'url': {'type': 'string'}, 'headers': {'type': 'array', 'items': {'$ref': '#/$defs/Header'}}, 'body': {'type': 'null'}, 'query_parameters': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'value': {'type': 'string'}}, 'required': ['name', 'value'], 'additionalProperties': False}}}, 'required': ['method', 'url', 'headers', 'body', 'query_parameters'], 'additionalProperties': False}}, 'required': ['version', 'service', 'original_request', 'page_selector', 'effective_request', 'query_population', 'field_selection', 'sort_selection', 'request_profile', 'native_request'], 'additionalProperties': False}, 'Field': {'type': 'string', 'enum': ['aa_length', 'aa_sequence_md5', 'aa_variant', 'accession', 'active', 'alignments', 'alt_locus_tag', 'analysis_group_1', 'analysis_group_2', 'analysis_method', 'annotation', 'assembly_accession', 'assembly_method', 'bioset_id', 'bioset_type', 'biosets', 'cds', 'cds_mean', 'cds_sd', 'checkm_completeness', 'checkm_contamination', 'chromosome', 'chromosomes', 'class', 'classification', 'classifier_round', 'classifier_score', 'codon_start', 'contig_l50', 'contig_n50', 'contigs', 'core_families', 'core_family_ids', 'counts', 'definition', 'description', 'detection_instrument', 'detection_method', 'e_value', 'ec_description', 'ec_number', 'end', 'entity_count', 'entity_id', 'entity_name', 'entity_type', 'evidence', 'evidence_code', 'exp_id', 'exp_name', 'exp_type', 'family_id', 'family_product', 'family_type', 'feature_id', 'feature_id_a', 'feature_id_b', 'feature_type', 'figfam_id', 'file_path', 'fpkm', 'gc_content', 'gene', 'gene_id', 'genetic_code', 'genome_count', 'genome_ec', 'genome_id', 'genome_id_a', 'genome_id_b', 'genome_length', 'genome_length_mean', 'genome_length_sd', 'genome_name', 'genome_status', 'genomes', 'go', 'go_id', 'go_name', 'hypothetical_cds_ratio_mean', 'hypothetical_cds_ratio_sd', 'id', 'id_type', 'id_value', 'interaction_type', 'interactor_a', 'interactor_b', 'interactor_type_a', 'interactor_type_b', 'interpro_description', 'interpro_id', 'length', 'lineage_ids', 'lineage_names', 'lineage_ranks', 'location', 'locus_tag', 'log2_fc', 'map_location', 'map_name', 'map_type', 'md5', 'measurement_technique', 'method', 'mol_type', 'na_length', 'na_sequence_md5', 'occurrence', 'ontology', 'other_ids', 'other_value', 'p_value', 'parent_id', 'pathway_class', 'pathway_ec', 'pathway_id', 'pathway_name', 'patric_id', 'pdb_accession', 'pdb_id', 'pgfam_id', 'plasmid', 'plasmids', 'plfam_cds_ratio_mean', 'plfam_cds_ratio_sd', 'plfam_id', 'prediction_method', 'product', 'property', 'protein_id', 'public', 'public_identifier', 'public_repository', 'refseq_locus_tag', 'refseq_locus_tag_a', 'refseq_locus_tag_b', 'resolution', 'result_type', 'role_id', 'role_name', 'rrna', 'samples', 'score', 'segments', 'sequence', 'sequence_id', 'sequence_md5', 'sequence_status', 'sequence_type', 'sequencing_depth', 'sequencing_platform', 'sf_category', 'sf_id', 'sf_name', 'sf_sequence', 'sf_sequence_md5', 'sfvt_genome_count', 'sfvt_genome_ids', 'sfvt_id', 'sfvt_sequence', 'sfvt_sequence_md5', 'sfvt_variations', 'source', 'source_aa_sequence', 'source_db', 'source_id', 'source_sf_location', 'start', 'strand', 'subclass', 'subsystem_id', 'subsystem_name', 'superclass', 'taxon_id', 'taxon_id_a', 'taxon_id_b', 'taxon_id_i', 'taxon_lineage_ids', 'taxon_lineage_names', 'taxon_name', 'taxon_rank', 'topology', 'tpm', 'treatment_amount', 'treatment_duration', 'treatment_name', 'treatment_type', 'trna', 'uniprot_id', 'uniprotkb_accession', 'value', 'variant_types', 'version', 'z_score']}}

def _schema(name: str) -> dict:
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$defs': _deepcopy(_SCHEMA_DEFS), '$ref': '#/$defs/' + name}
DATA_QUERY_SCHEMA = _schema('DataQuery')
_TYPE_CHECKER = _Draft202012Validator.TYPE_CHECKER.redefine_many({'integer': lambda _checker, value: type(value) is int, 'number': lambda _checker, value: type(value) in (int, float)})
_Validator = _extend_validator(_Draft202012Validator, type_checker=_TYPE_CHECKER)
_SYNTAX_SCHEMA = _schema('DataQuery')
_SYNTAX_SCHEMA['$defs']['Field'] = {'type': 'string'}
_SYNTAX_SCHEMA['$defs']['DataQuery']['properties']['collection'] = {'type': 'string'}
for _predicate in _SYNTAX_SCHEMA['$defs']['Predicate']['oneOf']:
    for _operand in ('value', 'lower', 'upper'):
        if _operand in _predicate['properties']:
            _predicate['properties'][_operand] = {}
_REQUEST_VALIDATOR = _Validator(_SYNTAX_SCHEMA)

def _finite_copy(value, *, error_code: str='bvbrc_data_request_schema_invalid'):
    """Copy only JSON values; do not coerce tuples, keys, numbers or omissions."""
    active = set()

    def copy(item):
        kind = type(item)
        if item is None or kind in (str, int, bool):
            return item
        if kind is float:
            if not _math.isfinite(item):
                raise _ContractError('bvbrc_nonfinite_number')
            return item
        if kind not in (dict, list) or id(item) in active:
            raise _ContractError(error_code)
        active.add(id(item))
        try:
            if kind is list:
                return [copy(child) for child in item]
            if any((type(key) is not str for key in item)):
                raise _ContractError(error_code)
            return {key: copy(child) for key, child in item.items()}
        finally:
            active.remove(id(item))
    try:
        return copy(value)
    except RecursionError as error:
        raise _ContractError(error_code) from error

def _mode_conflicts(request: dict) -> None:
    mode = request.get('mode')
    if mode in ('count', 'facet') and any((key in request for key in ('fields', 'sort', 'offset', 'limit'))):
        raise _ContractError('bvbrc_mode_parameter_conflict')
    if mode in ('page', 'count') and 'facet' in request or (mode == 'facet' and 'facet' not in request):
        raise _ContractError('bvbrc_mode_parameter_conflict')

def _field_spec(collection: str, field: str) -> dict:
    spec = _FIELD_REGISTRY[collection]['fields'].get(field)
    if spec is None:
        raise _ContractError('bvbrc_unknown_field')
    return spec

def _typed_scalar(value, spec: dict) -> None:
    native_type = spec['solr_type']
    kind = type(value)
    valid = native_type in ('int', 'long') and kind is int or (native_type == 'float' and kind in (int, float)) or (native_type == 'boolean' and kind is bool) or (native_type in ('string', 'string_ci', 'string_raw') and kind is str)
    if not valid:
        raise _ContractError('bvbrc_filter_value_type_mismatch')

def _validate_predicate(collection: str, predicate: dict) -> None:
    spec = _field_spec(collection, predicate['field'])
    operator = predicate['operator']
    if operator in ('eq', 'in'):
        if not spec['exact_filter_supported']:
            raise _ContractError('bvbrc_exact_filter_field_not_supported')
        value = predicate['value']
        if operator == 'in':
            if type(value) is not list or not value:
                raise _ContractError('bvbrc_filter_value_shape_mismatch')
            operands = value
        else:
            if type(value) not in (str, int, float, bool):
                raise _ContractError('bvbrc_filter_value_shape_mismatch')
            operands = [value]
        for operand in operands:
            if type(operand) not in (str, int, float, bool):
                raise _ContractError('bvbrc_filter_value_shape_mismatch')
            _typed_scalar(operand, spec)
    elif operator == 'range':
        if not spec['range_filter_supported']:
            raise _ContractError('bvbrc_range_filter_field_not_supported')
        lower, upper = (predicate['lower'], predicate['upper'])
        for value in (lower, upper):
            if value is not None:
                _typed_scalar(value, spec)
        if lower is None and upper is None or (lower is None and predicate['lower_inclusive']) or (upper is None and predicate['upper_inclusive']) or (lower is not None and upper is not None and (lower > upper)):
            raise _ContractError('bvbrc_invalid_range_bounds')
    elif not spec['existence_filter_supported']:
        raise _ContractError('bvbrc_exists_filter_field_not_supported')

def validate_data_query(request: dict) -> dict:
    """Return a detached, finite original request, without defaults or I/O.

    Syntax errors use bvbrc_data_request_schema_invalid. Recognizable semantic
    failures use the frozen field/type/mode codes; the caller's object is never
    changed, including on error. No name or candidate annotation is required.
    """
    original = _finite_copy(request)
    if type(original) is dict:
        _mode_conflicts(original)
    try:
        _REQUEST_VALIDATOR.validate(original)
    except _ValidationError as error:
        raise _ContractError('bvbrc_data_request_schema_invalid') from error
    collection = original['collection']
    if collection not in _FIELD_REGISTRY:
        raise _ContractError('bvbrc_unknown_collection')
    for field in original.get('fields', []):
        if not _field_spec(collection, field)['stored']:
            raise _ContractError('bvbrc_unknown_field')
    for predicate in original['filters']:
        _validate_predicate(collection, predicate)
    sort_fields = set()
    for sort in original.get('sort', []):
        field = sort['field']
        if field in sort_fields:
            raise _ContractError('bvbrc_duplicate_sort_field')
        sort_fields.add(field)
        if not _field_spec(collection, field)['sort_supported']:
            raise _ContractError('bvbrc_sort_field_not_supported')
    if 'facet' in original:
        if not _field_spec(collection, original['facet']['field'])['facet_supported']:
            raise _ContractError('bvbrc_facet_field_not_supported')
    return original
