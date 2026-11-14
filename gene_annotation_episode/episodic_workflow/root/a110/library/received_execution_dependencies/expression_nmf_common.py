from copy import deepcopy
import hashlib
import json
import math
SHEET_SCHEMA = 'expression_nmf_sheet_v1'
CALCULATION_SCHEMA = 'expression_nmf_calculations_v1'
MODE = 'gene_expression_nmf_cd_frobenius'
OPERATION = 'perform_gene_expression_nmf_analysis'
_DATA_TEXT = {'type': ['string', 'null'], 'minLength': 1, 'maxLength': 128, 'pattern': '^[^\\u0000-\\u001f\\u007f]+$'}
_KEY_TEXT = {'type': ['string', 'null'], 'minLength': 1, 'maxLength': 256, 'pattern': '^[A-Za-z0-9][A-Za-z0-9_.:/+()=-]*$'}
_POSITION = {'type': 'integer', 'minimum': 0}
METADATA_SCHEMA = {'type': ['object', 'null'], 'properties': {'units': _DATA_TEXT, 'genes': {'type': 'array', 'items': {'type': 'object', 'properties': {'position': _POSITION, 'label': {'type': 'string'}, 'target_key': _KEY_TEXT}, 'required': ['position', 'label'], 'additionalProperties': False}}, 'samples': {'type': 'array', 'items': {'type': 'object', 'properties': {'position': _POSITION, 'label': {'type': 'string'}, 'condition': _DATA_TEXT, 'biological_replicate': _KEY_TEXT, 'technical_replicate': _KEY_TEXT}, 'required': ['position', 'label'], 'additionalProperties': False}}}, 'additionalProperties': False}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def require(value, code):
    if not value:
        raise ValueError(code)

def finite(value):
    return type(value) in (int, float) and math.isfinite(value)

def validate_parameters(parameters):
    require(type(parameters) is dict and set(parameters) == {'rank', 'random_state', 'normalization', 'tol', 'max_iter'}, 'invalid_nmf_parameters')
    require(type(parameters['rank']) is int and parameters['rank'] > 0, 'invalid_nmf_rank')
    require(type(parameters['random_state']) is int and 0 <= parameters['random_state'] <= 2 ** 32 - 1, 'invalid_nmf_random_state')
    require(parameters['normalization'] in ('none', 'column_sum_1000'), 'unsupported_nmf_normalization')
    require(finite(parameters['tol']) and parameters['tol'] >= 0, 'invalid_nmf_tolerance')
    require(type(parameters['max_iter']) is int and parameters['max_iter'] > 0, 'invalid_nmf_max_iter')
    return deepcopy(parameters)
