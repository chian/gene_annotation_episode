"""A107 original enrichr received contracts; selected retained metadata/operand declarations.

Original source qualifications and identity checks remain intact; no acquisition or dispatch is added.
"""
from __future__ import annotations
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
