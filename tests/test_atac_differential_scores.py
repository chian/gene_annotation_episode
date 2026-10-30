"""Native numerical oracles and failure-isolation checks, not biological data."""
from copy import deepcopy
import json
import math
from pathlib import Path
import socket
import struct
import subprocess

import pytest

from gene_annotation_episode.atac_differential_scores import calculate_atac_interval_scores


_NATIVE = (Path(__file__).resolve().parents[1] / 'verification' /
           'tool_graders_atac_differential_plan_2026-10-27_460' /
           'native001' / 'explicit_tracks' / 'NATIVE_DIAGNOSTIC.json')


def calculate(**changes):
    operands = {'signal1': 20, 'background1': 1, 'signal2': 2, 'background2': 2,
                'depth1': 1, 'depth2': 2, 'depth_unit': 'million_tags', 'pseudocount': 0.01}
    operands.update(changes)
    return calculate_atac_interval_scores(**operands)


def score(result, name):
    return result['likelihoods'][name]['native_float32']['value']


@pytest.mark.parametrize('index', range(5))
def test_actual_retained_native_three_component_arrays(index):
    native = json.loads(_NATIVE.read_text())
    source = native['source_values']
    result = calculate(signal1=source['t1'][index], background1=source['c1'][index],
                       signal2=source['t2'][index], background2=source['c2'][index])
    recorded = native['arrays'][0]
    for output, source_key in (
            ('condition1_vs_background', 'native_condition1_vs_background'),
            ('condition2_vs_background', 'native_condition2_vs_background'),
            ('condition1_vs_condition2', 'native_condition1_vs_condition2')):
        assert score(result, output) == recorded[source_key][index]
    assert 'coordinates' not in result
    assert result['uncertainty'] == {'kind': 'not_estimated', 'value': None}


def test_count_units_and_pseudocount_order_are_explicit():
    native_counts = calculate(depth1=100, depth2=200, depth_unit='tags')
    assert native_counts['inputs']['depth1'] == 100
    assert native_counts['inputs']['depth2'] == 200
    assert native_counts['depth_factors']['condition1']['value'] == 1
    assert native_counts['depth_factors']['condition2']['value'] == 0.5
    assert native_counts['adjusted_values']['signal2']['value'] == 1.005
    assert score(native_counts, 'condition1_vs_condition2') == 17.7408447265625
    assert calculate(depth1=100, depth2=200, depth_unit='fragments')['parameters']['depth_unit'] == 'fragments'


def test_raw_decimal_and_native_precision_remain_separate():
    raw = 1.00000004
    result = calculate(signal1=raw)
    native = struct.unpack('<f', struct.pack('<f', raw))[0]
    assert result['inputs']['signal1'] == raw
    assert result['native_input_values']['signal1']['value'] == native
    assert native != raw
    assert result['adjusted_values']['signal1']['value'] == native + .01


def test_zero_and_depletion_are_numbers_not_missing_or_clamped():
    depleted = calculate(signal1=0, background1=1, signal2=0, background2=1,
                         depth1=100, depth2=100, depth_unit='tags')
    assert score(depleted, 'condition1_vs_background') < 0
    assert score(depleted, 'condition1_vs_condition2') == 0
    assert depleted['native_input_values']['signal1']['value'] == 0
    assert not depleted['input_issues']


@pytest.mark.parametrize('missing', ['background1', 'background2'])
def test_missing_background_does_not_erase_other_comparisons(missing):
    result = calculate(**{missing: None})
    own = 'condition' + missing[-1] + '_vs_background'
    other = 'condition' + ('2' if missing[-1] == '1' else '1') + '_vs_background'
    assert result['likelihoods'][own]['native_float32']['state'] == 'missing'
    assert score(result, own) is None
    assert score(result, other) is not None
    assert score(result, 'condition1_vs_condition2') == 17.7408447265625


@pytest.mark.parametrize('invalid,reason', [(-1, 'negative_operand'),
    (math.inf, 'nonfinite_operand'), (math.nan, 'nonfinite_operand'),
    (True, 'numeric_operand_required'), ('20', 'numeric_operand_required')])
def test_invalid_signal_isolated_and_finite_json(invalid, reason):
    result = calculate(signal1=invalid)
    assert {'field': 'signal1', 'reason': reason} in result['input_issues']
    assert score(result, 'condition1_vs_background') is None
    assert score(result, 'condition1_vs_condition2') is None
    assert score(result, 'condition2_vs_background') == 0
    if invalid == -1:
        assert result['inputs']['signal1'] == -1
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('depth,state,reason', [(None, 'missing', 'operand_unavailable'),
    (0, 'undefined', 'zero_depth'), (-1, 'invalid', 'negative_operand'),
    (False, 'invalid', 'numeric_operand_required')])
def test_depth_missingness_never_assumes_equal_counts(depth, state, reason):
    result = calculate(depth1=depth)
    for measurement in result['depth_factors'].values():
        assert measurement == {'value': None, 'state': state, 'reason': reason, 'unit': '1'}
    assert all(score(result, name) is None for name in result['likelihoods'])
    assert result['native_input_values']['signal1']['value'] == 20


@pytest.mark.parametrize('pseudocount', [None, 0, -1, True, math.inf, math.nan, '0.01', 10**400])
def test_invalid_formula_parameter_rejected(pseudocount):
    with pytest.raises(ValueError, match='positive_finite_pseudocount'):
        calculate(pseudocount=pseudocount)


@pytest.mark.parametrize('unit', [None, '', 'reads', 'counts', True])
def test_explicit_depth_population_unit_required(unit):
    with pytest.raises(ValueError, match='depth_unit_required'):
        calculate(depth_unit=unit)


def test_saved_calculation_uses_only_given_values(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('saved numerical calculation must not acquire or execute')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    arguments = dict(signal1=20, background1=1, signal2=2, background2=2,
                     depth1=1, depth2=2, depth_unit='million_tags', pseudocount=.01)
    original = deepcopy(arguments)
    first = calculate_atac_interval_scores(**arguments)
    second = calculate_atac_interval_scores(**{**arguments, 'pseudocount': 1})
    assert arguments == original
    assert first['inputs'] == second['inputs']
    assert first['parameters']['pseudocount'] == .01
    assert second['parameters']['pseudocount'] == 1
    assert score(first, 'condition1_vs_condition2') != score(second, 'condition1_vs_condition2')


def test_extreme_inputs_preserve_independent_results():
    overflow = calculate(signal1=1e40)
    assert overflow['inputs']['signal1'] == 1e40
    assert overflow['native_input_values']['signal1']['reason'] == 'float32_overflow'
    assert score(overflow, 'condition2_vs_background') == 0
    tiny_factor = calculate(depth1=1e-300, depth2=1e300)
    assert tiny_factor['depth_factors']['condition1']['value'] == 1
    assert tiny_factor['depth_factors']['condition2']['reason'] == 'depth_factor_underflow'
    assert score(tiny_factor, 'condition1_vs_background') == 17.699888229370117
    huge_depth = calculate(depth1=10**400)
    assert huge_depth['inputs']['depth1'] == 10**400
    assert huge_depth['depth_factors']['condition1']['reason'] == 'numeric_overflow'
    json.dumps(huge_depth, allow_nan=False)


def test_underflow_at_explicit_native_conversion_is_not_missing_data():
    result = calculate(signal1=1e-50)
    assert result['inputs']['signal1'] == 1e-50
    assert result['native_input_values']['signal1']['value'] == 0
    assert result['native_input_values']['signal1']['state'] == 'derived'
    assert result['adjusted_values']['signal1']['value'] == .01


def test_native_float32_score_overflow_preserves_unrounded_component():
    result = calculate(signal1=3e38, background1=0)
    pair = result['likelihoods']['condition1_vs_background']
    assert math.isfinite(pair['unrounded']['value'])
    assert pair['native_float32']['value'] is None
    assert pair['native_float32']['reason'] == 'float32_overflow'
