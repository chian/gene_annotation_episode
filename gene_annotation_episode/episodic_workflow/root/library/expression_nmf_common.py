"""Shared data validation for the NMF input, sheet and result consumers.

These helpers only examine supplied values. They perform no file access,
fitting, acquisition, episode selection or annotation-credit calculation.
"""
from copy import deepcopy
import hashlib
import json
import math
import re

INPUT_SCHEMA = 'expression_nmf_input_v1'
PREPARED_SCHEMA = 'expression_nmf_prepared_v1'
NATIVE_SCHEMA = 'expression_nmf_native_result_v1'
FACTOR_SCHEMA = 'expression_nmf_factors_v1'
SHEET_SCHEMA = 'expression_nmf_sheet_v1'
CALCULATION_SCHEMA = 'expression_nmf_calculations_v1'
MODE = 'gene_expression_nmf_cd_frobenius'
OPERATION = 'perform_gene_expression_nmf_analysis'
_DATA_TEXT = {'type': ['string', 'null'], 'minLength': 1, 'maxLength': 128, 'pattern': '^[^\\u0000-\\u001f\\u007f]+$'}
_KEY_TEXT = {'type': ['string', 'null'], 'minLength': 1, 'maxLength': 256, 'pattern': '^[A-Za-z0-9][A-Za-z0-9_.:/+()=-]*$'}
_POSITION = {'type': 'integer', 'minimum': 0}
METADATA_SCHEMA = {'type': ['object', 'null'], 'properties': {'units': _DATA_TEXT,
    'genes': {'type': 'array', 'items': {'type': 'object', 'properties': {'position': _POSITION,
        'label': {'type': 'string'}, 'target_key': _KEY_TEXT}, 'required': ['position', 'label'], 'additionalProperties': False}},
    'samples': {'type': 'array', 'items': {'type': 'object', 'properties': {'position': _POSITION,
        'label': {'type': 'string'}, 'condition': _DATA_TEXT, 'biological_replicate': _KEY_TEXT,
        'technical_replicate': _KEY_TEXT}, 'required': ['position', 'label'], 'additionalProperties': False}}},
    'additionalProperties': False}


def metadata_valid(value):
    if value is None:
        return True
    if type(value) is not dict or set(value) - {'units', 'genes', 'samples'}:
        return False
    def data_text(text):
        return text is None or (type(text) is str and 0 < len(text) <= 128
            and not any(ord(c) < 32 or ord(c) == 127 for c in text))
    def key_text(text):
        return text is None or (type(text) is str and 0 < len(text) <= 256
            and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/+()=-]*', text) is not None)
    if not data_text(value.get('units')):
        return False
    for name in ('genes', 'samples'):
        rows = value.get(name, [])
        allowed = {'position', 'label', 'target_key'} if name == 'genes' else {
            'position', 'label', 'condition', 'biological_replicate', 'technical_replicate'}
        if type(rows) is not list:
            return False
        for row in rows:
            if (type(row) is not dict or set(row) - allowed or not {'position', 'label'} <= set(row)
                    or type(row['position']) is not int or row['position'] < 0 or type(row['label']) is not str):
                return False
            if not data_text(row.get('condition')) or not all(key_text(row.get(k))
                    for k in ('target_key', 'biological_replicate', 'technical_replicate')):
                return False
    return True


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def identity(raw):
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}


def require(value, code):
    if not value:
        raise ValueError(code)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def issue(code, stage, *, field=None, gene_position=None, sample_position=None, component_position=None):
    return {'code': code, 'stage': stage, 'field': field, 'gene_position': gene_position,
        'sample_position': sample_position, 'component_position': component_position}


def unique_issues(*groups):
    return list({digest(row): deepcopy(row) for group in groups for row in group}.values())


def axis(labels, name):
    return [{'position': i, 'key': f'{name}:{i}', 'label': label, 'metadata': {}}
        for i, label in enumerate(labels)]


def axis_valid(rows, name):
    return type(rows) is list and all(type(row) is dict and set(row) == {'position', 'key', 'label', 'metadata'}
        and type(row['position']) is int and row['position'] == i and row['key'] == f'{name}:{i}'
        and type(row['label']) is str and type(row['metadata']) is dict for i, row in enumerate(rows))


def matrix_valid(matrix, rows, columns, *, nonnegative=False):
    return type(matrix) is list and len(matrix) == rows and all(type(row) is list and len(row) == columns
        and all(finite(value) and (not nonnegative or value >= 0) for value in row) for row in matrix)


def validate_parameters(parameters):
    require(type(parameters) is dict and set(parameters) == {'rank', 'random_state', 'normalization', 'tol', 'max_iter'},
        'invalid_nmf_parameters')
    require(type(parameters['rank']) is int and parameters['rank'] > 0, 'invalid_nmf_rank')
    require(type(parameters['random_state']) is int and 0 <= parameters['random_state'] <= 2**32 - 1,
        'invalid_nmf_random_state')
    require(parameters['normalization'] in ('none', 'column_sum_1000'), 'unsupported_nmf_normalization')
    require(finite(parameters['tol']) and parameters['tol'] >= 0, 'invalid_nmf_tolerance')
    require(type(parameters['max_iter']) is int and parameters['max_iter'] > 0, 'invalid_nmf_max_iter')
    return deepcopy(parameters)


def default_nmf_parameters(**overrides):
    """Original rank/seed/scaling/iteration defaults; explicit CD default tol."""
    return validate_parameters({'rank': 10, 'random_state': 42, 'normalization': 'column_sum_1000',
        'tol': 0.0001, 'max_iter': 1000, **overrides})


def fit_parameters(parameters):
    parameters = validate_parameters(parameters)
    return {'n_components': parameters['rank'], 'init': 'random', 'solver': 'cd', 'beta_loss': 'frobenius',
        'tol': parameters['tol'], 'max_iter': parameters['max_iter'], 'random_state': parameters['random_state'],
        'alpha_W': 0.0, 'alpha_H': 0.0, 'l1_ratio': 0.0, 'shuffle': False, 'verbose': 0}
