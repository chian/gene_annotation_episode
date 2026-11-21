"""AUC converter judges: the researched values are kept, every judge is monotone and bounded with partial credit around its researched value (no step), the
two counts are never conflicting (a short series or one experiment is low partial credit), and the scales follow the owner's questions (the stoichiometry is
symmetric in A:B and B:A, the loading range is judged on the fractional saturation so its two ends are mirror images, the shift is steep at the noise floor)."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_auc_converter as auc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

REFS = ['span_1']


def concentrations(count):
    return auc._judge_concentrations({'concentration_count': count, 'concentration_count_refs': REFS})


def replicates(count, independent='yes'):
    return auc._judge_replicates({'replicate_count': count, 'replicate_independent': independent, 'replicate_refs': REFS})


def shift(percent, larger=None, smaller=None):
    return auc._judge_shift({'shift_percent': percent, 'shift_refs': REFS, 'component_mass_larger': larger, 'component_mass_smaller': smaller})


def mass(deviation, smaller=None, theoretical=100.0):
    return auc._judge_mass({'mass_deviation_percent': deviation, 'mass_support_refs': REFS, 'mass_smaller_component': smaller, 'mass_theoretical': theoretical})


def stoichiometry(ratio):
    return auc._judge_stoichiometry({'stoichiometry_ratio': ratio, 'stoichiometry_refs': REFS})


def series_range(low, high):
    return auc._judge_range({'low_over_kd': low, 'high_over_kd': high, 'range_refs': REFS})


def degree_or_minus_one(verdict):
    """A conflicting verdict sorts below every supported degree, for the monotonicity checks."""
    return verdict['degree'] if verdict['status'] == 'supported' else -1.0


def test_the_researched_values_are_kept():
    assert auc.MIN_CONCENTRATIONS == 3 and auc.MIN_REPLICATES == 3
    assert (auc.SHIFT_FULL_AGREEMENT_PERCENT, auc.SHIFT_ZERO_AGREEMENT_PERCENT) == (10.0, 2.0)
    assert (auc.MASS_FULL_AGREEMENT_PERCENT, auc.MASS_ZERO_AGREEMENT_PERCENT) == (10.0, 50.0)
    assert (auc.STOICHIOMETRY_FULL_AGREEMENT_FOLD, auc.STOICHIOMETRY_ZERO_AGREEMENT_FOLD) == (1.1, 1.5)
    assert (auc.LOW_OVER_KD_FULL_AGREEMENT, auc.LOW_OVER_KD_ZERO_AGREEMENT, auc.HIGH_OVER_KD_FULL_AGREEMENT, auc.HIGH_OVER_KD_ZERO_AGREEMENT) == (0.2, 1.0, 5.0, 1.0)
    assert auc.FIT_RMSD_FULL_AGREEMENT == {'AU': 0.005, 'fringes': 0.003} and auc.FIT_RMSD_ZERO_AGREEMENT == {'AU': 0.02, 'fringes': 0.012}


def test_a_short_concentration_series_is_low_partial_credit_never_conflicting():
    assert concentrations(auc.MIN_CONCENTRATIONS) == {'status': 'supported', 'support_refs': REFS, 'degree': 1.0}
    assert concentrations(2) == {'status': 'supported', 'support_refs': REFS, 'degree': pytest.approx(2 / 3)}
    assert concentrations(1) == {'status': 'supported', 'support_refs': REFS, 'degree': pytest.approx(1 / 3)}      # one c(s) run of the mixture: low, not against
    assert concentrations(8)['degree'] == 1.0
    assert concentrations(0) == {'status': 'unknown', 'support_refs': []}


def test_concentration_series_is_monotone_and_bounded():
    degrees = [concentrations(n)['degree'] for n in range(1, 10)]
    assert degrees == sorted(degrees) and all(0.0 < d <= 1.0 for d in degrees)


def test_replicates_are_the_precision_of_the_mean_and_never_conflicting():
    assert replicates(auc.MIN_REPLICATES) == {'status': 'supported', 'support_refs': REFS, 'degree': 1.0}
    assert replicates(2)['degree'] == pytest.approx(math.sqrt(2 / 3))
    assert replicates(1) == {'status': 'supported', 'support_refs': REFS, 'degree': pytest.approx(math.sqrt(1 / 3))}
    assert replicates(6)['degree'] == 1.0
    degrees = [replicates(n)['degree'] for n in range(1, 10)]
    assert degrees == sorted(degrees) and all(0.0 < d <= 1.0 for d in degrees)


def test_replicates_are_unknown_without_stated_independence():
    for count in (1, 2, 5):
        assert replicates(count, independent='unknown') == {'status': 'unknown', 'support_refs': []}


def test_the_shift_is_gradual_monotone_and_steep_at_the_noise_floor():
    assert shift(-5.0)['status'] == shift(2.0)['status'] == 'conflicting'      # no shift beyond the reproducibility of s
    assert 0.0 < shift(9.9)['degree'] < 1.0 and shift(10.0)['degree'] == 1.0 and shift(30.0)['degree'] == 1.0
    degrees = [degree_or_minus_one(shift(v)) for v in (-5.0, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0, 9.9, 10.0, 30.0)]
    assert degrees == sorted(degrees)
    assert shift(4.0)['degree'] - shift(3.0)['degree'] > shift(10.0)['degree'] - shift(9.0)['degree']      # concave: a percent near the noise matters most
    assert shift(4.0)['degree'] > 0.25      # above the linear ramp


def test_the_stoichiometry_is_symmetric_in_the_order_of_the_partners():
    for ratio in (1.05, 1.2, 1.3, 1.45, 1.6, 2.0):
        assert stoichiometry(ratio)['status'] == stoichiometry(1 / ratio)['status']
        assert degree_or_minus_one(stoichiometry(ratio)) == pytest.approx(degree_or_minus_one(stoichiometry(1 / ratio)))
    assert stoichiometry(1.0)['degree'] == 1.0 and stoichiometry(1 / 1.1)['degree'] == pytest.approx(1.0)
    assert stoichiometry(1 / 1.5)['status'] == 'conflicting'      # 1:1.5 is as far from 1:1 as 1.5:1 (the old |r - 1| gave it 0.42)
    folds = [degree_or_minus_one(stoichiometry(r)) for r in (1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 2.0)]
    assert folds == sorted(folds, reverse=True) and 0.0 < folds[2] < 1.0


def test_the_loading_range_is_judged_on_the_saturation_so_its_two_ends_mirror():
    for x in (1.5, 2.0, 3.0, 4.9):
        low_only = series_range(1 / x, 10.0)
        high_only = series_range(0.05, x)
        assert low_only['degree'] == pytest.approx(high_only['degree'])      # KD/x and x*KD are mirror points of the isotherm
    assert series_range(0.5, 10.0)['degree'] == pytest.approx(0.5) and series_range(0.05, 2.0)['degree'] == pytest.approx(0.5)
    assert series_range(1.0, 10.0)['status'] == 'conflicting' and series_range(0.05, 1.0)['status'] == 'conflicting'
    assert series_range(0.2, 5.0)['degree'] == pytest.approx(1.0) and series_range(0.01, 100.0)['degree'] == 1.0
    lows = [degree_or_minus_one(series_range(low, 10.0)) for low in (1.0, 0.8, 0.5, 0.3, 0.21, 0.2, 0.05)]
    highs = [degree_or_minus_one(series_range(0.05, high)) for high in (1.0, 1.2, 2.0, 3.0, 4.9, 5.0, 50.0)]
    assert lows == sorted(lows) and highs == sorted(highs) and 0.0 < lows[4] < 1.0 and 0.0 < highs[4] < 1.0


def test_mass_and_fit_ramps_fall_with_a_worse_value():
    masses = [degree_or_minus_one(mass(d)) for d in (0.0, -10.0, 11.0, 30.0, -49.0, 50.0)]
    assert masses == sorted(masses, reverse=True) and 0.0 < masses[2] < 1.0 and masses[-1] == -1.0
    fit = [degree_or_minus_one(auc._judge_fit({'fit_rmsd': r, 'fit_rmsd_unit': 'AU', 'fit_refs': REFS})) for r in (0.003, 0.005, 0.006, 0.015, 0.02)]
    assert fit == sorted(fit, reverse=True) and 0.0 < fit[2] < 1.0 and fit[-1] == -1.0
    fringes = [degree_or_minus_one(auc._judge_fit({'fit_rmsd': r, 'fit_rmsd_unit': 'fringes', 'fit_refs': REFS})) for r in (0.003, 0.004, 0.012)]
    assert fringes == sorted(fringes, reverse=True) and 0.0 < fringes[1] < 1.0 and fringes[-1] == -1.0


def test_support_lowers_the_degree_and_never_changes_a_status():
    partial = concentrations(2)
    lowered = apply_support(partial, ['implied'])
    assert lowered['status'] == 'supported' and lowered['degree'] == pytest.approx(2 / 3 * 0.7)
    conflicting = shift(1.0)
    assert apply_support(conflicting, ['about_something_else']) == conflicting


def _graded_with_sd(replicate_count):
    operand = {'status': 'point', 'value': 2.0, 'unit': 'nM', 'source_refs': ['span_sd']}
    count = {'status': 'point', 'value': replicate_count, 'unit': 'count', 'source_refs': ['span_n']}
    native = {'kd_nM': 50.0, 'spread_kind': 'standard_deviation', 'quantities': {'kd_spread': operand, 'replicate_count': count},
              'replicate_count': replicate_count, 'replicate_independent': 'yes', 'replicate_refs': ['span_n']}
    return {'native': native, 'reasons': {'replicates': 'replicate_count_recorded_for_the_sheet'}, 'criteria': {'replicates': {'status': 'unknown', 'support_refs': []}}}


def test_a_standard_deviation_becomes_a_variance_only_from_two_or_more_experiments():
    assert auc._variance(_graded_with_sd(4)) == (pytest.approx(4.0 / 4), None, ['span_sd', 'span_n'])
    assert auc._variance(_graded_with_sd(1))[:2] == (None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate')      # one experiment: supported, but no spread


def test_a_criterion_not_handed_to_the_sheet_keeps_the_graders_answer():
    graded = {'reasons': {'replicates': 'replicate_count_or_independence_unknown'}, 'criteria': {'replicates': {'status': 'unknown', 'support_refs': []}}, 'native': {}}
    assert auc._criterion(graded, 'replicates') == {'status': 'unknown', 'support_refs': []}


def test_the_shift_is_read_against_the_partner_size_when_both_masses_are_stated():
    assert auc._shift_full({'component_mass_larger': None, 'component_mass_smaller': 10.0}) == auc.SHIFT_FULL_AGREEMENT_PERCENT      # not stated: the absolute 10 percent
    equal = auc._shift_full({'component_mass_larger': 50.0, 'component_mass_smaller': 50.0})
    small = auc._shift_full({'component_mass_larger': 100.0, 'component_mass_smaller': 10.0})
    assert equal == auc.SHIFT_FULL_AGREEMENT_PERCENT      # an equal partner: capped at the researched absolute end
    assert auc.SHIFT_FULL_MIN_OVER_ZERO * auc.SHIFT_ZERO_AGREEMENT_PERCENT <= small < equal      # a small partner needs less
    assert shift(5.0, 100.0, 10.0)['degree'] == 1.0 and shift(5.0)['degree'] < 1.0      # a 5 percent rise is right for a partner a tenth of the size
    assert shift(2.0, 100.0, 10.0)['status'] == 'conflicting'      # the zero end is unchanged
    degrees = [degree_or_minus_one(shift(v, 100.0, 10.0)) for v in (1.0, 2.0, 2.5, 3.0, 3.9, 4.0, 8.0)]
    assert degrees == sorted(degrees) and 0.0 < degrees[4] < 1.0


def test_the_mass_zero_end_is_one_smaller_partner_when_its_mass_is_stated():
    assert mass(20.0, smaller=10.0, theoretical=110.0)['status'] == 'conflicting'      # 20 percent off is more than one partner of 10/110 = 9 percent
    assert mass(20.0, smaller=55.0, theoretical=110.0)['status'] == 'supported'      # equal partners: 50 percent zero end, as before
    assert mass(20.0)['degree'] == mass(20.0, smaller=500.0, theoretical=110.0)['degree']      # a big partner is capped at the absolute 50 percent
    degrees = [degree_or_minus_one(mass(d, smaller=10.0, theoretical=110.0)) for d in (0.0, 1.0, 2.0, 5.0, 8.0, 9.2, 15.0)]
    assert degrees == sorted(degrees, reverse=True) and 0.0 < degrees[3] < 1.0 and degrees[-1] == -1.0


def _graded_synthetic(**changes):
    """The grade of the record the synthetic passage gives (the extraction's own record), with the named answers replaced."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_auc_extraction as form
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import auc_passages
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_auc_grader import grade_auc
    answer = auc_passages.synthetic_answer()
    answer.update(changes)
    return grade_auc(form.record_from_answer(answer, auc_passages.SYNTHETIC, 0, 'experiment', 'source', 'assertion'))


def _unavailable(unit=None):
    return {'status': 'unavailable', 'value': None, 'quote': None, 'support': None, 'reason': 'not_stated_in_passage', **({'unit': unit} if unit else {})}


def test_the_grader_records_the_component_masses_for_the_shift_and_the_mass():
    graded = _graded_synthetic()
    native = graded['native']
    assert (native['component_mass_larger'], native['component_mass_smaller'], native['mass_smaller_component']) == (36, 18, 18)
    assert 'span_component_mass_larger' in native['shift_refs'] and 'span_component_mass_smaller' in native['shift_refs'] and 'span_component_mass_smaller' in native['mass_support_refs']
    assert auc._criterion(graded, 'sedimentation_shift')['status'] == 'supported' and auc._criterion(graded, 'mass')['status'] == 'supported'
    without = _graded_synthetic(component_mass_larger=_unavailable('kDa'), component_mass_smaller=_unavailable('kDa'))['native']
    assert without['component_mass_larger'] is None and without['mass_smaller_component'] is None      # not stated: the absolute scales apply


def test_a_stated_no_series_is_a_series_of_one_not_a_conflict():
    no_series = {'status': 'stated', 'value': 'no', 'quote': 'as a concentration series', 'support': 'direct', 'reason': None}
    graded = _graded_synthetic(concentration_series_measured=no_series, concentration_count=_unavailable('count'))
    assert graded['reasons']['concentration_series'] == 'concentration_count_recorded_for_the_sheet' and graded['native']['concentration_count'] == 1
    assert auc._criterion(graded, 'concentration_series') == {'status': 'supported', 'support_refs': ['span_concentration_series_measured'], 'degree': pytest.approx(1 / 3)}
    stated = _graded_synthetic(concentration_series_measured=no_series)      # a stated count of five is recorded as it is
    assert stated['native']['concentration_count'] == 5
