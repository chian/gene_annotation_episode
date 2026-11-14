"""Pure custody-neutral envelopes and literal views of the existing CD core.

The numerical sheet and calculator remain in circular_dichroism_measurements.
These contracts validate shapes and relationships and copy retained values;
they never evaluate spectral signs, thermal normalization, midpoint or width.
No validation here establishes a producer, receipt or permission to read a File.
"""
from copy import deepcopy
import json
import math
import re
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority import circular_dichroism_measurements as core
RETURN_VERSION = 'circular_dichroism_summary_v1'
FACT_SOURCE = 'circular_dichroism_summaries'
_SOURCE = re.compile('source_[0-9a-f]{24}\\Z')
_SIGNALS = ('mdeg', 'delta_epsilon', 'unknown')
_FEATURES = {sample: tuple((row[0] for row in rows)) for sample, rows in core.SPECTRAL_FEATURES.items()}
_SIGNS = {row[0]: row[3] for rows in core.SPECTRAL_FEATURES.values() for row in rows}
_WINDOWS = {row[0]: list(row[1:3]) for rows in core.SPECTRAL_FEATURES.values() for row in rows}
_STRUCTURES = {'protein': ('predominantly alpha-helical', 'predominantly beta-sheet', 'mixed or predominantly random coil'), 'nucleic_acid': ('G-quadruplex characteristics', 'B-form characteristics', 'non-standard structure')}
_COOPERATIVITY = ('highly cooperative (sharp transition)', 'moderately cooperative', 'non-cooperative (broad transition)')
ISSUE_CODES = ('expected_object', 'unknown_field', 'unsupported_measurement_schema', 'unsupported_sample_type', 'invalid_sample_key', 'missing_spectrum', 'coordinate_unit_required', 'explicit_signal_unit_required', 'missing_array', 'expected_one_dimensional_list', 'empty_array', 'non_numeric_value', 'nonfinite_value', 'not_exactly_representable_binary64', 'nonpositive_wavelength', 'paired_length_mismatch', 'nonpositive_measurement_wavelength', 'zero_signal_range', 'arithmetic_overflow')
_THERMAL_QUALIFICATIONS = ('signal_unit_unknown', 'thermal_measurement_wavelength_unknown', 'temperature_order_not_strictly_increasing', 'binary64_temperature_steps_not_identical', 'zero_endpoint_temperature_difference')
_METRICS = ('signal_minimum', 'signal_maximum', 'normalization_range', 'sampled_midpoint_index', 'sampled_midpoint_temperature', 'transition_point_count', 'source_endpoint_span_per_point', 'source_transition_width')
_COUNT_NAMES = (*_SIGNS, 'sampled_midpoint_index', 'transition_point_count')
_OVERFLOW_NAMES = ('normalization_range', 'source_endpoint_span_per_point', 'source_transition_width')
_FORMULAS = {**{name: 'count_inclusive_window_strict_sign' for name in _SIGNS}, 'signal_minimum': 'minimum_supplied_signal', 'signal_maximum': 'maximum_supplied_signal', 'normalization_range': 'maximum_minus_minimum', 'sampled_midpoint_index': 'first_nearest_relative_signal_half', 'sampled_midpoint_temperature': 'temperature_at_sampled_midpoint_index', 'transition_point_count': 'count_strict_relative_window_0_2_0_8', 'source_endpoint_span_per_point': 'endpoint_temperature_difference_divided_by_N', 'source_transition_width': 'endpoint_temperature_difference_divided_by_N_times_transition_point_count', 'relative_signal': 'signal_minus_minimum_over_signal_range'}
_UNITS = {**{name: 'sampled_points' for name in _SIGNS}, 'sampled_midpoint_index': 'zero_based_position', 'sampled_midpoint_temperature': 'degC', 'transition_point_count': 'sampled_points', 'source_endpoint_span_per_point': 'degC_per_sampled_point', 'source_transition_width': 'degC', 'relative_signal': 'dimensionless'}
_SIGNAL_METRICS = ('signal_minimum', 'signal_maximum', 'normalization_range')
_CELL_KEYS = {'name', 'value', 'unit', 'state', 'reason', 'formula_id', 'input_fields', 'numerator', 'denominator', 'origin', 'uncertainty'}

def _fail(code):
    raise ValueError('circular_dichroism_' + code)

def _require(condition, code='contract_invalid'):
    if not condition:
        _fail(code)

def _copy(value, ancestors=()):
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str:
        try:
            value.encode('utf-8')
        except UnicodeError:
            _fail('finite_json_required')
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if id(value) in ancestors:
        _fail('finite_json_required')
    if type(value) is list:
        return [_copy(item, (*ancestors, id(value))) for item in value]
    if type(value) is dict and all((type(key) is str for key in value)):
        return {_copy(key): _copy(item, (*ancestors, id(value))) for key, item in value.items()}
    _fail('finite_json_required')

def _same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)

def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys))

def _integer(value, *, nullable=False):
    return value is None and nullable or (type(value) is int and value >= 0)

def _number(value, *, nullable=False):
    return value is None and nullable or (type(value) in (int, float) and (type(value) is int or math.isfinite(value)))

def _enum_list(value, allowed):
    _require(type(value) is list and all((type(item) is str and item in allowed for item in value)) and (len(value) == len(set(value))))

def _cell(value, *, name=None, unit=None, fields=None):
    _closed(value, _CELL_KEYS)
    actual = value['name']
    _require(type(actual) is str and actual in _FORMULAS and (name is None or actual == name))
    expected_unit = unit if actual in _SIGNAL_METRICS else _UNITS[actual]
    _require(value['unit'] == expected_unit and expected_unit is not None and (value['formula_id'] == _FORMULAS[actual]) and (value['origin'] == 'derived_supplied_measurements') and _same(value['uncertainty'], {'state': 'unavailable', 'reason': 'not_supplied_or_estimated'}))
    _require(type(value['input_fields']) is list and all((type(item) is str and item.startswith('/') for item in value['input_fields'])))
    if fields is not None:
        _require(value['input_fields'] == fields)
    if value['state'] == 'invalid_input':
        _require(actual in _OVERFLOW_NAMES and value['value'] is None and (value['reason'] == 'arithmetic_overflow'))
    else:
        _require(value['state'] == 'present' and value['reason'] is None and (_integer(value['value']) if actual in _COUNT_NAMES else _number(value['value'])))
    if actual in (*_SIGNS, 'transition_point_count'):
        _require(_same(value['numerator'], value['value']) and value['denominator'] is None)
    elif actual == 'source_endpoint_span_per_point':
        _require(_number(value['numerator'], nullable=True) and _integer(value['denominator']) and (value['denominator'] > 0))
    elif actual == 'relative_signal':
        _require(_number(value['numerator']) and value['numerator'] >= 0 and _number(value['denominator']) and (value['denominator'] > 0) and (0 <= value['value'] <= 1))
    else:
        _require(value['numerator'] is None and value['denominator'] is None)
    if actual == 'normalization_range' and value['value'] is not None:
        _require(value['value'] >= 0)

def _thermal_cells(rows, unit):
    _require(type(rows) is list)
    names = [row.get('name') if type(row) is dict else None for row in rows]
    _require(names in ([], list(_METRICS[:3]), list(_METRICS)))
    by_name = dict(zip(names, rows))
    for name, row in by_name.items():
        fields = ['/thermal/temperature_data', '/thermal/thermal_cd_data'] if name in {'sampled_midpoint_index', 'source_transition_width'} else ['/thermal/temperature_data'] if name == 'source_endpoint_span_per_point' else ['/thermal/thermal_cd_data']
        if name == 'sampled_midpoint_temperature':
            fields = [f"/thermal/temperature_data/{by_name['sampled_midpoint_index']['value']}", '/thermal/thermal_cd_data']
        _cell(row, name=name, unit=unit, fields=fields)
    return by_name

def validate_circular_dichroism_return(value):
    """Validate a literal frozen summary without a sheet, File or calculator."""
    value = _copy(value)
    _closed(value, ('version', 'source_ref', 'sample_key', 'sample_type', 'spectrum', 'thermal', 'issue_codes', 'qualifications'))
    _require(value['version'] == RETURN_VERSION and type(value['source_ref']) is str and (_SOURCE.fullmatch(value['source_ref']) is not None), 'return_invalid')
    _require(value['sample_key'] is None or (type(value['sample_key']) is str and bool(value['sample_key'].strip())))
    _require(value['sample_type'] in (None, 'protein', 'nucleic_acid') and _same(value['qualifications'], core.QUALIFICATIONS))
    _enum_list(value['issue_codes'], ISSUE_CODES)
    _require(value['issue_codes'] == sorted(value['issue_codes']))
    spectrum = value['spectrum']
    _closed(spectrum, ('state', 'wavelength_count', 'signal_count', 'signal_unit', 'features', 'source_structure_label', 'qualifications'))
    _require(spectrum['state'] in ('present', 'missing_input', 'invalid_input', 'incompatible') and all((_integer(spectrum[key], nullable=True) for key in ('wavelength_count', 'signal_count'))) and (spectrum['signal_unit'] in (None, *_SIGNALS)) and (type(spectrum['features']) is list))
    if spectrum['state'] != 'present':
        _require(spectrum['features'] == [] and spectrum['source_structure_label'] is None and (spectrum['qualifications'] is None))
    else:
        sample = value['sample_type']
        _require(sample in _FEATURES and [row.get('name') if type(row) is dict else None for row in spectrum['features']] == list(_FEATURES[sample]) and (spectrum['source_structure_label'] in _STRUCTURES[sample]) and (spectrum['signal_unit'] in _SIGNALS) and (type(spectrum['wavelength_count']) is int) and (spectrum['wavelength_count'] == spectrum['signal_count'] > 0) and (spectrum['qualifications'] == (['signal_unit_unknown'] if spectrum['signal_unit'] == 'unknown' else [])))
        for row in spectrum['features']:
            _closed(row, ('name', 'window_nm', 'sign', 'count', 'population_count', 'count_denominator'))
            _require(_same(row['window_nm'], _WINDOWS[row['name']]) and row['sign'] == _SIGNS[row['name']] and (row['count_denominator'] is None) and _integer(row['population_count']) and (row['population_count'] <= spectrum['wavelength_count']))
            _cell(row['count'], name=row['name'], fields=['/spectrum/wavelength_data', '/spectrum/cd_signal_data'])
            _require(row['count']['value'] <= row['population_count'])
    thermal = value['thermal']
    _closed(thermal, ('state', 'temperature_count', 'signal_count', 'signal_unit', 'measurement_wavelength', 'summary', 'endpoint_temperature_difference', 'width_divisor_point_count', 'source_cooperativity_label', 'qualifications'))
    _require(thermal['state'] in ('present', 'partial', 'not_supplied', 'invalid_input', 'incompatible') and all((_integer(thermal[key], nullable=True) for key in ('temperature_count', 'signal_count', 'width_divisor_point_count'))) and (thermal['signal_unit'] in (None, *_SIGNALS)) and _number(thermal['endpoint_temperature_difference'], nullable=True))
    wavelength = thermal['measurement_wavelength']
    if wavelength is not None:
        _closed(wavelength, ('state', 'value', 'unit', 'reason'))
        _require(wavelength['unit'] == 'nm')
        if wavelength['state'] == 'present':
            _require(_number(wavelength['value']) and wavelength['value'] > 0 and (wavelength['reason'] is None))
        elif wavelength['state'] == 'not_supplied':
            _require(wavelength['value'] is None and wavelength['reason'] == 'not_supplied')
        else:
            _require(wavelength['state'] == 'invalid_input' and wavelength['reason'] in ('non_numeric_value', 'nonfinite_value', 'not_exactly_representable_binary64', 'nonpositive_measurement_wavelength'))
            _require(_number(wavelength['value']) and wavelength['value'] <= 0 if wavelength['reason'] == 'nonpositive_measurement_wavelength' else wavelength['value'] is None)
    _enum_list(thermal['qualifications'], _THERMAL_QUALIFICATIONS)
    cells = _thermal_cells(thermal['summary'], thermal['signal_unit'])
    if thermal['state'] in ('not_supplied', 'invalid_input', 'incompatible'):
        _require(not cells and thermal['endpoint_temperature_difference'] is None and (thermal['width_divisor_point_count'] is None) and (thermal['source_cooperativity_label'] is None) and (thermal['qualifications'] == []))
    else:
        _require(len(cells) in (3, 8) and thermal['signal_unit'] in _SIGNALS and (type(thermal['temperature_count']) is int) and (thermal['temperature_count'] == thermal['signal_count'] > 0))
        if len(cells) == 3:
            _require(thermal['state'] == 'partial' and thermal['endpoint_temperature_difference'] is None and (thermal['width_divisor_point_count'] is None) and (thermal['source_cooperativity_label'] is None))
        else:
            count = thermal['temperature_count']
            _require(thermal['width_divisor_point_count'] == count and cells['sampled_midpoint_index']['value'] < count and (cells['transition_point_count']['value'] <= count) and (cells['source_endpoint_span_per_point']['denominator'] == count) and _same(cells['source_endpoint_span_per_point']['numerator'], thermal['endpoint_temperature_difference']))
            _require(thermal['source_cooperativity_label'] in _COOPERATIVITY if thermal['state'] == 'present' else thermal['source_cooperativity_label'] is None)
    return value

def _obj(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)

def _nullable(node):
    return {'anyOf': [node, {'type': 'null'}]}

def _array(node):
    return dict(type='array', items=node)

def _enum(values):
    return {'enum': list(values)}

def _cell_schema(name):
    integer = {'type': 'integer', 'minimum': 0}
    number = {'type': 'number'}
    value = integer if name in _COUNT_NAMES else number
    if name in _OVERFLOW_NAMES:
        value = _nullable(value)
    return _obj(dict(name={'const': name}, value=value, unit=_enum(_SIGNALS) if name in _SIGNAL_METRICS else {'const': _UNITS[name]}, state=_enum(('present', 'invalid_input') if name in _OVERFLOW_NAMES else ('present',)), reason=_enum((None, 'arithmetic_overflow') if name in _OVERFLOW_NAMES else (None,)), formula_id={'const': _FORMULAS[name]}, input_fields=_array({'type': 'string', 'pattern': '^/'}), numerator=_nullable(integer if name in (*_SIGNS, 'transition_point_count') else number) if name in (*_SIGNS, 'transition_point_count', 'source_endpoint_span_per_point', 'relative_signal') else {'type': 'null'}, denominator=integer if name == 'source_endpoint_span_per_point' else number if name == 'relative_signal' else {'type': 'null'}, origin={'const': 'derived_supplied_measurements'}, uncertainty=_obj(dict(state={'const': 'unavailable'}, reason={'const': 'not_supplied_or_estimated'}))))

def circular_dichroism_return_schema():
    count = {'type': 'integer', 'minimum': 0}
    number = {'type': 'number'}
    feature = _obj(dict(name=_enum(_SIGNS), window_nm=dict(type='array', items={'type': 'integer', 'minimum': 1}, minItems=2, maxItems=2, enum=deepcopy(list(_WINDOWS.values()))), sign=_enum(('positive', 'negative')), count={'anyOf': [_cell_schema(name) for name in _SIGNS]}, population_count=count, count_denominator={'type': 'null'}))
    wavelength = _obj(dict(state=_enum(('present', 'not_supplied', 'invalid_input')), value=_nullable(number), unit={'const': 'nm'}, reason=_enum((None, 'not_supplied', 'non_numeric_value', 'nonfinite_value', 'not_exactly_representable_binary64', 'nonpositive_measurement_wavelength'))))
    return _obj(dict(version={'const': RETURN_VERSION}, source_ref={'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source', 'pattern': '^source_[0-9a-f]{24}$'}, sample_key=_nullable({'type': 'string', 'minLength': 1}), sample_type=_enum((None, 'protein', 'nucleic_acid')), spectrum=_obj(dict(state=_enum(('present', 'missing_input', 'invalid_input', 'incompatible')), wavelength_count=_nullable(count), signal_count=_nullable(count), signal_unit=_enum((None, *_SIGNALS)), features=_array(feature), source_structure_label=_enum((None, *(label for labels in _STRUCTURES.values() for label in labels))), qualifications=_nullable(_array(_enum(('signal_unit_unknown',)))))), thermal=_obj(dict(state=_enum(('present', 'partial', 'not_supplied', 'invalid_input', 'incompatible')), temperature_count=_nullable(count), signal_count=_nullable(count), signal_unit=_enum((None, *_SIGNALS)), measurement_wavelength=_nullable(wavelength), summary=_array({'anyOf': [_cell_schema(name) for name in _METRICS]}), endpoint_temperature_difference=_nullable(number), width_divisor_point_count=_nullable(count), source_cooperativity_label=_enum((None, *_COOPERATIVITY)), qualifications=_array(_enum(_THERMAL_QUALIFICATIONS)))), issue_codes=_array(_enum(ISSUE_CODES)), qualifications=_array(_enum(core.QUALIFICATIONS))))

def circular_dichroism_fact_sources():
    return {FACT_SOURCE: dict(type='array', meaning='Literal full-original-population CD summaries from a retained Source. Spectral values are signed sampled-point counts; thermal values are source-defined relative-signal/sample-midpoint/N-point-width heuristics. No calibrated structure fractions, fitted thermodynamics or function-confidence probabilities. Selected views do not change these summaries.', report_schema=dict(type='array', items=circular_dichroism_return_schema(), **{'x-source': FACT_SOURCE}))}
