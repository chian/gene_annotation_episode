"""Spectro_direct converter: grader result -> the activity_rate sheet's quantities, criteria and cells; the sheet-side judgements are monotone, bounded,
unknown (not 0) when nothing is stated and have no step at their researched values."""
import math

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spectro_direct_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import COMPONENTS
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_spectro_direct_converter as converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_converter import (
    ABSORBANCE_FULL, ABSORBANCE_ZERO, CONSUMED_FULL_PERCENT, CONSUMED_ZERO_PERCENT, ENZYME_RATIO_FULL, ENZYME_RATIO_ZERO, HIGH_FACTOR, HIGH_ZERO_FACTOR, LOW_FACTOR,
    LOW_ZERO_FACTOR, MIN_REPLICATES, MIN_SUBSTRATE_CONCENTRATIONS, NULL_REASONS, STRAY_LIGHT, SUBSTRATE_CONCENTRATIONS_ZERO, _criterion, convert_spectro_direct)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_grader import grade_spectro_direct
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spectro_direct_cases import (
    sparse_record, synthetic_record)


def judged(record, name):
    return _criterion(grade_spectro_direct(record), name)


def without(record, *names):
    for name in names:
        record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}
    return record


def test_complete_record_fills_effect_variance_precision_and_criteria():
    converted = convert_spectro_direct(grade_spectro_direct(synthetic_record()))
    cells = converted['sheet']['cells']
    assert tuple(cells) == COMPONENTS
    assert cells['measured_effect']['value'] == 5.0e5 and cells['measured_effect']['unit'] == 'M^-1s^-1'      # the best-determined quantity
    assert cells['effect_variance']['value'] == pytest.approx(4.0e4 ** 2) and cells['effect_variance']['unit'] == 'M^-1s^-1_squared'
    assert converted['extraction']['quantity_kind'] == 'catalytic_efficiency' and converted['extraction']['assay_type'] == 'activity_rate'
    assert {c['status'] for c in converted['extraction']['interpretations'].values()} == {'supported'}
    assert set(converted['extraction']['interpretations']) == {'background_alternatives', 'attribution_supported', 'calibration_applicability', 'rate_regime', 'kinetic_model', 'normalization_basis',
                                                               'sampling_basis', 'assertion_relevance', 'condition_scope', 'variance_correspondence'}
    assert converted['enzyme_mass_g_per_mol'] == 48000.0 and converted['dependence']['analyte_preparation_ref'] == 'prep_enzyme_a'
    assert converted['dependence']['immobilized_preparation_ref'] is None and converted['dependence']['surface_ref'] is None
    assert converted['direction_field_support'] == 'direct' and 'qualitative_effect' not in converted
    assert 'effect' not in converted['null_components'] and set(NULL_REASONS) <= set(converted['null_components'])


def test_the_effect_is_the_best_determined_stated_quantity_in_the_class_order_with_its_own_unit_and_spread():
    r = without(synthetic_record(), 'catalytic_efficiency')
    converted = convert_spectro_direct(grade_spectro_direct(r))
    assert converted['extraction']['quantity_kind'] == 'turnover' and converted['extraction']['quantities']['effect']['value'] == 20.0
    assert converted['extraction']['quantities']['effect_variance']['value'] == pytest.approx(1.5 ** 2) and converted['extraction']['quantities']['effect_variance']['unit'] == 's^-1_squared'
    converted = convert_spectro_direct(grade_spectro_direct(without(r, 'turnover')))
    assert converted['extraction']['quantity_kind'] == 'rate' and converted['extraction']['quantities']['effect']['unit'] == 'U/mg'
    converted = convert_spectro_direct(grade_spectro_direct(without(r, 'turnover', 'specific_activity')))
    assert converted['extraction']['quantity_kind'] == 'rate_ratio' and converted['sheet']['cells']['measured_effect']['unit'] == 'fold'      # 'fold' is a unit of the rate ratio
    assert converted['extraction']['quantities']['effect_variance']['value'] == pytest.approx(144.0)


def test_other_units_of_the_vocabulary_are_converted_exactly_and_the_stated_number_is_kept():
    r = synthetic_record()
    r['quantities']['catalytic_efficiency'] = point(500.0, 'mM^-1 s^-1', 'k', ['s'])
    r['quantities']['catalytic_efficiency_spread'] = point(40.0, 'mM^-1 s^-1', 'k', ['s'])
    effect = convert_spectro_direct(grade_spectro_direct(r))['extraction']['quantities']
    assert effect['effect']['value'] == pytest.approx(5.0e5) and effect['effect_variance']['value'] == pytest.approx(4.0e4 ** 2)
    r = without(synthetic_record(), 'catalytic_efficiency')
    r['quantities']['turnover'] = point(1200.0, 'min^-1', 'k', ['s'])
    r['quantities']['turnover_spread'] = point(90.0, 'min^-1', 'k', ['s'])
    effect = convert_spectro_direct(grade_spectro_direct(r))['extraction']['quantities']
    assert effect['effect']['value'] == pytest.approx(20.0) and effect['effect_variance']['value'] == pytest.approx(1.5 ** 2)
    r = without(synthetic_record(), 'catalytic_efficiency', 'turnover')
    r['quantities']['specific_activity'] = point(25000.0, 'nmol/min/mg', 'k', ['s'])
    assert convert_spectro_direct(grade_spectro_direct(r))['extraction']['quantities']['effect']['value'] == pytest.approx(25.0)


def test_standard_deviation_needs_independent_replicates_and_divides_by_n_and_other_spread_kinds_give_no_variance():
    r = synthetic_record()
    r['spread_kind'] = 'standard_deviation'
    assert convert_spectro_direct(grade_spectro_direct(r))['sheet']['cells']['effect_variance']['value'] == pytest.approx(4.0e4 ** 2 / 3)
    r['facts']['independent_replicates'] = fact('unknown')
    converted = convert_spectro_direct(grade_spectro_direct(r))
    assert converted['sheet']['cells']['effect_variance']['value'] is None and converted['null_components']['effect_variance'].startswith('sd_needs_independent')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']
    r['spread_kind'] = 'confidence_interval'
    assert convert_spectro_direct(grade_spectro_direct(r))['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    r['spread_kind'] = None
    assert convert_spectro_direct(grade_spectro_direct(r))['null_components']['effect_variance'] == 'spread_kind_not_stated'
    r = without(synthetic_record(), 'catalytic_efficiency_spread')
    assert convert_spectro_direct(grade_spectro_direct(r))['null_components']['effect_variance'] == 'catalytic_efficiency_spread_not_given'


def test_no_quantity_leaves_the_effect_null_and_the_papers_statement_fixes_the_direction():
    r = without(synthetic_record(), 'catalytic_efficiency', 'turnover', 'specific_activity', 'rate_over_control')
    converted = convert_spectro_direct(grade_spectro_direct(r))
    assert converted['sheet']['cells']['measured_effect']['value'] is None and converted['null_components']['effect'] == 'no_activity_quantity_given_as_a_point_value'
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_exp_synthetic_spectro_direct_1']} and converted['direction_field_support'] == 'direct'
    r['facts']['activity_detected_above_control'] = fact('no', ['s'], 'implied')
    converted = convert_spectro_direct(grade_spectro_direct(r))
    assert converted['qualitative_effect']['statement'] == 'interaction_not_detected' and converted['direction_field_support'] == 'implied'
    r['facts']['activity_detected_above_control'] = fact('unknown')
    converted = convert_spectro_direct(grade_spectro_direct(r))
    assert 'qualitative_effect' not in converted and converted['direction_field_support'] is None


def test_conflicting_and_unknown_members_combine_by_the_rule():
    r = synthetic_record()
    r['facts']['no_substrate_control'] = fact('unknown')
    r['facts']['no_enzyme_control'] = fact('no', ['s'])
    r['facts']['inactive_enzyme_control'] = fact('no', ['s'])
    interpretations = convert_spectro_direct(grade_spectro_direct(r))['extraction']['interpretations']
    assert interpretations['background_alternatives']['status'] == 'conflicting'
    r['facts']['no_enzyme_control'] = fact('yes', ['s'])
    assert convert_spectro_direct(grade_spectro_direct(r))['extraction']['interpretations']['background_alternatives']['status'] == 'unknown'


def test_the_converter_holds_the_researched_constants_with_their_values():
    assert (CONSUMED_FULL_PERCENT, CONSUMED_ZERO_PERCENT, ENZYME_RATIO_FULL, ENZYME_RATIO_ZERO, MIN_SUBSTRATE_CONCENTRATIONS, SUBSTRATE_CONCENTRATIONS_ZERO) == (10.0, 90.0, 0.01, 1.0, 6, 2)
    assert (LOW_FACTOR, LOW_ZERO_FACTOR, HIGH_FACTOR, HIGH_ZERO_FACTOR, ABSORBANCE_FULL, ABSORBANCE_ZERO, STRAY_LIGHT, MIN_REPLICATES) == (0.2, 1.0, 10.0, 1.0, 1.0, 3.0, 0.01, 3)


def test_every_number_a_judge_uses_is_a_named_expert_review_constant():
    import inspect
    source = inspect.getsource(converter).splitlines()
    for name in ('CONSUMED_FULL_PERCENT', 'CONSUMED_ZERO_PERCENT', 'ENZYME_RATIO_FULL', 'ENZYME_RATIO_ZERO', 'MIN_SUBSTRATE_CONCENTRATIONS', 'SUBSTRATE_CONCENTRATIONS_ZERO', 'LOW_FACTOR', 'LOW_ZERO_FACTOR', 'HIGH_FACTOR',
                 'HIGH_ZERO_FACTOR', 'ABSORBANCE_FULL', 'ABSORBANCE_ZERO', 'STRAY_LIGHT', 'MIN_REPLICATES', 'PERCENT_PER_FRACTION', 'GRAMS_PER_MOL_PER_KDA'):
        lines = [line for line in source if line.startswith(name + ' = ')]
        assert len(lines) == 1 and ('EXPERT_REVIEW' in lines[0] or 'FIXED_BY_DEFINITION' in lines[0]), name
        if 'EXPERT_REVIEW' in lines[0]:
            assert 'owner to confirm' in lines[0], name


def with_consumed(percent):
    r = synthetic_record()
    r['quantities']['substrate_consumed_percent'] = point(percent, 'percent', 'c', ['s'])
    return judged(r, 'initial_rate_regime')


def degrees(verdicts):
    return [v['degree'] if v['status'] == 'supported' else 0.0 for v in verdicts]


def test_the_consumed_share_is_judged_gradually_monotone_bounded_and_conflicting_only_at_the_zero_end():
    percents = [1, 5, 10, 11, 15, 20, 30, 50, 70, 89]
    verdicts = [with_consumed(p) for p in percents]
    assert all(v['status'] == 'supported' for v in verdicts)
    ds = degrees(verdicts)
    assert ds == sorted(ds, reverse=True) and all(0.0 <= d <= 1.0 for d in ds)
    assert ds[2] == 1.0 and 0.9 < ds[3] < 1.0 and 0.0 < ds[-1] < 0.1      # just over the researched 10 percent is partial credit, not a step
    assert with_consumed(90)['status'] == 'conflicting' and with_consumed(99)['status'] == 'conflicting'


def with_enzyme(nm):
    r = synthetic_record()
    r['quantities']['enzyme_concentration'] = point(nm, 'nM', 'e', ['s'])
    return judged(r, 'enzyme_substrate_ratio')


def test_the_enzyme_over_substrate_plus_km_is_judged_on_the_log_scale_gradually():
    ratios = [1e-4, 0.01, 0.02, 0.1, 0.5, 0.9]      # E / (S + Km), with S + Km = 240 uM
    verdicts = [with_enzyme(r * 240000) for r in ratios]
    ds = degrees(verdicts)
    assert ds == sorted(ds, reverse=True) and ds[0] == 1.0 and ds[1] == 1.0 and 0.8 < ds[2] < 1.0 and 0.0 < ds[-1] < 0.05
    assert with_enzyme(1.0 * 240000)['status'] == 'conflicting' and with_enzyme(5 * 240000)['status'] == 'conflicting'
    assert judged(without(synthetic_record(), 'km'), 'enzyme_substrate_ratio')['status'] == 'unknown'      # not stated is unknown, never 0


def with_series(values, km=40.0):
    r = synthetic_record()
    r['concentration_series'] = {**r['concentration_series'], 'value': values}
    r['quantities']['km'] = point(km, 'uM', 'k', ['s'])
    return judged(r, 'substrate_range')


def test_the_substrate_series_is_judged_on_saturation_and_count_gradually_and_a_short_series_is_never_conflicting():
    full = [4.0, 8.0, 20.0, 80.0, 200.0, 400.0]      # 0.1 to 10 x Km, six concentrations
    assert with_series(full)['degree'] == 1.0
    high = [with_series([4.0, 6.0, 8.0, 12.0, 20.0, 40.0 * h])['degree'] for h in (10, 8, 5, 3, 2, 1.2)]
    assert high == sorted(high, reverse=True) and high[0] == 1.0 and 0.0 < high[-1] < 0.5      # a top just under the researched 10 x Km is partial credit
    low = [with_series([40.0 * f, 80.0, 120.0, 200.0, 300.0, 400.0])['degree'] for f in (0.1, 0.2, 0.3, 0.5, 0.8)]
    assert low == sorted(low, reverse=True) and low[0] == 1.0 and low[1] == 1.0 and 0.0 < low[-1] < 0.5
    assert with_series([40.0, 80.0, 400.0])['status'] == 'conflicting'      # the lowest at the Km is the zero end of the low ramp
    assert with_series([4.0, 400.0])['degree'] == 0.0 and with_series([4.0, 400.0])['status'] == 'supported'      # two concentrations: no residual degree of freedom, degree 0, never conflicting
    counts = [with_series([4.0, 8.0, 20.0, 80.0, 200.0, 400.0][:n - 1] + [400.0])['degree'] for n in (2, 3, 4, 5, 6)]      # the same top, n concentrations
    assert counts == sorted(counts) and counts[0] == 0.0 and counts[-1] == 1.0 and counts[1] == pytest.approx(0.25) and counts[3] == pytest.approx(0.75)
    one = with_series([400.0])
    assert one['status'] == 'supported' and one['degree'] == 0.0      # one concentration is a short series, not a badly placed one
    assert judged(without(synthetic_record(), 'km'), 'substrate_range')['status'] == 'unknown'


def with_absorbance(a):
    r = synthetic_record()
    r['quantities']['absorbance_max'] = point(a, 'AU', 'a', ['s'])
    return judged(r, 'absorbance_range')


def test_the_absorbance_is_judged_on_the_stray_light_bias_gradually():
    levels = [0.2, 0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 2.9]
    ds = degrees([with_absorbance(a) for a in levels])
    assert ds == sorted(ds, reverse=True) and ds[2] == 1.0 and 0.9 < ds[3] < 1.0 and 0.0 < ds[-1] < 0.1
    assert with_absorbance(3.0)['status'] == 'conflicting' and with_absorbance(4.0)['status'] == 'conflicting'
    bias = lambda a: 1 - -math.log10((10 ** -a + STRAY_LIGHT) / (1 + STRAY_LIGHT)) / a
    assert bias(1.0) == pytest.approx(0.037, abs=0.002) and bias(2.0) == pytest.approx(0.15, abs=0.01) and bias(3.0) == pytest.approx(0.35, abs=0.02)


def test_replicates_are_precision_never_conflicting_and_unknown_without_independence():
    def with_count(n, independent='yes'):
        r = synthetic_record()
        r['quantities']['replicate_count'] = point(n, 'count', 'n', ['s'])
        r['facts']['independent_replicates'] = fact(independent, ['s'] if independent != 'unknown' else [])
        return judged(r, 'replicates')
    assert [with_count(n)['degree'] for n in (1, 2, 3, 6)] == [pytest.approx(math.sqrt(1 / 3)), pytest.approx(math.sqrt(2 / 3)), 1.0, 1.0]
    assert with_count(3, 'unknown')['status'] == 'unknown'


def test_unstated_values_are_unknown_not_zero():
    r = sparse_record()
    for name in ('initial_rate_regime', 'enzyme_substrate_ratio', 'substrate_range', 'absorbance_range', 'replicates'):
        assert judged(r, name)['status'] == 'unknown' and 'degree' not in judged(r, name), name


def test_support_lowers_the_degree_of_a_supported_criterion_and_never_changes_a_status():
    base = convert_spectro_direct(grade_spectro_direct(synthetic_record()))['extraction']['interpretations']
    r = synthetic_record()
    r['facts']['purified_enzyme'] = fact('yes', ['s'], 'implied')
    r['facts']['native_substrate'] = fact('yes', ['s'], 'about_something_else')
    lowered = convert_spectro_direct(grade_spectro_direct(r))['extraction']['interpretations']
    assert lowered['condition_scope']['status'] == 'supported' and lowered['condition_scope']['degree'] == pytest.approx(0.7)
    assert lowered['assertion_relevance']['degree'] == pytest.approx(0.3) and base['condition_scope'].get('degree') is None
    assert {c['status'] for c in lowered.values()} == {'supported'}


def test_a_sheet_criterion_carries_the_smallest_degree_of_its_members():
    r = synthetic_record()
    r['quantities']['substrate_consumed_percent'] = point(50.0, 'percent', 'c', ['s'])
    interpretations = convert_spectro_direct(grade_spectro_direct(r))['extraction']['interpretations']
    assert interpretations['rate_regime']['degree'] == pytest.approx(with_consumed(50.0)['degree'])
