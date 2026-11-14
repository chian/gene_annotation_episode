from __future__ import annotations
import json as _json
import math as _math
_PREFIX = 'blast_vdb_function_'
_SCOPES = {'whole_sequence', 'feature'}
_GROUPINGS = {'target_duplicates_only', 'known_source_blocks'}

def _fail(suffix):
    raise ValueError(_PREFIX + suffix)

def _copy(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and _math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(v) for v in value]
    if type(value) is dict and all((type(k) is str for k in value)):
        return {k: _copy(v) for k, v in value.items()}
    _fail('finite_json_required')

def _token(value):
    return _json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)

def _closed(value, fields, code='model_parameters_invalid'):
    if type(value) is not dict or set(value) != set(fields.split()):
        _fail(code)

def _string(value):
    return type(value) is str and bool(value.strip())

def _number(value, *, positive=False):
    if type(value) not in (int, float):
        return False
    try:
        return _math.isfinite(value) and (value > 0 if positive else value >= 0)
    except OverflowError:
        return False

def validate_blast_vdb_function_model(model: dict) -> dict:
    """Return a detached unchanged explicit model; candidates are checked later."""
    result = _copy(model)
    _closed(result, 'version temperature_bits grouping_model unknown_source_dependency function_priors census_selection')
    if result['version'] != 'vdb_function_kernel_v1' or not _number(result['temperature_bits'], positive=True) or type(result['grouping_model']) is not str or (result['grouping_model'] not in _GROUPINGS) or (type(result['unknown_source_dependency']) is not str) or (result['unknown_source_dependency'] not in {'qualify_separate', 'withhold_weights'}):
        _fail('model_parameters_invalid')
    priors = result['function_priors']
    if priors is not None:
        if type(priors) is not list:
            _fail('model_parameters_invalid')
        seen = set()
        for row in priors:
            _closed(row, 'assignment_scope namespace function weight')
            _closed(row['function'], 'namespace value')
            if type(row['assignment_scope']) is not str or row['assignment_scope'] not in _SCOPES or (not _string(row['namespace'])) or (not _string(row['function']['namespace'])) or (not _string(row['function']['value'])) or (row['function']['namespace'] != row['namespace']) or (not _number(row['weight'])):
                _fail('model_parameters_invalid')
            key = (row['assignment_scope'], row['namespace'], _token(row['function']))
            if key in seen:
                _fail('model_parameters_invalid')
            seen.add(key)
    if type(result['census_selection']) is not list:
        _fail('census_selector_invalid')
    seen = set()
    for row in result['census_selection']:
        _closed(row, 'assignment_scope namespace census_key', 'census_selector_invalid')
        if type(row['assignment_scope']) is not str or row['assignment_scope'] not in _SCOPES or (not _string(row['namespace'])) or (not _string(row['census_key'])):
            _fail('census_selector_invalid')
        key = (row['assignment_scope'], row['namespace'])
        if key in seen:
            _fail('census_selector_invalid')
        seen.add(key)
    return result
