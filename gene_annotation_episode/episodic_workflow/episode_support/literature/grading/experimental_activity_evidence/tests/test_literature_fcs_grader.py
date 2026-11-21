"""FCS grader: each criterion's rule on records, with the arithmetic worked by hand."""
from math import log, log10, sqrt

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fcs_record import fact, point, unavailable
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_grader import CRITERIA, grade_fcs
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fcs_cases import sparse_record, synthetic_record

HANDED = {'diffusion_change', 'mass_consistency', 'saturation', 'labelled_range', 'labelled_over_kd', 'concentration_series', 'acquisition', 'replicates'}      # equilibrium is ruled by its fact in the synthetic record


def _mass_degree(fold):
    """The degree of the mass consistency: linear in the logarithm of the fold, 1 at a fold of 1.5, 0 at a fold of 3."""
    return (log(3.0) - log(fold)) / (log(3.0) - log(1.5))


def status(record, criterion):
    """The status after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_fcs(record), criterion)['status']


def grader_status(record, criterion):
    return grade_fcs(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_fcs(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_what_the_grader_recorded():
    graded = grade_fcs(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 21
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == HANDED
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'} and all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['kd_nM'] == 20.0 and native['constant_name'] == 'kd' and native['constant_nM'] == 20.0 and graded['experiment_type'] == 'fcs'
    assert native['labelled_over_kd'] == pytest.approx(0.1) and native['labelled_nM'] == 2.0 and native['particle_number'] == 0.8
    assert native['diffusion_ratio'] == pytest.approx(1.8) and native['expected_diffusion_ratio'] == pytest.approx(6 ** (1 / 3))
    assert native['concentration_count'] == 12 and native['concentration_low_over_constant'] == pytest.approx(0.05) and native['concentration_high_over_constant'] == pytest.approx(102.4)
    assert native['incubation_min'] == 20.0 and native['acquisition_total_s'] == 150.0 and native['diffusion_model'] == 'two_component' and native['readout_signal'] == 'diffusion_time'


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_fcs(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['criteria']['diffusion_change']['status'] == 'unknown' and graded['native']['kd_nM'] == 20.0


def test_the_diffusion_change_by_times_then_by_coefficients():
    r = synthetic_record()
    assert (grader_status(r, 'diffusion_change'), reason(r, 'diffusion_change')) == ('unknown', 'diffusion_ratio_recorded_for_the_sheet')
    r['quantities']['bound_diffusion_time'] = point(0.078, 'ms', 'b', ['s'])            # 78 us in ms: 1.3
    assert grade_fcs(r)['native']['diffusion_ratio'] == pytest.approx(1.3) and grade_fcs(r)['native']['diffusion_refs'] == ['span_exp_synthetic_fcs_1', 's']
    assert status(r, 'diffusion_change') == 'supported'
    r['quantities']['bound_diffusion_time'] = point(66.0, 'us', 'b', ['s'])             # 1.1
    assert reason(r, 'diffusion_change') == 'diffusion_ratio_recorded_for_the_sheet' and status(r, 'diffusion_change') == 'supported'
    missing(r, 'bound_diffusion_time')                                                 # the coefficients are used: 280 / 156 = 1.79
    assert status(r, 'diffusion_change') == 'supported' and grade_fcs(r)['native']['diffusion_ratio'] == pytest.approx(280 / 156)
    r['quantities']['bound_diffusion_coefficient'] = point(280.0, 'um2/s', 'b', ['s'])  # 280 / 280 = 1: no change of the diffusion
    assert reason(r, 'diffusion_change') == 'diffusion_ratio_recorded_for_the_sheet' and status(r, 'diffusion_change') == 'conflicting'
    r['quantities']['bound_diffusion_coefficient'] = point(250.0, 'um2/s', 'b', ['s'])  # 280 / 250 = 1.12
    missing(r, 'free_diffusion_coefficient')
    assert reason(r, 'diffusion_change') == 'diffusion_values_not_given' and status(r, 'diffusion_change') == 'unknown'
    r['readout_signal'] = 'cross_correlation'
    assert reason(r, 'diffusion_change') == 'readout_is_not_the_diffusion' and status(r, 'diffusion_change') == 'not_applicable'


def test_the_mass_consistency_follows_the_cube_root_law_within_its_factor():
    r = synthetic_record()                                                                # 6^(1/3) = 1.817, ratio 1.8
    assert (grader_status(r, 'mass_consistency'), reason(r, 'mass_consistency')) == ('unknown', 'mass_consistency_recorded_for_the_sheet')
    assert status(r, 'mass_consistency') == 'supported' and _criterion(grade_fcs(r), 'mass_consistency')['degree'] == 1.0
    r['quantities']['mass_ratio'] = point(2.0, 'ratio', 'm', ['s'])                       # 2^(1/3) = 1.26 (a doubling of the mass: 26 percent): 1.8 / 1.26 = 1.43, inside 1.5
    assert status(r, 'mass_consistency') == 'supported' and grade_fcs(r)['native']['expected_diffusion_ratio'] == pytest.approx(1.2599, abs=1e-4)
    assert grade_fcs(r)['native']['mass_consistency_refs'] == ['s', 'span_exp_synthetic_fcs_1']
    r['quantities']['mass_ratio'] = point(1.5, 'ratio', 'm', ['s'])                       # 1.5^(1/3) = 1.145: 1.8 / 1.145 = 1.57, a little outside 1.5: a degree just below 1 (linear in the logarithm of the fold)
    assert reason(r, 'mass_consistency') == 'mass_consistency_recorded_for_the_sheet' and status(r, 'mass_consistency') == 'supported'
    assert _criterion(grade_fcs(r), 'mass_consistency')['degree'] == pytest.approx(_mass_degree(1.8 / 1.5 ** (1 / 3)))
    r['quantities']['mass_ratio'] = point(27.0, 'ratio', 'm', ['s'])                      # 27^(1/3) = 3: 3 / 1.8 = 1.67, outside 1.5 the other way: degree from the logarithm of the fold 1.667
    assert status(r, 'mass_consistency') == 'supported' and _criterion(grade_fcs(r), 'mass_consistency')['degree'] == pytest.approx(_mass_degree(3.0 / 1.8))
    r['quantities']['mass_ratio'] = point(8.0, 'ratio', 'm', ['s'])                       # 8^(1/3) = 2: 2 / 1.8 = 1.11
    assert status(r, 'mass_consistency') == 'supported' and _criterion(grade_fcs(r), 'mass_consistency')['degree'] == 1.0
    r['quantities']['mass_ratio'] = point(0.1, 'ratio', 'm', ['s'])                       # 0.1^(1/3) = 0.464: 1.8 / 0.464 = 3.9, beyond 3
    assert status(r, 'mass_consistency') == 'conflicting' and 'degree' not in _criterion(grade_fcs(r), 'mass_consistency')
    r['quantities']['mass_ratio'] = point(216.0, 'ratio', 'm', ['s'])                     # 216^(1/3) = 6: 6 / 1.8 = 3.33, beyond 3 the other way
    assert status(r, 'mass_consistency') == 'conflicting'
    r['quantities']['mass_ratio'] = point(6.0, 'ratio', 'm', ['s'])
    missing(r, 'mass_ratio')
    assert reason(r, 'mass_consistency') == 'mass_ratio_or_diffusion_not_given' and status(r, 'mass_consistency') == 'unknown'
    r['readout_signal'] = 'brightness'
    assert status(r, 'mass_consistency') == 'unknown'                                     # a diffusion ratio is given: the readout does not make it not applicable
    for name in ('free_diffusion_time', 'bound_diffusion_time', 'free_diffusion_coefficient', 'bound_diffusion_coefficient'):
        missing(r, name)
    assert reason(r, 'mass_consistency') == 'readout_is_not_the_diffusion' and status(r, 'mass_consistency') == 'not_applicable'


def test_saturation_needs_the_plateau_to_be_reached():
    r = synthetic_record()
    r['quantities']['fraction_bound_maximum'] = point(50.0, 'percent', 'f', ['s'])
    assert (grader_status(r, 'saturation'), reason(r, 'saturation')) == ('unknown', 'fraction_bound_maximum_recorded_for_the_sheet')
    assert grade_fcs(r)['native']['fraction_bound_maximum'] == 50.0 and grade_fcs(r)['native']['fraction_bound_maximum_refs'] == ['s']
    for value, expected in ((92.0, 'supported'), (80.0, 'supported'), (50.0, 'supported'), (21.0, 'supported'), (20.0, 'conflicting'), (5.0, 'conflicting')):
        r['quantities']['fraction_bound_maximum'] = point(value, 'percent', 'f', ['s'])
        assert status(r, 'saturation') == expected, value
    r['quantities']['fraction_bound_maximum'] = point(50.0, 'percent', 'f', ['s'])         # halfway from 20 down to 80: a degree of 0.5
    assert _criterion(grade_fcs(r), 'saturation') == {'status': 'supported', 'support_refs': ['s'], 'degree': pytest.approx(0.5)}
    missing(r, 'fraction_bound_maximum')
    assert reason(r, 'saturation') == 'fraction_bound_maximum_not_given' and status(r, 'saturation') == 'unknown'


def test_the_diffusion_model_two_component_one_component_and_the_others():
    r = synthetic_record()
    assert reason(r, 'diffusion_model') == 'two_component_with_free_time_fixed'
    r['facts']['free_diffusion_time_fixed'] = fact('no', ['s'])
    assert reason(r, 'diffusion_model') == 'two_component_with_free_time_not_fixed' and status(r, 'diffusion_model') == 'conflicting'
    r['facts']['free_diffusion_time_fixed'] = fact('unknown')
    assert reason(r, 'diffusion_model') == 'free_time_fixing_not_stated' and status(r, 'diffusion_model') == 'unknown'
    r['diffusion_model'] = 'one_component'
    assert reason(r, 'diffusion_model') == 'one_component_with_reference_values' and status(r, 'diffusion_model') == 'supported'
    missing(r, 'bound_diffusion_time')
    missing(r, 'free_diffusion_coefficient')                                              # no complete pair is left
    assert reason(r, 'diffusion_model') == 'one_component_needs_free_and_bound_reference_values' and status(r, 'diffusion_model') == 'unknown'
    for model in ('anomalous', 'other'):
        r['diffusion_model'] = model
        assert reason(r, 'diffusion_model') == 'diffusion_model_anomalous_or_other' and status(r, 'diffusion_model') == 'unknown'
    r['diffusion_model'] = None
    assert reason(r, 'diffusion_model') == 'diffusion_model_not_stated' and status(r, 'diffusion_model') == 'unknown'
    r['readout_signal'] = 'cross_correlation'
    assert reason(r, 'diffusion_model') == 'readout_is_not_the_diffusion' and status(r, 'diffusion_model') == 'not_applicable'


@pytest.mark.parametrize('criterion, fact_name', [('triplet_state', 'triplet_state_modelled'), ('volume_calibration', 'confocal_volume_calibrated'), ('brightness', 'brightness_change_accounted'), ('background', 'background_corrected'), ('aggregates', 'aggregates_checked'), ('photobleaching', 'photobleaching_or_saturation_checked'), ('surface_adsorption', 'surface_adsorption_prevented'), ('labelling', 'labelling_does_not_alter_binding'), ('specificity_control', 'nonbinding_control_done')])
def test_single_fact_criteria_are_the_one_fact(criterion, fact_name):
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('unknown', 'unknown'), ('not_applicable', 'not_applicable')):
        r['facts'][fact_name] = fact(answer, ['s'])
        assert status(r, criterion) == expected


def test_crosstalk_is_the_fact_and_an_unstated_one_is_not_applicable_for_a_single_colour_readout():
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('unknown', 'not_applicable'), ('not_applicable', 'not_applicable')):       # the readout is a diffusion time
        r['facts']['crosstalk_corrected'] = fact(answer, ['s'])
        assert status(r, 'crosstalk') == expected
    r['facts']['crosstalk_corrected'] = fact('unknown')
    assert reason(r, 'crosstalk') == 'single_colour_readout'
    for readout, expected in (('cross_correlation', 'unknown'), (None, 'unknown'), ('brightness', 'not_applicable'), ('diffusion_coefficient', 'not_applicable')):
        r['readout_signal'] = readout
        assert status(r, 'crosstalk') == expected
    r['readout_signal'] = 'cross_correlation'
    r['facts']['crosstalk_corrected'] = fact('no', ['s'])
    assert reason(r, 'crosstalk') == 'fact_answered_no' and status(r, 'crosstalk') == 'conflicting'


def test_labelled_range_by_the_particle_number_then_by_the_concentration():
    r = synthetic_record()                                                                 # N 0.8
    # inside 0.1..10 full credit (no degree); just outside, partial credit falling in the logarithm to 0 a decade beyond (0.01 and 100): no step at the window
    for number, expected, expected_degree in ((0.1, 'supported', None), (10.0, 'supported', None), (0.09, 'supported', log10(0.09 / 0.01)), (10.5, 'supported', log10(100.0 / 10.5)),
                                              (0.01, 'conflicting', None), (100.0, 'conflicting', None), (0.005, 'conflicting', None)):
        r['quantities']['particle_number'] = point(number, 'molecules', 'n', ['s'])
        judged = _criterion(grade_fcs(r), 'labelled_range')
        assert judged['status'] == expected and judged.get('degree') == (None if expected_degree is None else pytest.approx(expected_degree)), number
        assert (grader_status(r, 'labelled_range'), reason(r, 'labelled_range')) == ('unknown', 'particle_number_recorded_for_the_sheet')
    r['quantities']['particle_number'] = point(10.5, 'molecules', 'n', ['s'])
    assert grade_fcs(r)['native']['particle_number'] == 10.5 and grade_fcs(r)['native']['labelled_range_refs'] == ['s', 'span_exp_synthetic_fcs_1'] and _criterion(grade_fcs(r), 'labelled_range')['support_refs'] == ['s', 'span_exp_synthetic_fcs_1']      # the brightness ref is in the refs: the count rate is judged
    assert grade_fcs(r)['native']['count_rate_kHz'] == pytest.approx(10.5 * 12.0) and grade_fcs(r)['native']['particle_number_derived'] is False
    missing(r, 'particle_number')                                                          # 2 nM in 0.66 fL: 2 * 0.66 * 0.6022 = 0.795 molecules, derived from the detection volume
    assert reason(r, 'labelled_range') == 'particle_number_derived_from_volume_recorded_for_the_sheet' and status(r, 'labelled_range') == 'supported'
    assert grade_fcs(r)['native']['particle_number_used'] == pytest.approx(0.795, abs=1e-3) and grade_fcs(r)['native']['particle_number_derived'] is True
    assert grade_fcs(r)['native']['count_rate_kHz'] == pytest.approx(0.795 * 12.0, abs=0.02) and grade_fcs(r)['native']['labelled_range_refs'] == ['span_exp_synthetic_fcs_1']
    r['quantities']['labelled_concentration'] = point(200.0, 'nM', 'l', ['s'])             # 200 nM in 0.66 fL: 79.5 molecules, in the log-linear fall (partial credit)
    assert 0 < _criterion(grade_fcs(r), 'labelled_range')['degree'] < 1
    r['quantities']['labelled_concentration'] = point(2.0, 'nM', 'l', ['s'])
    missing(r, 'detection_volume')                                                         # 2 nM, no volume: judged on the concentration alone
    assert reason(r, 'labelled_range') == 'labelled_concentration_recorded_for_the_sheet' and status(r, 'labelled_range') == 'supported'
    for value, unit, expected in ((0.3, 'nM', 'supported'), (30.0, 'nM', 'supported'), (0.29, 'nM', 'supported'), (31.0, 'nM', 'supported'), (100.0, 'pM', 'supported'),
                                  (0.03, 'nM', 'conflicting'), (300.0, 'nM', 'conflicting'), (0.03, 'uM', 'supported')):
        r['quantities']['labelled_concentration'] = point(value, unit, 'l', ['s'])
        assert status(r, 'labelled_range') == expected, (value, unit)
    assert reason(r, 'labelled_range') == 'labelled_concentration_recorded_for_the_sheet' and grade_fcs(r)['native']['labelled_nM'] == pytest.approx(30.0)
    r['quantities']['labelled_concentration'] = point(0.29, 'nM', 'l', ['s'])               # just below 0.3 nM: nearly full credit, not a failure
    assert _criterion(grade_fcs(r), 'labelled_range')['degree'] == pytest.approx(log10(0.29 / 0.03))
    r['quantities']['labelled_concentration'] = point(100.0, 'pM', 'l', ['s'])              # 0.1 nM: about half the decade from 0.3 down to 0.03 nM
    assert status(r, 'labelled_range') == 'supported' and _criterion(grade_fcs(r), 'labelled_range')['degree'] == pytest.approx(log10(0.1 / 0.03))
    r['quantities']['particle_number'] = point(0.8, 'molecules', 'n', ['s'])               # the particle number decides when both are given
    assert status(r, 'labelled_range') == 'supported' and 'degree' not in _criterion(grade_fcs(r), 'labelled_range')
    missing(r, 'particle_number')
    missing(r, 'labelled_concentration')
    assert reason(r, 'labelled_range') == 'labelled_concentration_not_given' and status(r, 'labelled_range') == 'unknown'


def test_labelled_over_kd_by_ratio_and_by_fact():
    r = synthetic_record()                                                                 # labelled 2 nM, KD 20 nM: 0.1 x KD
    assert (grader_status(r, 'labelled_over_kd'), reason(r, 'labelled_over_kd')) == ('unknown', 'labelled_over_kd_recorded_for_the_sheet')
    assert grade_fcs(r)['native']['labelled_over_kd'] == pytest.approx(0.1) and grade_fcs(r)['native']['tight_binding_analysis'] is True
    r['quantities']['labelled_concentration'] = point(20.0, 'nM', 'l', ['s'])              # 1.0 x KD: exactly the limit, allowed, with the full degree
    assert _criterion(grade_fcs(r), 'labelled_over_kd')['status'] == 'supported' and _criterion(grade_fcs(r), 'labelled_over_kd')['degree'] == 1.0
    r['quantities']['labelled_concentration'] = point(0.1, 'uM', 'l', ['s'])               # 100 nM = 5 x KD
    assert _criterion(grade_fcs(r), 'labelled_over_kd') == {'status': 'supported', 'support_refs': ['s', 'span_exp_synthetic_fcs_1']}      # tight binding considered: yes, no degree
    r['facts']['tight_binding_considered'] = fact('unknown')
    assert grade_fcs(r)['native']['tight_binding_analysis'] is False
    assert status(r, 'labelled_over_kd') == 'supported' and _criterion(grade_fcs(r), 'labelled_over_kd')['degree'] == pytest.approx(0.3888, abs=1e-3)      # 5 x KD without a tight-binding analysis: ln(6 / 3.5) / ln 4 (was linear, 5 / 9)
    r['quantities']['labelled_concentration'] = point(0.2, 'uM', 'l', ['s'])               # 10 x KD: at the zero-agreement limit
    assert status(r, 'labelled_over_kd') == 'conflicting' and 'degree' not in _criterion(grade_fcs(r), 'labelled_over_kd')
    r['quantities']['labelled_concentration'] = point(0.1, 'uM', 'l', ['s'])
    r['fit_model'] = 'quadratic'
    assert status(r, 'labelled_over_kd') == 'supported' and 'degree' not in _criterion(grade_fcs(r), 'labelled_over_kd')
    r['fit_model'] = '1:1'
    missing(r, 'labelled_concentration')                                                   # no ratio: the fact decides
    r['facts']['labelled_partner_at_or_below_kd'] = fact('yes', ['s'])
    assert reason(r, 'labelled_over_kd') == 'labelled_at_or_below_kd'
    r['facts']['labelled_partner_at_or_below_kd'] = fact('no', ['s'])
    assert reason(r, 'labelled_over_kd') == 'labelled_above_kd_without_tight_binding_analysis'
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])
    assert status(r, 'labelled_over_kd') == 'supported'
    r['facts']['labelled_partner_at_or_below_kd'] = fact('unknown')
    assert reason(r, 'labelled_over_kd') == 'labelled_or_kd_missing' and status(r, 'labelled_over_kd') == 'unknown'


def test_concentration_series_by_count_and_span():
    r = synthetic_record()
    r['concentration_series']['value'] = [4.0, 16.0, 40.0, 80.0, 120.0, 160.0, 190.0, 200.0]   # eight values (KD 20 nM), lowest 0.2 x KD, highest 10 x KD: on the limits
    assert (grader_status(r, 'concentration_series'), reason(r, 'concentration_series')) == ('unknown', 'concentration_series_recorded_for_the_sheet')
    native = grade_fcs(r)['native']
    assert native['concentration_count'] == 8 and native['concentration_low_over_constant'] == pytest.approx(0.2) and native['concentration_high_over_constant'] == pytest.approx(10.0)
    assert native['concentration_span_refs'] == ['span_exp_synthetic_fcs_1'] and native['concentration_count_refs'] == ['span_exp_synthetic_fcs_1']
    assert _criterion(grade_fcs(r), 'concentration_series') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_fcs_1'], 'degree': 1.0}
    r['concentration_series']['value'] = [4.0, 16.0, 40.0, 80.0, 120.0, 160.0, 200.0]          # seven, same span: partial credit sqrt(7 / 8), no longer a failure
    assert _criterion(grade_fcs(r), 'concentration_series') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_fcs_1'], 'degree': pytest.approx(sqrt(7 / 8))}
    r['concentration_series']['value'] = [4.0, 40.0, 200.0]                                    # three: low partial credit sqrt(3 / 8), never conflicting
    assert _criterion(grade_fcs(r), 'concentration_series') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_fcs_1'], 'degree': pytest.approx(sqrt(3 / 8))}
    r['concentration_series']['value'] = [12.0, 16.0, 40.0, 80.0, 120.0, 160.0, 190.0, 400.0]   # lowest 0.6 x KD: occupancy 0.375 between 1/6 and 1/2, degree (0.5 - 0.375) / (1/3) = 0.375 (was 0.5, linear in x)
    assert _criterion(grade_fcs(r), 'concentration_series')['degree'] == pytest.approx(0.375)
    r['concentration_series']['value'] = [20.0, 30.0, 40.0, 80.0, 120.0, 160.0, 190.0, 400.0]   # lowest 1 x KD: the zero-agreement limit
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [4.0, 16.0, 40.0, 80.0, 120.0, 160.0, 190.0, 110.0]   # the largest value counts: 190 / 20 = 9.5 x KD, 90.5 percent bound, above 80: full degree
    assert _criterion(grade_fcs(r), 'concentration_series')['degree'] == pytest.approx(1.0)
    r['concentration_series']['value'] = [4.0, 8.0, 12.0, 16.0, 20.0, 25.0, 30.0, 40.0]        # highest 2 x KD: 66.7 percent bound on the saturation scale 80 / 20: degree (66.7 - 20) / 60
    assert _criterion(grade_fcs(r), 'concentration_series')['degree'] == pytest.approx((100.0 * 2 / 3 - 20.0) / 60.0)
    r['concentration_series']['value'] = [4.0, 8.0, 12.0, 16.0, 20.0, 30.0, 40.0]              # the same span with seven: the weaker of the count (sqrt(7 / 8) = 0.935) and the span (0.778)
    assert _criterion(grade_fcs(r), 'concentration_series')['degree'] == pytest.approx((100.0 * 2 / 3 - 20.0) / 60.0)
    r['concentration_series']['value'] = [1.0, 2.0, 3.0, 4.0, 4.5, 5.0, 2.5, 3.5]               # highest 0.25 x KD: 20 percent bound, the zero end of the saturation scale
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [0.004, 0.016, 0.04, 0.08, 0.12, 0.16, 0.19, 0.2]      # the same as the first, in uM
    r['concentration_series']['unit'] = 'uM'
    assert status(r, 'concentration_series') == 'supported' and _criterion(grade_fcs(r), 'concentration_series')['degree'] == pytest.approx(1.0)
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert reason(r, 'concentration_series') == 'concentration_series_recorded_for_the_sheet' and status(r, 'concentration_series') == 'unknown'    # 12 points counted, no list: the span is not known
    assert grade_fcs(r)['native']['concentration_low_over_constant'] is None
    r['quantities']['titration_point_count'] = point(7, 'count', 'n', ['s'])           # seven without a list: partial on the count, the span unknown, so unknown (not a failure)
    assert status(r, 'concentration_series') == 'unknown'
    r['quantities']['titration_point_count'] = point(3, 'count', 'n', ['s'])           # three without a list: the span is not known, so unknown (a short count is never conflicting)
    assert status(r, 'concentration_series') == 'unknown'
    r['quantities']['titration_point_count'] = point(8, 'count', 'n', ['s'])
    assert status(r, 'concentration_series') == 'unknown'
    missing(r, 'titration_point_count')
    assert (grader_status(r, 'concentration_series'), reason(r, 'concentration_series')) == ('unknown', 'kd_or_series_missing') and grade_fcs(r)['native']['concentration_count'] is None


def test_without_a_kd_the_span_cannot_be_judged():
    r = synthetic_record()
    missing(r, 'kd')
    graded = grade_fcs(r)
    assert graded['native']['constant_name'] is None and graded['native']['constant_nM'] is None
    assert _criterion(graded, 'concentration_series')['status'] == 'unknown' and graded['reasons']['labelled_over_kd'] == 'labelled_at_or_below_kd'    # the fact is yes
    assert graded['native']['concentration_count'] == 12 and graded['native']['concentration_low_over_constant'] is None      # the list is counted, its span cannot be recorded


def test_equilibrium():
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('not_applicable', 'not_applicable')):
        r['facts']['equilibrium_reached'] = fact(answer, ['s'])
        assert status(r, 'equilibrium') == expected
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert (grader_status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'incubation_recorded_for_the_sheet') and grade_fcs(r)['native']['incubation_min'] == 20.0
    # KD 20 nM: T_FAST 5 ln 2 / (2 * 1e8 * 2e-8) s = 0.866 s = 0.01444 min, T_SLOW (kon 1e5) = 866 s = 14.44 min; degree = min(t / 5, ln(t / T_FAST) / ln 1000)
    assert status(r, 'equilibrium') == 'supported' and 'degree' not in _criterion(grade_fcs(r), 'equilibrium')      # 20 min: beyond T_SLOW, full
    r['quantities']['incubation_time'] = point(1.0, 'min', 'i', ['s'])
    assert status(r, 'equilibrium') == 'supported' and _criterion(grade_fcs(r), 'equilibrium')['degree'] == pytest.approx(0.2) and grade_fcs(r)['native']['incubation_refs'] == ['s']
    assert _criterion(grade_fcs(r), 'equilibrium')['support_refs'] == ['s', 'span_exp_synthetic_fcs_1']      # the incubation and the KD it is judged against
    r['quantities']['incubation_time'] = point(300.0, 's', 'i', ['s'])      # 5 min: the floor is met, the association-rate share is ln(5 / 0.014438) / ln 1000 = 0.8465
    assert status(r, 'equilibrium') == 'supported' and _criterion(grade_fcs(r), 'equilibrium')['degree'] == pytest.approx(0.8465, abs=1e-3)
    r['quantities']['incubation_time'] = point(240.0, 's', 'i', ['s'])      # 4 min: floor 0.8, association share 0.8146
    assert _criterion(grade_fcs(r), 'equilibrium')['degree'] == pytest.approx(0.8)
    r['quantities']['incubation_time'] = point(0.5, 's', 'i', ['s'])      # below T_FAST (0.87 s): even the fastest association has not equilibrated
    assert status(r, 'equilibrium') == 'conflicting'
    r['quantities']['incubation_time'] = point(1.0, 'h', 'i', ['s'])      # 60 min, beyond T_SLOW: full
    assert status(r, 'equilibrium') == 'supported' and 'degree' not in _criterion(grade_fcs(r), 'equilibrium')
    missing(r, 'incubation_time')
    assert (grader_status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'fact_unknown')


def test_acquisition_is_the_time_times_the_repeats():
    r = synthetic_record()                                                                 # 30 s x 5 = 150 s
    assert grade_fcs(r)['native']['brightness_kHz'] == 12.0 and grade_fcs(r)['native']['free_diffusion_time_us'] == 60.0 and grade_fcs(r)['native']['acquisition_refs'] == ['span_exp_synthetic_fcs_1']
    missing(r, 'brightness')                                                               # the brightness and the diffusion time are given by the synthetic record; the sheet then needs
    missing(r, 'free_diffusion_time')                                                      # less than 60 s (see the converter tests), so they are removed to test the total against the 60 s reference
    assert (grader_status(r, 'acquisition'), reason(r, 'acquisition')) == ('unknown', 'acquisition_recorded_for_the_sheet') and status(r, 'acquisition') == 'supported'
    r['quantities']['measurement_repeat_count'] = point(2, 'count', 'r', ['s'])            # 60 s: exactly the researched minimum, full credit (no degree)
    assert status(r, 'acquisition') == 'supported' and grade_fcs(r)['native']['acquisition_total_s'] == 60.0 and 'degree' not in _criterion(grade_fcs(r), 'acquisition')
    r['quantities']['measurement_repeat_count'] = point(1, 'count', 'r', ['s'])            # 30 s: the curve is sqrt(30 / 60) as precise, partial credit (was a failure)
    judged = _criterion(grade_fcs(r), 'acquisition')
    assert judged['status'] == 'supported' and judged['degree'] == pytest.approx(sqrt(0.5)) and grade_fcs(r)['native']['measurement_repeats_given'] is True
    assert judged['support_refs'] == grade_fcs(r)['native']['acquisition_refs']
    r['quantities']['measurement_time'] = point(0.5, 'min', 't', ['s'])                    # 30 s again, in minutes
    assert _criterion(grade_fcs(r), 'acquisition')['degree'] == pytest.approx(sqrt(0.5))
    r['quantities']['measurement_time'] = point(1.0, 'min', 't', ['s'])                    # 60 s
    assert status(r, 'acquisition') == 'supported' and 'degree' not in _criterion(grade_fcs(r), 'acquisition')
    missing(r, 'measurement_repeat_count')
    r['quantities']['measurement_time'] = point(30.0, 's', 't', ['s'])                     # a short single measurement, repeats not given: unknown
    assert reason(r, 'acquisition') == 'acquisition_recorded_for_the_sheet' and grade_fcs(r)['native']['measurement_repeats_given'] is False and status(r, 'acquisition') == 'unknown'
    r['quantities']['measurement_time'] = point(120.0, 's', 't', ['s'])
    assert status(r, 'acquisition') == 'supported'
    missing(r, 'measurement_time')
    assert reason(r, 'acquisition') == 'measurement_time_not_given' and status(r, 'acquisition') == 'unknown'


def test_fit_model_is_stated_or_unknown():
    r = synthetic_record()
    assert reason(r, 'fit_model') == 'model_stated'
    for model in ('hill', 'quadratic', 'other'):
        r['fit_model'] = model
        assert status(r, 'fit_model') == 'supported'
    assert grade_fcs(r)['criteria']['fit_model']['support_refs'] == ['span_exp_synthetic_fcs_1']
    r['fit_model'] = None
    assert reason(r, 'fit_model') == 'fit_model_not_stated' and status(r, 'fit_model') == 'unknown'


def test_a_stated_fit_model_with_no_reported_kd_has_no_span_and_is_unknown_not_supported():
    r = synthetic_record()
    r['quantities']['kd'] = unavailable('nM', 'kd', 'not_given_in_the_inspected_source_text')      # no value and no span
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('unknown', 'model_stated_without_a_reported_kd')
    assert grade_fcs(r)['criteria']['fit_model']['support_refs'] == []


def test_no_criterion_returns_supported_or_conflicting_without_support_refs():
    for record in (synthetic_record(), sparse_record()):
        for graded in (grade_fcs(record),):
            assert all(c['support_refs'] for c in graded['criteria'].values() if c['status'] in ('supported', 'conflicting'))
    r = synthetic_record()
    r['facts']['independent_titrations'] = fact('no')
    r['quantities']['replicate_count'] = unavailable('count', 'replicate_count', 'not_given_in_the_inspected_source_text')      # a stated 'no' with no span at all: the grader refuses to return it
    with pytest.raises(ValueError):
        grade_fcs(r)


def test_replicates():
    r = synthetic_record()
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_recorded_for_the_sheet')
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])                    # two independent titrations: the precision of the mean sqrt(2 / 3), partial credit (was a failure)
    assert _criterion(grade_fcs(r), 'replicates') == {'status': 'supported', 'support_refs': ['s', 'span_exp_synthetic_fcs_1'], 'degree': pytest.approx(sqrt(2 / 3))}
    assert grade_fcs(r)['native']['replicate_count'] == 2 and grade_fcs(r)['native']['replicate_independent'] == 'yes'
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    assert _criterion(grade_fcs(r), 'replicates') == {'status': 'supported', 'support_refs': ['s', 'span_exp_synthetic_fcs_1']}      # the researched value: full credit, no degree
    r['facts']['independent_titrations'] = fact('no')
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('conflicting', 'replicates_not_independent')
    r['facts']['independent_titrations'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown'
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])                    # partial count, independence not stated: unknown, not opposition
    assert status(r, 'replicates') == 'unknown'
    r['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])                    # one titration, independence not stated: unknown (never conflicting for a count)
    assert status(r, 'replicates') == 'unknown'
    r['facts']['independent_titrations'] = fact('yes', ['s'])                               # one independent titration: sqrt(1 / 3), partial credit
    assert _criterion(grade_fcs(r), 'replicates')['degree'] == pytest.approx(sqrt(1 / 3))
    r['facts']['independent_titrations'] = fact('unknown')
    missing(r, 'replicate_count')
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_or_independence_unknown')
