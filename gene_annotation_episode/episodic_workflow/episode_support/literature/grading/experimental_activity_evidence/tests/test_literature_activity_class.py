"""The activity_rate class before its first experiment type (SOP 0b, 0c): the predicate 'catalyzes', the claim and bearing
rule for it, and the class-scoped direction/strength function with its anchors. No activity_rate experiment type exists yet, so
the bearing and direction tests register one placeholder type id ('activity_probe') in the contract's tables for the duration of
one test (monkeypatch); nothing else is replaced, all the code under test is real."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_bearing
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_activity_direction import (
    activity_direction_and_ratio, activity_strength, select_activity_effect, specific_activity_ends)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bearing import bearing
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_claim import claim_of_hypothesis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_direction import direction_and_ratio, strength
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_page_update import _check_claims
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    ACTIVITY_EFFECT_ORDER, ACTIVITY_STRENGTH_ANCHORS, CLAIM_PREDICATES_BY_CLASS, CLASS_OF_EXPERIMENT_TYPE, EXPERIMENT_TYPES,
    QUALITATIVE_LOG_RATIO, QUALITATIVE_STATEMENT, SYMMETRIC_PREDICATES)

PROBE = 'activity_probe'


@pytest.fixture
def probe_type(monkeypatch):
    monkeypatch.setattr(literature_bearing, 'EXPERIMENT_TYPES', (*EXPERIMENT_TYPES, PROBE))
    monkeypatch.setitem(CLASS_OF_EXPERIMENT_TYPE, PROBE, 'activity_rate')
    monkeypatch.setitem(QUALITATIVE_LOG_RATIO, PROBE, 1.0)
    return PROBE


def operand(value, unit):
    return {'status': 'point', 'value': value, 'unit': unit}


def smooth(p):
    return 3 * p ** 2 - 2 * p ** 3


# ---- the predicate -------------------------------------------------------------------------------------------------

def test_catalyzes_is_the_activity_rate_predicate_and_not_symmetric():
    assert CLAIM_PREDICATES_BY_CLASS['activity_rate'] == ('catalyzes',)
    assert 'catalyzes' not in SYMMETRIC_PREDICATES
    needed, targets = _check_claims({'h1': {'predicate': 'catalyzes', 'subject_id': 'e1', 'partner_id': None}})
    assert needed == {'h1': ('activity_rate',)}


def test_the_qualitative_vocabulary_is_unchanged():
    assert QUALITATIVE_STATEMENT == ('interaction_detected', 'interaction_not_detected', 'interaction_not_stated')


# ---- the claim -----------------------------------------------------------------------------------------------------

def hypothesis(predicate, value_type):
    return {'subject_refs': ['s'], 'predicate': predicate, 'value': {'type': value_type, 'ref': 'v'}, 'context_refs': []}


def test_a_reaction_term_value_gives_no_partner_for_catalyzes():
    claim = claim_of_hypothesis(hypothesis('catalyzes', 'term_ref'), {'s': 'Esterase EstA', 'v': 'Hydrolysis'})
    assert claim == {'predicate': 'catalyzes', 'subject_id': 'esterase esta', 'partner_id': None}


def test_a_molecule_reference_value_is_the_substrate_partner_for_catalyzes():
    claim = claim_of_hypothesis(hypothesis('catalyzes', 'reference'), {'s': 'Esterase EstA', 'v': 'p-Nitrophenyl acetate'})
    assert claim['partner_id'] == 'p-nitrophenyl acetate'


def test_binding_claims_keep_a_term_ref_partner():
    claim = claim_of_hypothesis(hypothesis('binds', 'term_ref'), {'s': 'PopZ', 'v': 'ParB'})
    assert claim == {'predicate': 'binds', 'subject_id': 'popz', 'partner_id': 'parb'}


# ---- bearing -------------------------------------------------------------------------------------------------------

def record(target, partner=None):
    return {'experiment_type': PROBE, 'target_id': target, 'partner_id': partner}


def test_enzyme_claim_on_a_reaction_term_is_direct_for_a_record_of_that_enzyme(probe_type):
    claim = claim_of_hypothesis(hypothesis('catalyzes', 'term_ref'), {'s': 'EstA', 'v': 'Hydrolysis'})
    assert bearing(record('esta'), claim) == {'bearing': 'direct', 'reasons': ['predicate_and_target_agree']}
    # the record's stated substrate is not compared when the claim has no molecule partner
    assert bearing(record('esta', 'pnpa'), claim)['bearing'] == 'direct'


def test_a_record_of_another_enzyme_is_a_different_subject(probe_type):
    claim = claim_of_hypothesis(hypothesis('catalyzes', 'term_ref'), {'s': 'EstA', 'v': 'Hydrolysis'})
    assert bearing(record('estb'), claim) == {'bearing': 'different_subject', 'reasons': ['target_differs_from_subject']}


def test_a_substrate_claim_does_not_bear_on_a_record_with_another_substrate(probe_type):
    claim = claim_of_hypothesis(hypothesis('catalyzes', 'reference'), {'s': 'EstA', 'v': 'pNPA'})
    assert bearing(record('esta', 'pnpb'), claim) == {'bearing': 'different_subject', 'reasons': ['partner_contradicts_claim']}
    assert bearing(record('esta', 'pnpa'), claim)['bearing'] == 'direct'
    assert bearing(record('esta'), claim)['bearing'] == 'direct'


def test_catalyzes_is_not_symmetric(probe_type):
    claim = {'predicate': 'catalyzes', 'subject_id': 'esta', 'partner_id': 'pnpa'}
    # the target is the claim's partner and the record's partner the claim's subject: direct for a symmetric predicate only
    assert bearing(record('pnpa', 'esta'), claim)['bearing'] == 'different_subject'


# ---- the anchors and the strength curve -----------------------------------------------------------------------------

def test_anchors_run_from_a_noise_end_to_a_larger_strong_end():
    for quantity, anchors in ACTIVITY_STRENGTH_ANCHORS.items():
        assert anchors['noise_end'] < anchors['strong_end'], quantity
    assert set(ACTIVITY_STRENGTH_ANCHORS) | {'specific_activity'} == set(ACTIVITY_EFFECT_ORDER)


@pytest.mark.parametrize('quantity,unit,noise,strong', [
    ('catalytic_efficiency', 'M^-1s^-1', 1e2, 1e6), ('turnover', 's^-1', 1e-2, 1e2), ('rate_over_control', 'fold', 1.0, 1e3)])
def test_strength_at_the_noise_end_the_strong_end_and_the_middle(quantity, unit, noise, strong):
    assert activity_strength(quantity, operand(noise, unit), None) == 0.0
    assert activity_strength(quantity, operand(noise / 10, unit), None) == 0.0       # below the noise end: clipped, not negative
    assert activity_strength(quantity, operand(strong, unit), None) == pytest.approx(1.0)
    assert activity_strength(quantity, operand(strong * 10, unit), None) == pytest.approx(1.0)
    middle = math.sqrt(noise * strong)
    assert activity_strength(quantity, operand(middle, unit), None) == pytest.approx(0.5)


def test_the_median_natural_enzyme_sits_at_the_same_place_on_both_scales():
    efficiency = activity_strength('catalytic_efficiency', operand(1e5, 'M^-1s^-1'), None)
    turnover = activity_strength('turnover', operand(10.0, 's^-1'), None)
    assert efficiency == pytest.approx(smooth(0.75)) and turnover == pytest.approx(smooth(0.75))


def test_a_stated_spread_lowers_the_strength_smoothly():
    effect = operand(1e4, 'M^-1s^-1')          # the middle of the scale: s = 0.5 without a spread
    values = [activity_strength('catalytic_efficiency', effect, {'status': 'point', 'value': (fraction * 1e4) ** 2, 'unit': 'M^-1s^-1_squared'})
              for fraction in (0.1, 0.5, 1.0, 2.0)]
    assert values[1] == pytest.approx(0.5 / 1.25)
    assert values[2] == pytest.approx(0.25)
    assert values == sorted(values, reverse=True) and all(0.0 < v < 0.5 for v in values)


def test_a_larger_rate_is_never_weaker():
    series = [activity_strength('turnover', operand(10 ** (exponent / 4), 's^-1'), None) for exponent in range(-12, 13)]
    assert series == sorted(series) and all(0.0 <= s <= 1.0 for s in series)
    assert len({round(s, 6) for s in series}) > 8     # no step: many distinct values between the ends


def test_specific_activity_ends_are_the_kcat_ends_at_the_enzyme_mass():
    noise, strong = specific_activity_ends(None)       # the 50 kDa reference mass: U/mg = kcat * 60 * 1000 / 5e4 = 1.2 kcat
    assert noise == pytest.approx(1.2e-2) and strong == pytest.approx(120.0)
    noise, strong = specific_activity_ends(1.0e5)
    assert noise == pytest.approx(6.0e-3) and strong == pytest.approx(60.0)
    assert activity_strength('specific_activity', operand(1.2, 'U/mg'), None) == pytest.approx(0.5)
    # the same U/mg of a heavier enzyme is more turnovers per enzyme molecule, so it is stronger
    assert activity_strength('specific_activity', operand(1.2, 'U/mg'), None, 1.0e5) > 0.5
    with pytest.raises(ValueError):
        specific_activity_ends(0)


def test_a_wrong_unit_or_a_non_positive_effect_raises():
    with pytest.raises(ValueError):
        activity_strength('turnover', operand(10.0, 'min^-1'), None)
    with pytest.raises(ValueError):
        activity_strength('turnover', operand(0.0, 's^-1'), None)
    with pytest.raises(ValueError):
        activity_strength('turnover', operand(10.0, 's^-1'), {'status': 'point', 'value': 4.0, 'unit': 's^-1'})
    with pytest.raises(ValueError):
        activity_strength('kcat', operand(10.0, 's^-1'), None)


def test_the_effect_is_the_best_determined_stated_quantity():
    stated = {'rate_over_control': operand(50.0, 'fold'), 'specific_activity': operand(3.0, 'U/mg'), 'turnover': operand(8.0, 's^-1')}
    assert select_activity_effect(stated)[0] == 'turnover'
    stated['catalytic_efficiency'] = operand(1e5, 'M^-1s^-1')
    assert select_activity_effect(stated)[0] == 'catalytic_efficiency'
    stated['catalytic_efficiency'] = {'status': 'unavailable', 'value': None, 'unit': None}
    assert select_activity_effect(stated)[0] == 'turnover'
    with pytest.raises(ValueError):
        select_activity_effect({'turnover': None})


# ---- the direction ---------------------------------------------------------------------------------------------------

def converted(kind, effect, variance=None, qualitative=None):
    result = {'experiment_type': PROBE, 'direction_field_support': 'direct',
              'extraction': {'quantity_kind': kind, 'quantities': {'effect': effect, 'effect_variance': variance}}}
    if qualitative is not None:
        result['qualitative_effect'] = {'statement': qualitative, 'support_refs': ['r']}
    return result


def test_a_stated_rate_supports_by_its_strength(probe_type):
    result = activity_direction_and_ratio(converted('catalytic_efficiency', operand(1e4, 'M^-1s^-1')), None)
    assert result['direction'] == 'supports' and result['log_ratio'] == pytest.approx(0.5) and result['effect_support'] == 1.0


def test_a_rate_at_the_noise_end_is_neutral_and_never_opposes(probe_type):
    result = activity_direction_and_ratio(converted('rate_ratio', operand(0.8, 'fold')), None)
    assert result == {'direction': 'neutral', 'log_ratio': 0.0, 'effect_support': 1.0}


def test_no_activity_above_the_papers_control_is_the_qualitative_not_detected_case(probe_type):
    assert activity_direction_and_ratio(converted('rate', None, qualitative='interaction_not_detected'), None)['direction'] == 'opposes'
    assert activity_direction_and_ratio(converted('rate', None, qualitative='interaction_detected'), None)['direction'] == 'supports'
    assert activity_direction_and_ratio(converted('rate', None, qualitative='interaction_not_stated'), None)['direction'] == 'unknown'


def test_a_specific_activity_effect_uses_the_stated_mass(probe_type):
    at_reference = activity_direction_and_ratio(converted('rate', operand(1.2, 'U/mg')), None)
    at_heavy = activity_direction_and_ratio(converted('rate', operand(1.2, 'U/mg')), 1.0e5)
    assert at_reference['log_ratio'] == pytest.approx(0.5) and at_heavy['log_ratio'] > at_reference['log_ratio']


def test_a_kind_without_anchors_raises(probe_type):
    with pytest.raises(ValueError):
        activity_direction_and_ratio(converted('kinetic_parameter', operand(1.0, 'uM')), None)


def test_a_binding_type_is_refused_by_the_activity_function():
    with pytest.raises(ValueError):
        activity_direction_and_ratio({'experiment_type': 'spr', 'extraction': {'quantities': {'effect': None}}}, None)


def test_binding_direction_is_unchanged():
    spr = {'experiment_type': 'spr', 'direction_field_support': 'direct',
           'extraction': {'quantity_kind': 'binding_parameter', 'quantities': {'effect': operand(20.0, 'nM'), 'effect_variance': None}}}
    p = (math.log10(20.0) - 6.0) / (0.0 - 6.0)
    assert strength('spr', operand(20.0, 'nM'), None) == pytest.approx(smooth(p))
    result = direction_and_ratio(spr)
    assert result['direction'] == 'supports' and result['log_ratio'] == pytest.approx(QUALITATIVE_LOG_RATIO['spr'] * smooth(p))
    assert direction_and_ratio({'experiment_type': 'pulldown', 'direction_field_support': 'direct',
                                'extraction': {'quantities': {'effect': None}},
                                'qualitative_effect': {'statement': 'interaction_not_detected', 'support_refs': ['r']}})['direction'] == 'opposes'
