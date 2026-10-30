"""Whole-API arithmetic contrasts on explicit engineering source fixtures."""
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

import pytest

from gene_annotation_episode.literature_ratio_source_calculations import populate_relative_signal_v2
from test_literature_ratio_source_inputs import extract, request, visual, image, prose


def sheet(rows):
    extraction, _ = extract(request(rows))
    return populate_relative_signal_v2(extraction)


def test_all_twelve_declared_constructed_cases():
    ambiguous = visual(state='ambiguous')
    ambiguous['selection']['candidates'].append({'numerator': image('0.80'), 'denominator': image('1.00', ref=True)})
    cases = [
        ('visual_only', [visual()], .6, [.6], None, True, True, False),
        ('mixed_same_reported_quantity', [prose(), visual()], .6, [.6], None, True, True, False),
        ('linked_representation_conflict', [visual('1.00'), visual('1.12', ident='v2')], None, [1., 1.12], 'source_representation_conflict', True, True, True),
        ('known_plus_unreadable', [visual('0.64'), visual(state='unreadable', ident='v2')], None, [.64], 'unreadable_transcription', False, False, False),
        ('ambiguous_numeral', [ambiguous], None, [.6, .8], 'ambiguous_transcription', False, False, False),
        ('printed_zero', [visual('0')], 0., [0.], None, True, True, False),
        ('printed_upper_limit', [visual('<0.10')], None, [], 'reported_limit_not_point', True, False, False),
        ('reported_ND_without_limit', [visual('ND')], None, [], 'unsupported_expression', False, False, False),
        ('zero_reference', [visual('0.60', '0')], None, [], 'positive_denominator_not_established', False, False, False),
        ('known_different_signal_scales', [visual(scale='different')], None, [], 'signal_scales_differ', False, False, False),
        ('exact_source_duplicate', [visual(), visual(ident='copy')], .6, [.6], None, True, True, False),
        ('different_reported_quantities', [visual(), visual('0.80', ident='v2', relation='different')], None, [.6], 'different_reported_quantities', False, False, False),
    ]
    assert len(cases) == 12
    for name, rows, value, candidates, reason, resolved, complete, conflict in cases:
        out = sheet(rows)
        cell = out['cells']['reported_ratio']
        assert (cell['value'], cell['value_candidates'], cell['unavailable_reason']) == (value, candidates, reason), name
        assert (out['selected_roster_resolved'], out['point_candidate_set_complete'], out['known_source_conflict']) == (resolved, complete, conflict), name
        assert out['independent_preparation_count'] is None and out['annotation_credit'] is None
        for component, why in (('calibrated_amount_ratio', 'calibrated_amount_conversion_unimplemented'),
                               ('amount_adjusted_effect', 'functional_response_conversion_unimplemented'),
                               ('source_profile_log_ratio', 'observation_model_unimplemented'), ('source_signed_index', 'observation_model_unimplemented')):
            assert out['cells'][component]['value'] is None
            assert out['cells'][component]['unavailable_reason'] == why
    out = sheet([visual('0')])
    assert out['cells']['difference_from_reference']['value'] == -1
    assert out['cells']['log_reported_ratio']['unavailable_reason'] == 'zero_reported_ratio'
    assert out['cells']['log_reported_ratio']['reported_domains'] == []


def test_exact_rational_equality_and_rounded_inequality():
    out = sheet([visual('0.60', '2'), visual('30%', kind='visual_percent', ident='percent'), visual('0.3', kind='visual_ratio', ident='ratio')])
    assert out['cells']['reported_ratio']['value'] == .3 and not out['known_source_conflict']
    assert out['cells']['difference_from_reference']['value'] == -.7
    assert out['cells']['log_reported_ratio']['value'] == pytest.approx(math.log(.3))
    # Both project to float1 but retain different exact fractions.
    out = sheet([visual('1'), visual('1.0000000000000000000000000000000000001', ident='v2')])
    assert out['known_source_conflict'] and out['cells']['reported_ratio']['value'] is None
    assert out['cells']['log_reported_ratio']['value_candidates'][1] > 0
    out = sheet([visual('1.0000000000000000000000000000000000001')])
    assert out['cells']['log_reported_ratio']['value'] > 0
    assert out['cells']['difference_from_reference']['value'] == 1e-37


@pytest.mark.parametrize('literal,reason', [('ND', 'unsupported_expression'), ('n.d.', 'unsupported_expression'),
    ('0.6 ± 0.1', 'unsupported_expression'), ('-0.6', 'negative_reported_signal_unsupported'),
    ('<0', 'unsupported_expression'), ('1e309', 'numerical_model_range'), ('1e-400', 'numerical_model_range')])
def test_literal_capability_partials_never_become_zeros(literal, reason):
    extraction, _ = extract(request([visual(literal)]))
    reading = extraction['representations'][0]['readings'][0]
    assert reading['numerator']['literal'] == literal
    assert reading['ratio'] is None and reading['reported_domains'] == []
    out = populate_relative_signal_v2(extraction)
    assert out['cells']['reported_ratio']['value'] is None
    assert out['cells']['reported_ratio']['unavailable_reason'] == reason


def test_strict_domains_nonnegative_feasibility_and_outward_projection():
    out = sheet([visual('<0.10')])
    ratio = out['cells']['reported_ratio']['reported_domains'][0]
    assert ratio['lower'] == 0 and ratio['lower_closed'] and not ratio['upper_closed']
    assert Fraction.from_float(ratio['upper']) >= Fraction(1, 10)
    diff = out['cells']['difference_from_reference']['reported_domains'][0]
    assert diff['lower'] == -1 and diff['upper'] >= -.9 and not diff['upper_closed']
    log = out['cells']['log_reported_ratio']['reported_domains'][0]
    assert log['lower'] is None and log['lower_infinite'] and not log['lower_closed']
    assert log['upper'] >= math.log(.1) and not log['upper_closed']
    for literal, low_closed, high_closed in [('<=0', True, True), ('>0', False, False), ('≥0.1', True, False)]:
        out = sheet([visual(literal)])
        domain = out['cells']['reported_ratio']['reported_domains'][0]
        assert domain['lower_closed'] == low_closed
        assert domain['upper_closed'] == high_closed
    # A positive lower-open reference is a positive domain; division can be
    # unbounded, whereas a reference domain including zero is unsupported.
    out = sheet([visual('1', '>0')])
    domain = out['cells']['reported_ratio']['reported_domains'][0]
    assert domain['upper_infinite'] and domain['upper'] is None and domain['lower'] == 0
    out = sheet([visual('1', '<1')])
    assert out['cells']['reported_ratio']['unavailable_reason'] == 'positive_denominator_not_established'
    json.dumps(out, allow_nan=False)


def test_known_conflict_survives_unresolved_and_aliases_do_not_add_measurements():
    out = sheet([visual('1'), visual('1.12', ident='v2'), visual(state='unreadable', ident='v3')])
    assert out['known_source_conflict']
    assert out['cells']['reported_ratio']['unavailable_reason'] == 'incomplete_conflicting_representations'
    out = sheet([visual(), visual(ident='copy')])
    assert len(out['cells']['reported_ratio']['reported_domains']) == 1
    assert out['independent_preparation_count'] is None
    unknown = visual('0.8', ident='unknown', relation='unknown')
    out = sheet([visual(), unknown])
    assert not out['known_source_conflict']
    assert out['cells']['reported_ratio']['value_candidates'] == [.6]
    assert out['cells']['reported_ratio']['unavailable_reason'] == 'comparison_association_unresolved'


def test_numerical_range_during_division_and_nonunit_log_underflow():
    extraction, _ = extract(request([visual('1e308', '1e-308')]))
    reading = extraction['representations'][0]['readings'][0]
    assert reading['ratio_exact'] is not None and reading['ratio'] is None
    assert populate_relative_signal_v2(extraction)['cells']['reported_ratio']['unavailable_reason'] == 'numerical_model_range'
    value = '1.' + '0' * 330 + '1'
    out = sheet([visual(value)])
    assert out['cells']['log_reported_ratio']['value'] is None
    assert out['cells']['log_reported_ratio']['unavailable_reason'] == 'numerical_model_range'


def test_empty_roster_preserves_unknown_components():
    out = sheet([])
    assert out['cells']['reported_ratio']['unavailable_reason'] == 'no_selected_representations'
    assert not out['point_candidate_set_complete'] and not out['selected_roster_resolved']


def test_complete_literal_percent_negatives_compound_and_blank():
    for literal in (' ', '60', '60% extra', '~60%', '60% ±2%'):
        out = sheet([visual(literal, kind='visual_percent')])
        assert out['cells']['reported_ratio']['value'] is None
        assert out['cells']['reported_ratio']['unavailable_reason'] == 'unsupported_expression'
    out = sheet([visual('<=10%', kind='visual_percent')])
    domain = out['cells']['reported_ratio']['reported_domains'][0]
    assert domain['upper'] >= .1 and domain['upper_closed']
    out = sheet([visual('0.6'), visual('0.8', ident='other', relation='unknown')])
    assert out['cells']['reported_ratio']['value_candidates'] == [.6]
    assert not out['point_candidate_set_complete'] and not out['known_source_conflict']


def test_extreme_exponent_preserves_literal_without_allocating_giant_integer():
    extraction, _ = extract(request([visual('1e999999999999')]))
    operand = extraction['representations'][0]['readings'][0]['numerator']
    assert operand['literal'] == '1e999999999999' and operand['value'] is None
    out = populate_relative_signal_v2(extraction)
    assert out['cells']['reported_ratio']['unavailable_reason'] == 'numerical_model_range'
