"""Pure numerical records for MSA and MetaCATS, without acquisition or scoring policy.

Native tokens and ordinary numerical cells are different records. Neither a
successful parse nor a finite number establishes external custody or meaning.
Tool-specific functions validate the biological population and field semantics.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re

from . import phylogeny_calculation_contracts as c

STATES = ('available', 'missing', 'not_measured', 'failed', 'truncated', 'incompatible')
ORIGINS = ('native_observation', 'calculated', 'fitted')
_NUMBER = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')
_NATIVE_KEYS = {'raw_token', 'value', 'state', 'token_kind', 'source_location'}
_CELL_KEYS = {'value', 'state', 'unit', 'origin', 'numerator', 'denominator',
              'population_id', 'method_id', 'evidence', 'uncertainty', 'requirement_ids'}


def _require(ok, code):
    if not ok:
        raise ValueError('bvbrc_alignment_' + code)


def _finite(value):
    return type(value) is int or type(value) is float and math.isfinite(value)


def _text(value, *, empty=False):
    _require(type(value) is str and (empty or bool(value)), 'text_invalid')


def _strings(values):
    _require(type(values) in (list, tuple), 'array_invalid')
    for value in values:
        _text(value)
    _require(len(set(values)) == len(values), 'duplicate_identifier')


def native_number(raw_token: str, *, source_location: dict, integer: bool = False,
                  minimum=None, maximum=None) -> dict:
    """Preserve syntax, precision loss and invalid field ranges explicitly.

Bounds are supplied by each native field's parser. A finite but inadmissible
measurement remains recorded as incompatible; no sign or range is repaired.
"""
    _text(raw_token, empty=True)
    _require(type(integer) is bool, 'integer_flag_invalid')
    for bound in (minimum, maximum):
        _require(bound is None or _finite(bound), 'bound_invalid')
    _require(minimum is None or maximum is None or minimum <= maximum, 'bounds_reversed')
    c.location(source_location)
    token, value, state, kind = raw_token.strip(), None, 'failed', 'malformed'
    if not token:
        state, kind = 'missing', 'blank'
    elif token == 'NA':
        state, kind = 'not_measured', 'native_na'
    elif token.lower().lstrip('+-') in ('nan', 'inf', 'infinity'):
        kind = 'nonfinite'
    elif _NUMBER.fullmatch(token):
        try:
            exact = Decimal(token)
            if integer and exact == exact.to_integral_value():
                value = int(exact)
            else:
                value = float(exact)
            if not _finite(value):
                value, kind = None, 'overflow'
            elif value == 0 and exact != 0:
                value, kind = None, 'underflow'
            else:
                kind, state = 'finite', 'available'
                if (integer and exact != exact.to_integral_value()
                        or minimum is not None and exact < Decimal(str(minimum))
                        or maximum is not None and exact > Decimal(str(maximum))):
                    state = 'incompatible'
        except (InvalidOperation, OverflowError, ValueError):
            value, state, kind = None, 'failed', 'malformed'
    return {'raw_token': raw_token, 'value': value, 'state': state,
            'token_kind': kind, 'source_location': deepcopy(source_location)}


def validate_native_number(value: dict) -> dict:
    _require(type(value) is dict and set(value) == _NATIVE_KEYS, 'native_number_shape_invalid')
    _text(value['raw_token'], empty=True)
    c.location(value['source_location'])
    number = value['value']
    if value['token_kind'] == 'finite':
        _require(value['state'] in ('available', 'incompatible') and _finite(number),
                 'native_number_state_conflict')
        _require(_NUMBER.fullmatch(value['raw_token'].strip()) is not None,
                 'native_number_token_conflict')
        exact = Decimal(value['raw_token'].strip())
        _require(exact == number if type(number) is int else float(exact) == number,
                 'native_number_token_conflict')
        _require(number != 0 or exact == 0, 'native_number_underflow_conflict')
    else:
        parsed = native_number(value['raw_token'], source_location=value['source_location'])
        _require(number is None and parsed == value, 'native_number_token_conflict')
    return deepcopy(value)


def numeric_cell(value, *, state: str, unit: str, origin: str,
                 population_id: str, method_id: str, numerator=None, denominator=None,
                 evidence=(), uncertainty=None, requirement_ids=()) -> dict:
    return validate_numeric_cell({'value': value, 'state': state, 'unit': unit,
        'origin': origin, 'numerator': numerator, 'denominator': denominator,
        'population_id': population_id, 'method_id': method_id,
        'evidence': list(evidence), 'uncertainty': uncertainty,
        'requirement_ids': list(requirement_ids)})


def validate_numeric_cell(value: dict) -> dict:
    _require(type(value) is dict and set(value) == _CELL_KEYS, 'numeric_cell_shape_invalid')
    _require(value['state'] in STATES and value['origin'] in ORIGINS, 'numeric_cell_state_invalid')
    for field in ('unit', 'population_id', 'method_id'):
        _text(value[field])
    for field in ('value', 'numerator', 'denominator'):
        _require(value[field] is None or _finite(value[field]), 'numeric_cell_nonfinite')
    if value['state'] == 'available':
        _require(value['value'] is not None, 'numeric_cell_available_null')
    elif value['state'] != 'incompatible' or value['origin'] != 'native_observation':
        _require(value['value'] is None, 'numeric_cell_unavailable_value')
    c.evidence(value['evidence'])
    _strings(value['requirement_ids'])
    uncertainty = value['uncertainty']
    if uncertainty is not None:
        _require(type(uncertainty) is dict and set(uncertainty) == {
            'kind', 'lower', 'upper', 'value', 'method_id'}, 'uncertainty_shape_invalid')
        _require(uncertainty['kind'] in ('confidence_interval', 'standard_error',
            'standard_deviation', 'native_unknown'), 'uncertainty_kind_invalid')
        _text(uncertainty['method_id'])
        for field in ('lower', 'upper', 'value'):
            _require(uncertainty[field] is None or _finite(uncertainty[field]), 'uncertainty_nonfinite')
        _require(uncertainty['lower'] is None or uncertainty['upper'] is None
                 or uncertainty['lower'] <= uncertainty['upper'], 'uncertainty_reversed')
    return deepcopy(value)


def document_id(kind: str, *, artifact: dict, parameters: dict) -> str:
    _text(kind)
    _require(type(artifact) is dict and set(artifact) == {
        'raw_artifact_ref', 'source_ref', 'sha256'}, 'artifact_shape_invalid')
    _text(artifact['raw_artifact_ref'])
    _text(artifact['source_ref'])
    c.digest(artifact['sha256'])
    _require(type(parameters) is dict, 'parameters_invalid')
    payload = json.dumps({'artifact': artifact, 'parameters': parameters}, sort_keys=True,
                         separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')
    return kind + ':' + hashlib.sha256(payload).hexdigest()


def diagnostic(code: str, *, phase='association', path='', severity='qualification',
               evidence_refs=()) -> dict:
    _text(code)
    _text(path, empty=True)
    _require(not path or path.startswith('/'), 'diagnostic_path_invalid')
    _require(phase in ('custody', 'prepare', 'transport', 'native_decode', 'association',
                      'publication', 'recovery', 'return'), 'diagnostic_phase_invalid')
    _require(severity in ('error', 'qualification'), 'diagnostic_severity_invalid')
    _strings(evidence_refs)
    return {'code': code, 'phase': phase, 'path': path, 'severity': severity,
            'evidence_refs': list(evidence_refs)}


def requirement(requirement_id: str, *, kind: str, role: str | None,
                source_refs=(), reason_code: str) -> dict:
    _text(requirement_id)
    _text(reason_code)
    if role is not None:
        _text(role)
    _require(kind in ('definition', 'input_metadata', 'input_bytes', 'original_task',
        'task_manifest', 'output_metadata', 'output_bytes', 'byte_version_evidence',
        'scientific_metadata', 'parser_binding'), 'requirement_kind_invalid')
    _strings(source_refs)
    return {'requirement_id': requirement_id, 'kind': kind, 'role': role,
            'source_refs': list(source_refs), 'reason_code': reason_code}
