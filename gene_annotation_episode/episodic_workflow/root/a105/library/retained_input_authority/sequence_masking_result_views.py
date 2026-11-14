"""Pure selection of saved masking preparation facts, without numerical work.

Native measurements and their missing reasons come from the shared masking
sheet/components or the separate WindowMasker statistics reader. References are
custody operands; returning a quantity never implicitly grants an input file.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_blast_contracts import finite_json_copy
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.sequence_masking_contracts import validate_sequence_masking_record as core
PREFIX = 'native_blast_masking_'
QUANTITIES = ('input_length', 'native_interval_count', 'merged_interval_count', 'masked_positions', 'unmasked_positions', 'changed_positions', 'masked_fraction')
SAVED_SCHEMAS = {'sheet': 'sequence_masking_sheet_v1', 'calculations': 'sequence_masking_components_v1', 'parsed_statistics': 'windowmasker_statistics_v1'}
_STR = {'type': 'string', 'minLength': 1}
_NULL_STR = {'type': ['string', 'null'], 'minLength': 1}
_MACHINE = {'type': 'string', 'pattern': '^[a-z][a-z0-9_]*$'}
_NULL_MACHINE = {'anyOf': [_MACHINE, {'type': 'null'}]}
_UINT = {'type': 'integer', 'minimum': 0}
_NULL_UINT = {'type': ['integer', 'null'], 'minimum': 0}
_SOURCE = {**_STR, 'format': 'reference', 'x-reference-namespace': 'execution_result'}
_ARTIFACT = {**_STR, 'format': 'reference', 'x-reference-namespace': 'artifact'}
_RECORD = {**_STR, 'format': 'reference', 'x-reference-namespace': PREFIX + 'record'}
_OCCURRENCE = {**_STR, 'format': 'reference', 'x-reference-namespace': PREFIX + 'occurrence'}

def _object(properties, *, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required, 'additionalProperties': False}

def _array(items, *, unique=False):
    return {'type': 'array', 'items': items, **({'uniqueItems': True} if unique else {})}
COUNT_SCHEMA = _object({'value': _NULL_UINT, 'unit': {'enum': ['nt', 'aa', 'intervals', 'records']}, 'missing_reason': _NULL_MACHINE})
FRACTION_SCHEMA = _object({'numerator': _NULL_UINT, 'denominator': _NULL_UINT, 'value': {'type': ['number', 'null'], 'minimum': 0, 'maximum': 1}, 'missing_reason': _NULL_MACHINE})
STATUS_SCHEMA = _object({'source_ref': _SOURCE, 'state': {'enum': ['complete', 'partial', 'failed', 'unavailable']}, 'native_state': {'enum': ['succeeded', 'failed', 'incomplete', 'unknown']}, 'output_complete': {'type': 'boolean'}})
ARTIFACT_SCHEMA = _object({'occurrence_id': _OCCURRENCE, 'direction': {'enum': ['input', 'output']}, 'role': {'enum': ['sequences', 'reference_sequences', 'statistics', 'mask', 'stdout', 'stderr']}, 'ordinal': _UINT, 'artifact_ref': _ARTIFACT, 'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'size_bytes': _UINT, 'completeness': {'enum': ['complete', 'partial', 'unknown']}})
QUANTITY_SCHEMA = _object({'source_ref': _SOURCE, 'record_key': _RECORD, 'quantity': {'enum': list(QUANTITIES)}, 'value': {'oneOf': [COUNT_SCHEMA, FRACTION_SCHEMA]}})
CHECK_SCHEMA = _object({'source_ref': _SOURCE, 'name': _MACHINE, 'status': {'enum': ['pass', 'fail', 'unknown', 'not_applicable']}, 'record_key': {'anyOf': [_RECORD, {'type': 'null'}]}, 'reason': _NULL_MACHINE})
FAILURE_SCHEMA = _object({'source_ref': _SOURCE, 'stage': {'enum': ['input', 'parse', 'association', 'native', 'statistics', 'calculation', 'custody']}, 'code': _MACHINE, 'occurrence_id': _NULL_STR, 'record_key': _NULL_STR, 'line_number': {'type': ['integer', 'null'], 'minimum': 1}})
_BINDING_SCHEMA = _object({'kind': {'enum': ['generated', 'supplied']}, 'statistics_occurrence_id': _STR, 'reference_occurrence_ids': _array(_STR, unique=True), 'producer_source_ref': _NULL_STR, 'producer_attempt_id': _NULL_STR, 'provenance': {'enum': ['authenticated_generation', 'caller_declared', 'unknown']}})
_UNIT_SCHEMA = _object({'line_number': {'type': 'integer', 'minimum': 1}, 'unit_code_hex': {'type': 'string', 'pattern': '^[0-9a-fA-F]+$'}, 'unit_code': _UINT, 'native_count': _UINT})
_PERCENTILE_SCHEMA = _object({'line_number': {'type': 'integer', 'minimum': 1}, 'count': _UINT, 'percentage': {'type': 'number'}, 'percentage_lexeme': _STR})
_STAT_FIELDS = {'format_version': _NULL_STR, 'algorithm_version': _NULL_STR, 'unit_length': {'type': ['integer', 'null'], 'minimum': 1, 'maximum': 16}, 'thresholds': _object({k: {'type': ['integer', 'null']} for k in ('t_low', 't_extend', 't_threshold', 't_high')}), 'percentiles': _array(_PERCENTILE_SCHEMA)}
STATISTICS_SCHEMA = _object({'source_ref': _SOURCE, 'statistics_ref': {**_STR, 'format': 'reference', 'x-reference-namespace': PREFIX + 'statistics'}, 'occurrence_id': _STR, 'reference_binding': {'anyOf': [_BINDING_SCHEMA, {'type': 'null'}]}, 'fields': _object(_STAT_FIELDS, required=[]), 'unit_counts': _array(_UNIT_SCHEMA), 'missing_unit_codes': _array(_UINT, unique=True)})
SAVED_DATA_SCHEMA = _object({'source_ref': _SOURCE, 'kind': {'enum': list(SAVED_SCHEMAS)}, 'artifact_ref': _ARTIFACT, 'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'size_bytes': _UINT, 'schema': {'enum': list(SAVED_SCHEMAS.values())}})

def _error(code):
    raise ContractError(PREFIX + code)

def _schema(value, schema):
    from jsonschema import Draft202012Validator
    if next(Draft202012Validator(schema).iter_errors(value), None) is not None:
        _error('result_schema_invalid')

def masking_fact_sources() -> dict:
    entries = {'status': (STATUS_SCHEMA, 'Recorded native state and selected preparation result availability.'), 'artifacts': (ARTIFACT_SCHEMA, 'Only explicitly requested original artifact occurrences.'), 'quantities': (QUANTITY_SCHEMA, 'Exact requested shared masking components; no function confidence.'), 'checks': (CHECK_SCHEMA, 'Selected-record and relevant global saved validation checks.'), 'statistics': (STATISTICS_SCHEMA, 'Requested original WindowMasker native statistics and provenance.'), 'failures': (FAILURE_SCHEMA, 'Retained typed failures relevant to this selected preparation result.'), 'saved_data': (SAVED_DATA_SCHEMA, 'Only explicitly requested immutable shared sheets, components or parsed statistics.')}
    result = {}
    for name, (schema, meaning) in entries.items():
        source = 'execution.masking_' + name
        schema = _array(deepcopy(schema))
        result[source] = {'type': schema['type'], 'meaning': meaning, 'report_schema': {**schema, 'x-source': source}}
    return result
FACT_SOURCES = masking_fact_sources()

def validate_masking_fact_values(source, values):
    """Validate typed public facts; custody and selected scope belong to the host."""
    if type(source) is not str or source not in FACT_SOURCES:
        _error('unknown_fact_source')
    values = finite_json_copy(values)
    _schema(values, FACT_SOURCES[source]['report_schema'])
    name = source.removeprefix('execution.masking_')
    for row in values:
        if name in {'checks', 'failures'}:
            core('Check' if name == 'checks' else 'Failure', {k: v for k, v in row.items() if k != 'source_ref'})
        elif name == 'artifacts':
            core('Occurrence', row)
            if row['artifact_ref'] != 'artifact_' + row['sha256']:
                _error('fact_artifact_identity_conflict')
        elif name == 'quantities':
            core('Fraction' if row['quantity'] == 'masked_fraction' else 'Count', row['value'])
            if row['quantity'] != 'masked_fraction':
                units = {'intervals'} if row['quantity'] in {'native_interval_count', 'merged_interval_count'} else {'nt', 'aa'}
                if row['value']['unit'] not in units:
                    _error('fact_quantity_unit_conflict')
        elif name == 'saved_data':
            if row['schema'] != SAVED_SCHEMAS[row['kind']] or row['artifact_ref'] != 'artifact_' + row['sha256'] or type(row['size_bytes']) is not int:
                _error('fact_saved_data_identity_conflict')
        elif name == 'statistics':
            if row['statistics_ref'] != row['occurrence_id'] + '#/statistics':
                _error('fact_statistics_identity_conflict')
            if row['reference_binding'] is not None:
                core('StatisticsBinding', row['reference_binding'])
                if row['reference_binding']['statistics_occurrence_id'] != row['occurrence_id']:
                    _error('fact_statistics_binding_conflict')
            for unit in row['unit_counts']:
                if any((type(unit[k]) is not int for k in ('line_number', 'unit_code', 'native_count'))) or int(unit['unit_code_hex'], 16) != unit['unit_code']:
                    _error('fact_statistics_unit_invalid')
            if any((type(v) is not int for v in row['missing_unit_codes'])) or set(row['missing_unit_codes']) & {u['unit_code'] for u in row['unit_counts']}:
                _error('fact_statistics_missing_unit_conflict')
            fields = row['fields']
            if 'unit_length' in fields and fields['unit_length'] is not None and (type(fields['unit_length']) is not int):
                _error('fact_statistics_unit_length_invalid')
            if 'thresholds' in fields and any((v is not None and type(v) is not int for v in fields['thresholds'].values())):
                _error('fact_statistics_threshold_invalid')
            for pct in fields.get('percentiles', []):
                try:
                    parsed = float(pct['percentage_lexeme'])
                except ValueError as error:
                    raise ContractError(PREFIX + 'fact_percentile_lexeme_invalid') from error
                if type(pct['line_number']) is not int or type(pct['count']) is not int or type(pct['percentage']) not in (int, float) or (parsed != pct['percentage']):
                    _error('fact_percentile_value_conflict')
    return values
