"""FP grader: each criterion's rule on records, with the arithmetic worked by hand."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fp_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_grader import CRITERIA, grade_fp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fp_cases import sparse_record, synthetic_record


def status(record, criterion):
    """The status after the sheet's judgement where the grader handed the recorded facts over, else the grader's own (threshold-boundary cases are judged on the sheet side)."""
    return _criterion(grade_fp(record), criterion)['status']


def reason(record, criterion):
    return grade_fp(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere():
    graded = grade_fp(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 11
    handed_over = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed_over == {'assay_window', 'tracer_concentration', 'concentration_series', 'replicates', 'direct_vs_competition'}      # equilibrium and intensity_change are decided by their stated facts
    assert all(graded['criteria'][name] == {'status': 'unknown', 'support_refs': []} for name in handed_over)                      # the grader holds no threshold
    judged = {name: _criterion(graded, name) for name in CRITERIA}
    assert {c['status'] for c in judged.values()} == {'supported'}
    assert all(c['support_refs'] for c in judged.values())
    native = graded['native']
    assert native['kd_nM'] == 20.0 and native['ki_nM'] == 40.0 and native['constant_name'] == 'kd' and graded['experiment_type'] == 'fp'
    assert native['tracer_over_kd'] == pytest.approx(0.25) and native['window_mP'] == 200.0
    assert native['concentration_count'] == 10 and native['concentration_low_over_constant'] == pytest.approx(0.1) and native['concentration_high_over_constant'] == pytest.approx(100.0)
    assert native['incubation_min'] == 30.0 and native['plate_type'] == 'black_non_binding'


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_fp(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['criteria']['assay_window']['status'] == 'unknown' and graded['native']['kd_nM'] == 20.0


def test_assay_window_in_mp_and_in_anisotropy():
    r = synthetic_record()
    r['quantities']['signal_maximum'] = point(120.0, 'mP', 's', ['s'])        # window 70: recorded, the grader does not judge it
    graded = grade_fp(r)
    assert graded['native']['window_mP'] == 70.0 and graded['native']['window_refs'] == ['span_exp_synthetic_fp_1', 's']
    assert graded['criteria']['assay_window'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['assay_window'] == 'window_recorded_for_the_sheet'
    assert status(r, 'assay_window') == 'supported'
    r['quantities']['signal_maximum'] = point(50.0, 'mP', 's', ['s'])        # a window of 0: recorded, the sheet judges it conflicting
    assert grade_fp(r)['native']['window_mP'] == 0.0 and status(r, 'assay_window') == 'conflicting'
    # anisotropy: r 0.05 -> P = 3 x 0.05 / 2.05 = 0.07317 = 73.17 mP; r 0.2 -> P = 0.6 / 2.2 = 272.73 mP; window 199.56 mP
    r['quantities']['signal_minimum'] = point(0.05, 'r', 'a', ['s'])
    r['quantities']['signal_maximum'] = point(0.2, 'r', 'b', ['s'])
    assert status(r, 'assay_window') == 'supported' and grade_fp(r)['native']['window_mP'] == pytest.approx(272.7272727 - 73.1707317)
    # r 0.05 to r 0.08: P 73.17 to 3 x 0.08 / 2.08 = 115.38 mP, a window of 42.2 mP
    r['quantities']['signal_maximum'] = point(0.08, 'r', 'b', ['s'])
    assert grade_fp(r)['native']['window_mP'] == pytest.approx(115.3846154 - 73.1707317)
    missing(r, 'signal_maximum')
    assert status(r, 'assay_window') == 'unknown' and reason(r, 'assay_window') == 'minimum_or_maximum_missing'


@pytest.mark.parametrize('criterion, fact_name', [('free_probe_baseline', 'free_probe_baseline_measured'), ('surface_adsorption', 'surface_adsorption_prevented')])
def test_single_fact_criteria_are_the_one_fact(criterion, fact_name):
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('unknown', 'unknown'), ('not_applicable', 'not_applicable')):
        r['facts'][fact_name] = fact(answer, ['s'])
        assert status(r, criterion) == expected


def test_tracer_concentration_by_ratio_and_by_fact():
    r = synthetic_record()
    r['quantities']['tracer_concentration'] = point(20.0, 'nM', 't', ['s'])         # 1.0 x KD: exactly the limit, allowed
    graded = grade_fp(r)
    assert graded['native']['tracer_over_kd'] == pytest.approx(1.0) and graded['native']['tight_binding_handled'] is True and graded['native']['tracer_refs']
    assert graded['criteria']['tracer_concentration'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['tracer_concentration'] == 'tracer_over_kd_recorded_for_the_sheet'
    assert status(r, 'tracer_concentration') == 'supported'
    r['quantities']['tracer_concentration'] = point(0.1, 'uM', 't', ['s'])          # 100 nM = 5 x KD
    assert grade_fp(r)['native']['tracer_over_kd'] == pytest.approx(5.0) and status(r, 'tracer_concentration') == 'supported'      # tight binding considered: yes
    r['facts']['tight_binding_considered'] = fact('unknown')
    assert grade_fp(r)['native']['tight_binding_handled'] is False
    r['fit_model'] = 'quadratic'
    assert grade_fp(r)['native']['tight_binding_handled'] is True
    r['fit_model'] = '1:1'
    # no ratio (tracer missing): the fact decides
    missing(r, 'tracer_concentration')
    r['facts']['tracer_at_or_below_kd'] = fact('yes', ['s'])
    assert reason(r, 'tracer_concentration') == 'tracer_at_or_below_kd'
    r['facts']['tracer_at_or_below_kd'] = fact('no', ['s'])
    assert reason(r, 'tracer_concentration') == 'tracer_above_kd_without_tight_binding_analysis'
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])
    assert status(r, 'tracer_concentration') == 'supported'
    r['facts']['tracer_at_or_below_kd'] = fact('unknown')
    assert reason(r, 'tracer_concentration') == 'tracer_or_kd_missing'
    # a Ki is not the tracer's KD: with only a Ki the ratio cannot be formed
    r = synthetic_record()
    missing(r, 'kd')
    r['facts']['tracer_at_or_below_kd'] = fact('unknown')
    assert reason(r, 'tracer_concentration') == 'tracer_or_kd_missing'


def test_concentration_series():
    r = synthetic_record()
    r['concentration_series']['value'] = [2.0, 6.0, 20.0, 60.0, 200.0, 400.0, 800.0]     # seven: recorded, the sheet judges the count
    graded = grade_fp(r)
    assert graded['native']['concentration_count'] == 7 and graded['reasons']['concentration_series'] == 'series_recorded_for_the_sheet' and graded['criteria']['concentration_series']['status'] == 'unknown'
    assert graded['native']['series_refs'] == ['span_exp_synthetic_fp_1']
    judged = _criterion(graded, 'concentration_series')
    assert judged['status'] == 'supported' and judged['degree'] == pytest.approx(0.8)      # (7 - 3) / (8 - 3); the ends 0.1 x and 40 x KD are full
    r['concentration_series']['value'] = [30.0, 40.0, 60.0, 100.0, 200.0, 300.0, 400.0, 500.0]   # lowest 1.5 x KD
    assert grade_fp(r)['native']['concentration_low_over_constant'] == pytest.approx(1.5) and status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 190.0]         # highest 9.5 x KD
    assert grade_fp(r)['native']['concentration_high_over_constant'] == pytest.approx(9.5)
    r['concentration_series']['value'] = [4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 200.0, 400.0]       # lowest 0.2 x KD and highest 20 x KD
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = [0.004, 0.008, 0.016, 0.032, 0.064, 0.128, 0.2, 0.4]    # the same in uM
    r['concentration_series']['unit'] = 'uM'
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = [0.4, 4.0, 40.0, 100.0, 200.0, 2000.0, 3000.0, 4000.0]  # in pM: the lowest is 0.02 x KD ... all pM
    r['concentration_series']['unit'] = 'pM'
    assert grade_fp(r)['native']['concentration_high_over_constant'] == pytest.approx(0.2) and status(r, 'concentration_series') == 'conflicting'      # highest 4 nM = 0.2 x KD
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert status(r, 'concentration_series') == 'unknown'


def test_the_series_is_judged_against_the_ki_when_there_is_no_kd():
    r = synthetic_record()
    missing(r, 'kd')       # Ki 40 nM is the constant: 2 nM is 0.05 x Ki, 2000 nM is 50 x Ki
    graded = grade_fp(r)
    assert graded['native']['constant_name'] == 'ki' and graded['native']['constant_nM'] == 40.0
    assert _criterion(graded, 'concentration_series')['status'] == 'supported'
    assert graded['native']['concentration_high_over_constant'] == pytest.approx(50.0)


def test_equilibrium():
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('not_applicable', 'not_applicable')):
        r['facts']['equilibrium_reached'] = fact(answer, ['s'])
        assert status(r, 'equilibrium') == expected
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert status(r, 'equilibrium') == 'supported'                  # 30 min, KD 20 nM: past T_SLOW (28.9 min), full degree; the fact is not stated, the sheet judges the time
    r['quantities']['incubation_time'] = point(4.0, 'min', 'i', ['s'])
    graded = grade_fp(r)
    assert graded['reasons']['equilibrium'] == 'incubation_recorded_for_the_sheet' and graded['native']['incubation_min'] == 4.0 and graded['native']['incubation_refs'] == ['s']
    assert graded['criteria']['equilibrium'] == {'status': 'unknown', 'support_refs': []}
    judged = _criterion(graded, 'equilibrium')
    assert judged['status'] == 'supported' and judged['degree'] == pytest.approx(0.571, abs=2e-3) and judged['support_refs'][0] == 's'      # log(4 / 0.2888) / ln 100
    r['quantities']['incubation_time'] = point(0.2, 'min', 'i', ['s'])      # below T_FAST 0.2888 min: not even the fastest binder has equilibrated
    assert status(r, 'equilibrium') == 'conflicting'
    r['quantities']['incubation_time'] = point(2.0, 'h', 'i', ['s'])
    assert status(r, 'equilibrium') == 'supported'


def test_intensity_change():
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('not_applicable', 'not_applicable')):
        r['facts']['intensity_change_checked'] = fact(answer, ['s'])
        assert status(r, 'intensity_change') == expected
    r['facts']['intensity_change_checked'] = fact('unknown')
    graded = grade_fp(r)                                                                      # 10 percent: recorded, the sheet judges it
    assert graded['reasons']['intensity_change'] == 'intensity_change_recorded_for_the_sheet' and graded['native']['intensity_change_percent'] == 10.0 and graded['criteria']['intensity_change']['status'] == 'unknown'
    assert status(r, 'intensity_change') == 'supported'
    r['quantities']['total_intensity_change'] = point(30.0, 'percent', 'c', ['s'])           # exactly the limit
    assert status(r, 'intensity_change') == 'supported'
    r['quantities']['total_intensity_change'] = point(120.0, 'percent', 'c', ['s'])
    assert status(r, 'intensity_change') == 'conflicting'
    missing(r, 'total_intensity_change')
    assert status(r, 'intensity_change') == 'unknown'


def test_specificity_control_either_is_enough():
    r = synthetic_record()
    r['facts']['unlabelled_competitor_displaces'] = fact('unknown')
    assert status(r, 'specificity_control') == 'supported'
    r['facts']['nonspecific_binding_checked'] = fact('no')
    assert status(r, 'specificity_control') == 'conflicting' and reason(r, 'specificity_control') == 'fact_answered_no'
    r['facts']['unlabelled_competitor_displaces'] = fact('yes', ['s'])
    assert status(r, 'specificity_control') == 'supported'
    r['facts']['unlabelled_competitor_displaces'] = fact('unknown')
    r['facts']['nonspecific_binding_checked'] = fact('unknown')
    assert status(r, 'specificity_control') == 'unknown'
    for name in ('nonspecific_binding_checked', 'unlabelled_competitor_displaces'):
        r['facts'][name] = fact('not_applicable')
    assert status(r, 'specificity_control') == 'not_applicable'


def test_fit_model_and_format():
    r = synthetic_record()
    assert reason(r, 'fit_model') == 'model_stated'
    r['fit_model'] = 'competitive_binding'
    assert reason(r, 'fit_model') == 'competition_model_for_direct_titration'
    r['assay_format'] = 'competition'
    assert status(r, 'fit_model') == 'supported'
    for model in ('1:1', 'hill'):
        r['fit_model'] = model
        assert reason(r, 'fit_model') == 'direct_model_for_competition'
    r['fit_model'] = 'quadratic'
    assert status(r, 'fit_model') == 'supported'
    r['assay_format'] = None
    r['fit_model'] = 'competitive_binding'
    assert status(r, 'fit_model') == 'supported'          # format not stated: nothing to clash with
    r['fit_model'] = None
    assert reason(r, 'fit_model') == 'fit_model_not_stated'


def test_replicates():
    r = synthetic_record()
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    graded = grade_fp(r)                                                                      # the count and the independence are recorded, the sheet judges them
    assert graded['reasons']['replicates'] == 'replicate_count_recorded_for_the_sheet' and graded['criteria']['replicates']['status'] == 'unknown'
    assert graded['native']['replicate_count'] == 2 and graded['native']['replicate_independent'] == 'yes' and graded['native']['replicate_refs']
    assert _criterion(graded, 'replicates')['status'] == 'supported' and _criterion(graded, 'replicates')['degree'] == pytest.approx(math.sqrt(2 / 3))      # two titrations: partial credit, never conflicting
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported'
    r['facts']['independent_titrations'] = fact('no', ['s'])                                 # a stated 'no' is a fact the grader judges
    assert grade_fp(r)['criteria']['replicates']['status'] == 'conflicting' and reason(r, 'replicates') == 'replicates_not_independent'
    r['facts']['independent_titrations'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown' and grade_fp(r)['native']['replicate_independent'] == 'unknown'
    missing(r, 'replicate_count')
    assert reason(r, 'replicates') == 'replicate_count_or_independence_unknown'


def test_direct_vs_competition():
    r = synthetic_record()                                            # 20 nM against 40 nM: ratio 2
    graded = grade_fp(r)
    assert graded['native']['estimate_fold'] == pytest.approx(2.0) and graded['reasons']['direct_vs_competition'] == 'estimates_recorded_for_the_sheet' and graded['criteria']['direct_vs_competition']['status'] == 'unknown'
    assert status(r, 'direct_vs_competition') == 'supported'
    r['quantities']['ki'] = point(60.0, 'nM', 'k', ['s'])             # ratio exactly 3: recorded
    assert grade_fp(r)['native']['estimate_fold'] == pytest.approx(3.0) and status(r, 'direct_vs_competition') == 'supported'
    r['quantities']['ki'] = point(0.0061, 'uM', 'k', ['s'])           # 6.1 nM: 20 / 6.1 = 3.28
    assert grade_fp(r)['native']['estimate_fold'] == pytest.approx(3.2787, abs=1e-3) and grade_fp(r)['native']['estimate_refs']
    assert status(r, 'direct_vs_competition') == 'supported'          # the fold gap is between 3 and 10: supported with a degree (see the converter test)
    missing(r, 'ki')
    assert reason(r, 'direct_vs_competition') == 'kd_or_ki_missing'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    assert status(r, 'direct_vs_competition') == 'not_applicable'


def test_the_noise_of_the_reads_is_recorded_with_the_window_and_judged_nowhere_in_the_grader():
    r = synthetic_record()
    assert grade_fp(r)['native']['window_noise_mP'] is None and grade_fp(r)['native']['window_noise_refs'] == []      # not stated: nothing recorded
    r['quantities']['signal_noise'] = point(10.0, 'mP', 'n', ['n'])
    graded = grade_fp(r)
    assert graded['native']['window_noise_mP'] == 10.0 and graded['native']['window_noise_refs'] == ['n'] and graded['native']['window_mP'] == 200.0
    assert graded['criteria']['assay_window'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['assay_window'] == 'window_recorded_for_the_sheet'
    missing(r, 'signal_maximum')                                                             # no window: the noise alone is not recorded as a window
    graded = grade_fp(r)
    assert graded['native']['window_noise_refs'] == [] and reason(r, 'assay_window') == 'minimum_or_maximum_missing'


def test_the_direction_of_the_intensity_change_is_recorded_as_stated_and_never_decides_in_the_grader():
    r = synthetic_record()
    r['facts']['intensity_change_checked'] = fact('unknown')
    assert grade_fp(r)['native']['intensity_change_direction'] is None                        # not stated
    for direction in ('increase', 'decrease'):
        r['intensity_change_direction'] = direction
        graded = grade_fp(r)
        assert graded['native']['intensity_change_direction'] == direction and graded['native']['intensity_change_percent'] == 10.0
        assert graded['criteria']['intensity_change'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['intensity_change'] == 'intensity_change_recorded_for_the_sheet'


def test_a_series_stated_as_competitor_is_read_against_the_ic50_else_against_the_constant():
    r = synthetic_record()                                                                    # KD 20 nM, series 2 to 2000 nM
    native = grade_fp(r)['native']
    assert native['series_kind'] is None and native['ic50_nM'] is None and native['series_reference'] == 'kd'
    r['quantities']['ic50'] = point(200.0, 'nM', 'i', ['i'])
    r['series_kind'] = 'titrant'                                                              # a titrant series stays on the constant even with an IC50 given
    native = grade_fp(r)['native']
    assert native['series_reference'] == 'kd' and native['concentration_high_over_constant'] == pytest.approx(100.0) and 'i' not in native['series_refs']
    r['series_kind'] = 'competitor'                                                           # 2 nM is 0.01 x IC50, 2000 nM is 10 x IC50
    graded = grade_fp(r)
    native = graded['native']
    assert native['series_kind'] == 'competitor' and native['ic50_nM'] == 200.0 and native['series_reference'] == 'ic50'
    assert native['concentration_low_over_constant'] == pytest.approx(0.01) and native['concentration_high_over_constant'] == pytest.approx(10.0) and native['series_refs'][-1] == 'i'
    assert graded['criteria']['concentration_series'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['concentration_series'] == 'series_recorded_for_the_sheet'
    missing(r, 'ic50')                                                                        # competitor without an IC50: the constant, as before
    native = grade_fp(r)['native']
    assert native['series_reference'] == 'kd' and native['concentration_high_over_constant'] == pytest.approx(100.0)
    missing(r, 'kd')                                                                          # no IC50, no KD: the Ki is the constant
    assert grade_fp(r)['native']['series_reference'] == 'ki'
