"""Pure per-interval MACS2 likelihood components from retained track values.

Coordinates, sample joins and native-output parsing belong to the sheet and its
consumer. This function neither runs MACS2 nor assigns annotation credit. The
three signed likelihood ratios are not p-values or estimates of replicate
variation. The explicit binary32 conversions reproduce MACS2 2.2.9.1 storage;
raw inputs and unrounded components remain separate.
"""
from __future__ import annotations

import math
import struct


_LOG10_E = 0.43429448190325176
_TRACKS = ('signal1', 'background1', 'signal2', 'background2')
_DEPTH_UNITS = ('tags', 'fragments', 'million_tags', 'million_fragments')


def _measurement(value=None, *, unit, state='derived', reason=None):
    return {'value': value, 'state': state, 'reason': reason, 'unit': unit}


def _unavailable(source, *, unit):
    return _measurement(unit=unit, state=source['state'], reason=source['reason'])


def _numeric_operand(value, *, depth=False):
    unit = 'depth_count' if depth else 'pileup'
    if value is None:
        return _measurement(unit=unit, state='missing', reason='operand_unavailable')
    if type(value) not in (int, float):
        return _measurement(unit=unit, state='invalid', reason='numeric_operand_required')
    try:
        number = float(value)
    except OverflowError:
        return _measurement(unit=unit, state='invalid', reason='numeric_overflow')
    if not math.isfinite(number):
        return _measurement(unit=unit, state='invalid', reason='nonfinite_operand')
    if number < 0:
        return _measurement(unit=unit, state='invalid', reason='negative_operand')
    if depth and number == 0:
        return _measurement(unit=unit, state='undefined', reason='zero_depth')
    return _measurement(number, unit=unit)


def _float32(source):
    if source['value'] is None:
        return dict(source)
    try:
        value = struct.unpack('<f', struct.pack('<f', source['value']))[0]
    except (OverflowError, struct.error):
        return _measurement(unit=source['unit'], state='undefined', reason='float32_overflow')
    if not math.isfinite(value):
        return _measurement(unit=source['unit'], state='undefined', reason='float32_overflow')
    return _measurement(value, unit=source['unit'])


def _depth_factors(first, second):
    unavailable = next((item for item in (first, second) if item['value'] is None), None)
    if unavailable is not None:
        return {name: _unavailable(unavailable, unit='1') for name in ('condition1', 'condition2')}
    minimum = min(first['value'], second['value'])
    factors = {}
    for name, count in (('condition1', first), ('condition2', second)):
        factor = minimum / count['value']
        factors[name] = (_measurement(factor, unit='1') if factor > 0 else
                         _measurement(unit='1', state='undefined', reason='depth_factor_underflow'))
    return factors


def _adjusted(source, factor, pseudocount):
    for operand in (source, factor):
        if operand['value'] is None:
            return _unavailable(operand, unit='depth_scaled_pileup')
    value = (source['value'] + pseudocount) * factor['value']
    if not math.isfinite(value):
        return _measurement(unit='depth_scaled_pileup', state='undefined', reason='adjusted_value_overflow')
    if value <= 0:
        return _measurement(unit='depth_scaled_pileup', state='undefined', reason='adjusted_value_underflow')
    return _measurement(value, unit='depth_scaled_pileup')


def _likelihood(first, second, *, symmetric):
    unit = 'signed_log10_likelihood_ratio'
    for operand in (first, second):
        if operand['value'] is None:
            return _unavailable(operand, unit=unit)
    x, y = first['value'], second['value']
    if x == y:
        score = 0.0
    elif x > y:
        score = (x * (math.log(x) - math.log(y)) + y - x) * _LOG10_E
    elif symmetric:
        score = (y * (math.log(x) - math.log(y)) + y - x) * _LOG10_E
    else:
        score = (x * (-math.log(x) + math.log(y)) - y + x) * _LOG10_E
    if not math.isfinite(score):
        return _measurement(unit=unit, state='undefined', reason='likelihood_overflow')
    return _measurement(score, unit=unit)


def validate_atac_likelihood_parameters(*, depth_unit: str,
                                       pseudocount: int | float) -> float:
    """Validate mathematical declarations independently of interval presence."""
    if type(depth_unit) is not str or depth_unit not in _DEPTH_UNITS:
        raise ValueError('atac_depth_unit_required')
    if type(pseudocount) not in (int, float):
        raise ValueError('atac_positive_finite_pseudocount_required')
    try:
        pseudo = float(pseudocount)
    except OverflowError as error:
        raise ValueError('atac_positive_finite_pseudocount_required') from error
    if not math.isfinite(pseudo) or pseudo <= 0:
        raise ValueError('atac_positive_finite_pseudocount_required')
    return pseudo


def calculate_atac_interval_scores(*, signal1: int | float | None,
                                   background1: int | float | None,
                                   signal2: int | float | None,
                                   background2: int | float | None,
                                   depth1: int | float | None,
                                   depth2: int | float | None,
                                   depth_unit: str,
                                   pseudocount: int | float) -> dict:
    """Calculate three inspectable likelihoods for one joined track interval.

    Depths must describe the same population units, validated by the sheet
    consumer. For single-end native BAM output they are post-filter treatment
    tags, not input BAM rows or unfiltered counts. Declared fixture depths keep
    their declared provenance in that sheet. A missing background affects only
    its own comparison; no missing operand is replaced by zero.
    """
    pseudo = validate_atac_likelihood_parameters(depth_unit=depth_unit, pseudocount=pseudocount)

    supplied = dict(signal1=signal1, background1=background1, signal2=signal2,
                    background2=background2, depth1=depth1, depth2=depth2)
    checked = {name: _numeric_operand(value, depth=name.startswith('depth'))
               for name, value in supplied.items()}
    native = {name: _float32(checked[name]) for name in _TRACKS}
    factors = _depth_factors(checked['depth1'], checked['depth2'])
    adjusted = {name: _adjusted(value, factors['condition' + name[-1]], pseudo)
                for name, value in native.items()}
    likelihoods = {}
    for name, first, second, symmetric in (
            ('condition1_vs_background', 'signal1', 'background1', False),
            ('condition2_vs_background', 'signal2', 'background2', False),
            ('condition1_vs_condition2', 'signal1', 'signal2', True)):
        raw = _likelihood(adjusted[first], adjusted[second], symmetric=symmetric)
        likelihoods[name] = {'unrounded': raw, 'native_float32': _float32(raw),
                             'operands': [first, second]}

    # Preserve finite negative/zero scientific operands as received, even when
    # unusable in this calculation. Non-JSON values stay identified by reason;
    # their original lexical bytes remain in the separately retained sheet.
    inputs = {name: value if type(value) is int or
              type(value) is float and math.isfinite(value) else None
              for name, value in supplied.items()}
    return {
        'method': 'macs2_2_2_9_1_likelihoods_correct_track_intervals',
        'parameters': {'pseudocount': pseudocount, 'depth_unit': depth_unit,
                       'input_precision': 'ieee754_binary32',
                       'arithmetic_precision': 'ieee754_binary64',
                       'score_precision': 'ieee754_binary32'},
        'inputs': inputs,
        'native_input_values': native,
        'depth_factors': factors,
        'adjusted_values': adjusted,
        'likelihoods': likelihoods,
        'input_issues': [{'field': name, 'reason': item['reason']}
                         for name, item in checked.items() if item['value'] is None],
        'uncertainty': {'kind': 'not_estimated', 'value': None},
    }


__all__ = ['calculate_atac_interval_scores', 'validate_atac_likelihood_parameters']
