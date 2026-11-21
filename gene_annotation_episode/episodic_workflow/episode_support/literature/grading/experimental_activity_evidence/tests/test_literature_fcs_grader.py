"""FCS grader: each criterion's rule on records, with the arithmetic worked by hand."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fcs_record import fact, point, unavailable
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_grader import CRITERIA, grade_fcs
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fcs_cases import sparse_record, synthetic_record

HANDED = {'diffusion_change', 'mass_consistency', 'saturation', 'labelled_range', 'labelled_over_kd', 'concentration_series', 'acquisition', 'replicates'}      # equilibrium is ruled by its fact in the synthetic record


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
    r['quantities']['mass_ratio'] = point(1.5, 'ratio', 'm', ['s'])                       # 1.5^(1/3) = 1.145: 1.8 / 1.145 = 1.57, a little outside 1.5: a degree just below 1
    assert reason(r, 'mass_consistency') == 'mass_consistency_recorded_for_the_sheet' and status(r, 'mass_consistency') == 'supported'
    assert _criterion(grade_fcs(r), 'mass_consistency')['degree'] == pytest.approx((3.0 - 1.8 / 1.5 ** (1 / 3)) / 1.5)
    r['quantities']['mass_ratio'] = point(27.0, 'ratio', 'm', ['s'])                      # 27^(1/3) = 3: 3 / 1.8 = 1.67, outside 1.5 the other way: degree (3 - 1.667) / 1.5
    assert status(r, 'mass_consistency') == 'supported' and _criterion(grade_fcs(r), 'mass_consistency')['degree'] == pytest.approx((3.0 - 3.0 / 1.8) / 1.5)
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
    for number, expected in ((0.1, 'supported'), (10.0, 'supported'), (0.09, 'conflicting'), (10.5, 'conflicting')):
        r['quantities']['particle_number'] = point(number, 'molecules', 'n', ['s'])
        assert status(r, 'labelled_range') == expected
        assert (grader_status(r, 'labelled_range'), reason(r, 'labelled_range')) == ('unknown', 'particle_number_recorded_for_the_sheet')
    assert grade_fcs(r)['native']['particle_number'] == 10.5 and grade_fcs(r)['native']['labelled_range_refs'] == ['s'] and _criterion(grade_fcs(r), 'labelled_range')['support_refs'] == ['s']
    missing(r, 'particle_number')                                                          # 2 nM
    assert reason(r, 'labelled_range') == 'labelled_concentration_recorded_for_the_sheet' and status(r, 'labelled_range') == 'supported'
    for value, unit, expected in ((0.3, 'nM', 'supported'), (30.0, 'nM', 'supported'), (0.29, 'nM', 'conflicting'), (31.0, 'nM', 'conflicting'), (100.0, 'pM', 'conflicting'), (0.03, 'uM', 'supported')):
        r['quantities']['labelled_concentration'] = point(value, unit, 'l', ['s'])
        assert status(r, 'labelled_range') == expected
    assert reason(r, 'labelled_range') == 'labelled_concentration_recorded_for_the_sheet' and grade_fcs(r)['native']['labelled_nM'] == pytest.approx(30.0)
    r['quantities']['labelled_concentration'] = point(100.0, 'pM', 'l', ['s'])
    assert status(r, 'labelled_range') == 'conflicting' and 'degree' not in _criterion(grade_fcs(r), 'labelled_range')         # an absolute range: no degree
    r['quantities']['particle_number'] = point(0.8, 'molecules', 'n', ['s'])               # the particle number decides when both are given
    assert status(r, 'labelled_range') == 'supported'
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
    assert status(r, 'labelled_over_kd') == 'supported' and _criterion(grade_fcs(r), 'labelled_over_kd')['degree'] == pytest.approx((10.0 - 5.0) / 9.0)      # 5 x KD without a tight-binding analysis
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
    r['concentration_series']['value'] = [4.0, 16.0, 40.0, 80.0, 120.0, 160.0, 200.0]          # seven: fewer than eight, no degree
    assert status(r, 'concentration_series') == 'conflicting' and 'degree' not in _criterion(grade_fcs(r), 'concentration_series')
    r['concentration_series']['value'] = [12.0, 16.0, 40.0, 80.0, 120.0, 160.0, 190.0, 400.0]   # lowest 0.6 x KD: halfway from 0.2 to 1.0, degree 0.5
    assert _criterion(grade_fcs(r), 'concentration_series')['degree'] == pytest.approx(0.5)
    r['concentration_series']['value'] = [20.0, 30.0, 40.0, 80.0, 120.0, 160.0, 190.0, 400.0]   # lowest 1 x KD: the zero-agreement limit
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [4.0, 16.0, 40.0, 80.0, 120.0, 160.0, 190.0, 110.0]   # the largest value counts: 190 / 20 = 9.5 x KD, degree 8.5 / 9
    assert _criterion(grade_fcs(r), 'concentration_series')['degree'] == pytest.approx((9.5 - 1.0) / 9.0)
    r['concentration_series']['value'] = [4.0, 16.0, 40.0, 80.0, 120.0, 20.0, 10.0, 15.0]      # highest 120 / 20 = 6 x KD: degree 5 / 9
    assert _criterion(grade_fcs(r), 'concentration_series')['degree'] == pytest.approx(5.0 / 9.0)
    r['concentration_series']['value'] = [4.0, 8.0, 12.0, 16.0, 17.0, 18.0, 19.0, 20.0]         # highest 1 x KD: the zero-agreement limit
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [0.004, 0.016, 0.04, 0.08, 0.12, 0.16, 0.19, 0.2]      # the same as the first, in uM
    r['concentration_series']['unit'] = 'uM'
    assert status(r, 'concentration_series') == 'supported' and _criterion(grade_fcs(r), 'concentration_series')['degree'] == pytest.approx(1.0)
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert reason(r, 'concentration_series') == 'concentration_series_recorded_for_the_sheet' and status(r, 'concentration_series') == 'unknown'    # 12 points counted, no list: the span is not known
    assert grade_fcs(r)['native']['concentration_low_over_constant'] is None
    r['quantities']['titration_point_count'] = point(7, 'count', 'n', ['s'])           # a count below the minimum fails without a list
    assert status(r, 'concentration_series') == 'conflicting' and _criterion(grade_fcs(r), 'concentration_series')['support_refs'] == ['span_exp_synthetic_fcs_1', 's']
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
    assert status(r, 'equilibrium') == 'unknown'                    # 20 min, but nothing says equilibrium
    r['quantities']['incubation_time'] = point(1.0, 'min', 'i', ['s'])
    assert status(r, 'equilibrium') == 'conflicting' and grade_fcs(r)['native']['incubation_refs'] == ['s'] and _criterion(grade_fcs(r), 'equilibrium')['support_refs'] == ['s']
    r['quantities']['incubation_time'] = point(300.0, 's', 'i', ['s'])      # 5 min exactly: allowed, so unknown
    assert status(r, 'equilibrium') == 'unknown'
    r['quantities']['incubation_time'] = point(240.0, 's', 'i', ['s'])      # 4 min
    assert status(r, 'equilibrium') == 'conflicting'
    r['quantities']['incubation_time'] = point(1.0, 'h', 'i', ['s'])
    assert status(r, 'equilibrium') == 'unknown'
    missing(r, 'incubation_time')
    assert (grader_status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'fact_unknown')


def test_acquisition_is_the_time_times_the_repeats():
    r = synthetic_record()                                                                 # 30 s x 5 = 150 s
    assert (grader_status(r, 'acquisition'), reason(r, 'acquisition')) == ('unknown', 'acquisition_recorded_for_the_sheet') and status(r, 'acquisition') == 'supported'
    r['quantities']['measurement_repeat_count'] = point(2, 'count', 'r', ['s'])            # 60 s: exactly the minimum, allowed
    assert status(r, 'acquisition') == 'supported' and grade_fcs(r)['native']['acquisition_total_s'] == 60.0
    r['quantities']['measurement_repeat_count'] = point(1, 'count', 'r', ['s'])            # 30 s
    assert status(r, 'acquisition') == 'conflicting' and grade_fcs(r)['native']['measurement_repeats_given'] is True and _criterion(grade_fcs(r), 'acquisition')['support_refs'] == grade_fcs(r)['native']['acquisition_refs']
    r['quantities']['measurement_time'] = point(0.5, 'min', 't', ['s'])                    # 30 s again, in minutes
    assert status(r, 'acquisition') == 'conflicting'
    r['quantities']['measurement_time'] = point(1.0, 'min', 't', ['s'])                    # 60 s
    assert status(r, 'acquisition') == 'supported'
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
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'conflicting' and grade_fcs(r)['native']['replicate_count'] == 2 and grade_fcs(r)['native']['replicate_independent'] == 'yes'
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported' and _criterion(grade_fcs(r), 'replicates')['support_refs'] == ['s', 'span_exp_synthetic_fcs_1']
    r['facts']['independent_titrations'] = fact('no')
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('conflicting', 'replicates_not_independent')
    r['facts']['independent_titrations'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown'
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])                    # a low count fails whatever the independence says
    assert status(r, 'replicates') == 'conflicting'
    missing(r, 'replicate_count')
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_or_independence_unknown')
