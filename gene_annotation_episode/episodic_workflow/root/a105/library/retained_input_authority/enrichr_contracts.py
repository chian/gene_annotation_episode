"""One retained Enrichr table and literal saved views of its native cells.

Parsing preserves submitted literals, original response bytes and row positions.
No function submits a request or calculates an enrichment statistic. Deterministic
byte/sheet validation establishes internal consistency, not source permissions,
server identity, a measured universe or correctness of the provider's statistics.
"""
from __future__ import annotations
from copy import deepcopy
import json
import math
REQUEST_VERSION = 'enrichr_request_v1'
SELECTOR_VERSION = 'enrichr_selector_v1'
TABLE_SOURCE = 'execution_enrichr_tables'
ROW_SOURCE = 'execution_enrichr_rows'
PROTOCOLS = ('standard_enrichr_v1', 'speedrichr_v1')
PROFILES = ('documented_odds_v1', 'gget_z_label_v1', 'uninterpreted')
FIELD_POSITIONS = {'rank': 0, 'term': 1, 'p_value': 2, 'statistic_3': 3, 'combined_score': 4, 'overlap': 5, 'adjusted_p_value': 6, 'old_p_value': 7, 'old_adjusted_p_value': 8}
QUALIFICATIONS = ('response_incomplete', 'invalid_utf8', 'invalid_json', 'duplicate_json_key', 'response_not_object', 'library_missing', 'library_null', 'library_not_array', 'nonstandard_numeric_token', 'malformed_row', 'unexpected_native_width', 'legacy_columns_absent', 'extra_columns_retained', 'invalid_rank', 'invalid_term', 'invalid_overlap', 'invalid_probability', 'native_nonfinite', 'numeric_underflow', 'numeric_overflow', 'profile_width_conflict', 'profile_value_conflict', 'interface_definition_conflict', 'declared_documentation_interpretation', 'statistic_uninterpreted')

def _obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def _enum(values, *, nullable=False):
    return {'type': ['string', 'null'] if nullable else 'string', 'enum': [*values, None] if nullable else list(values)}
_ENTRY = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\r\\n]+$'}
_GENES = {'type': 'array', 'items': _ENTRY, 'minItems': 1}
ENRICHR_REQUEST_SCHEMA = _obj({'version': {'type': 'string', 'const': REQUEST_VERSION}, 'protocol_profile': _enum(PROTOCOLS), 'library': deepcopy(_ENTRY), 'genes': deepcopy(_GENES), 'identifier_policy': {'type': 'string', 'const': 'literal_no_mapping'}, 'species_context': {'type': ['string', 'null']}, 'description': {'type': 'string'}, 'background': _obj({'policy': _enum(('service_native', 'supplied')), 'genes': {'type': ['array', 'null'], 'items': deepcopy(_ENTRY), 'minItems': 1}}), 'native_statistic_profile': _enum(PROFILES)})
ENRICHR_SELECTOR_SCHEMA = _obj({'version': {'type': 'string', 'const': SELECTOR_VERSION}, 'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 0}})

def _copy(value):

    def check(item):
        if item is None or type(item) in (bool, int):
            return
        if type(item) is str:
            item.encode('utf-8')
            return
        if type(item) is float:
            if math.isfinite(item):
                return
            raise ValueError('nonfinite_json_number')
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all((type(key) is str for key in item)):
            for key, child in item.items():
                key.encode('utf-8')
                check(child)
            return
        raise ValueError('not_json_data')
    try:
        check(value)
        content = json.dumps(value, allow_nan=False, ensure_ascii=False)
        content.encode('utf-8')
        return json.loads(content)
    except (TypeError, ValueError, OverflowError, UnicodeError, RecursionError) as error:
        raise ValueError('enrichr_finite_json_required') from error

def _require(condition, code):
    if not condition:
        raise ValueError(code)

def _keys(value, expected, code):
    _require(type(value) is dict and set(value) == set(expected), code)

def _entry(value):
    return type(value) is str and bool(value) and ('\r' not in value) and ('\n' not in value)

def validate_enrichr_request(value):
    value = _copy(value)
    _keys(value, ENRICHR_REQUEST_SCHEMA['properties'], 'enrichr_request_invalid')
    _require(value['version'] == REQUEST_VERSION and value['protocol_profile'] in PROTOCOLS and (value['native_statistic_profile'] in PROFILES) and (value['identifier_policy'] == 'literal_no_mapping') and _entry(value['library']) and (type(value['description']) is str) and (value['species_context'] is None or type(value['species_context']) is str) and (type(value['genes']) is list) and (len(value['genes']) > 0) and all((_entry(item) for item in value['genes'])), 'enrichr_request_invalid')
    background = value['background']
    _keys(background, ('policy', 'genes'), 'enrichr_background_invalid')
    _require(background['policy'] == 'service_native' and background['genes'] is None or (background['policy'] == 'supplied' and type(background['genes']) is list and (len(background['genes']) > 0) and all((_entry(item) for item in background['genes']))), 'enrichr_background_invalid')
    _require(background['policy'] != 'supplied' or value['protocol_profile'] == 'speedrichr_v1', 'enrichr_background_protocol_conflict')
    return value

def validate_enrichr_selector(value):
    value = _copy(value)
    _keys(value, ENRICHR_SELECTOR_SCHEMA['properties'], 'enrichr_selector_invalid')
    _require(value['version'] == SELECTOR_VERSION and all((type(value[name]) is int and value[name] >= 0 for name in ('offset', 'limit'))), 'enrichr_selector_invalid')
    return value

def _population():
    return {name: {'state': 'unknown', 'value': None} for name in ('effective_universe', 'mapped_genes', 'testing_family_size', 'server_version')}

def enrichr_fact_sources():
    """Closed literal fact shapes; an API owner must separately authenticate custody."""
    text = {'type': 'string'}
    nullable_text = {'type': ['string', 'null']}
    nullable_number = {'type': ['number', 'null']}
    nullable_integer = {'type': ['integer', 'null'], 'minimum': 0}
    integer = {'type': 'integer', 'minimum': 0}
    boolean = {'type': ['boolean', 'null']}
    kinds = ('absent', 'null', 'number', 'string', 'boolean', 'array', 'object')
    source = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    codes = {'type': 'array', 'uniqueItems': True, 'items': _enum(QUALIFICATIONS)}
    atom = _obj({'position': integer, 'pointer': text, 'kind': _enum(kinds[1:]), 'number_lexeme': nullable_text, 'number_state': _enum(('finite', 'nan', 'positive_infinity', 'negative_infinity', 'underflow', 'overflow'), nullable=True), 'number_value': nullable_number, 'string_value': nullable_text, 'boolean_value': boolean})
    metric = _obj({'position': integer, 'pointer': nullable_text, 'state': _enum(('missing', 'null', 'invalid', 'nonfinite', 'unrepresentable', 'present')), 'value': nullable_number, 'number_lexeme': nullable_text, 'reason': _enum(('native_field_absent', 'native_null', 'expected_native_number', 'nan', 'positive_infinity', 'negative_infinity', 'probability_out_of_range', 'expected_positive_integer', 'numeric_overflow', 'numeric_underflow'), nullable=True), 'unit': _enum(('ordinal_1_based', 'dimensionless'))})
    literal = _obj({'ordinal': integer, 'pointer': nullable_text, 'kind': _enum(kinds), 'state': _enum(('missing', 'null', 'invalid', 'present')), 'value': nullable_text})
    overlap = _obj({'state': _enum(('missing', 'null', 'invalid', 'present')), 'pointer': nullable_text, 'native_kind': _enum(kinds), 'returned_entry_count': nullable_integer, 'entries': {'type': 'array', 'items': literal}})
    interpretation = _obj({'profile': _enum(PROFILES), 'declared_meaning': _enum(('odds_ratio', 'z_score'), nullable=True), 'meaning': _enum(('unknown', 'odds_ratio')), 'claimed_client_label': _enum(('z_score',), nullable=True), 'basis': _enum(('documentation', 'client_label', 'uninterpreted')), 'server_version_verified': {'type': 'boolean', 'const': False}, 'qualification_codes': codes})
    population = _obj({name: _obj({'state': {'type': 'string', 'const': 'unknown'}, 'value': {'type': 'null'}}) for name in _population()})
    window = _obj({'state': _enum(('known', 'unavailable')), 'offset': integer, 'limit': integer, 'selected_row_count': nullable_integer, 'selected_ordinals': {'type': 'array', 'items': integer}, 'has_more_captured_rows': boolean, 'next_offset': nullable_integer, 'all_captured_rows_selected': boolean})
    table = _obj({'version': {'type': 'string', 'const': 'enrichr_table_return_v1'}, 'source_ref': source, 'library': text, 'protocol_profile': _enum(PROTOCOLS), 'species_context': nullable_text, 'identifier_policy': {'type': 'string', 'const': 'literal_no_mapping'}, 'background_policy': _enum(('service_native', 'supplied')), 'native_statistic_profile': _enum(PROFILES), 'response_state': _enum(('decoded', 'invalid_utf8', 'invalid_json')), 'response_complete': {'type': 'boolean'}, 'table_state': _enum(('unavailable', 'invalid', 'missing', 'null', 'rows', 'empty')), 'captured_returned_row_count': nullable_integer, 'window': window, 'population': population, 'qualification_codes': codes})
    row = _obj({'version': {'type': 'string', 'const': 'enrichr_row_return_v1'}, 'source_ref': source, 'ordinal': integer, 'pointer': text, 'native_kind': _enum(kinds[1:]), 'native_width': nullable_integer, 'native_row_value': atom, 'native_cells': {'type': 'array', 'items': atom}, 'term': literal, 'overlap': overlap, 'statistics': _obj({name: metric for name in FIELD_POSITIONS if name not in ('term', 'overlap')}), 'statistic_3_interpretation': interpretation, 'qualification_codes': codes})
    return {name: {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'items': shape, 'x-source': name}} for name, shape, meaning in ((TABLE_SOURCE, table, 'Captured Enrichr response and selected local row window; effective universe, mapped genes, testing-family size and server version remain unknown.'), (ROW_SOURCE, row, 'Literal native Enrichr rows at their original ordinals, with qualified numeric cells and explicitly declared statistic interpretation; no confidence or recomputed enrichment statistic.'))}
