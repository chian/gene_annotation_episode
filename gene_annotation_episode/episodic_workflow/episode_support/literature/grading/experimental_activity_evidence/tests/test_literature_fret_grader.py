"""FRET grader: each criterion's rule on records, with the arithmetic worked by hand."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fret_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_grader import CRITERIA, grade_fret
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.fret_cases import sparse_record, synthetic_record


def status(record, criterion):
    """The status after the sheet's judgement where the grader handed the recorded facts over, else the grader's own (threshold-boundary cases are judged on the sheet side)."""
    return _criterion(grade_fret(record), criterion)['status']


def reason(record, criterion):
    return grade_fret(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere():
    graded = grade_fret(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 13
    handed_over = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed_over == {'assay_window', 'time_gating', 'labelled_concentration', 'concentration_series', 'replicates', 'direct_vs_competition'}      # equilibrium is decided by its stated fact
    assert all(graded['criteria'][name] == {'status': 'unknown', 'support_refs': []} for name in handed_over)                      # the grader holds no threshold
    judged = {name: _criterion(graded, name) for name in CRITERIA}
    assert {c['status'] for c in judged.values()} == {'supported'}
    assert all(c['support_refs'] for c in judged.values())
    native = graded['native']
    assert native['kd_nM'] == 20.0 and native['ki_nM'] == 40.0 and native['constant_name'] == 'kd' and graded['experiment_type'] == 'fret'
    assert native['labelled_over_kd'] == pytest.approx(0.25) and native['labelled_nM'] == 5.0 and native['ratio_fold'] == pytest.approx(4.0)
    assert native['concentration_count'] == 10 and native['concentration_low_over_constant'] == pytest.approx(0.1) and native['concentration_high_over_constant'] == pytest.approx(100.0)
    assert native['incubation_min'] == 60.0 and native['plate_type'] == 'white' and native['delay_us'] == 100.0 and native['integration_us'] == 400.0


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_fret(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['criteria']['assay_window']['status'] == 'unknown' and graded['native']['kd_nM'] == 20.0


def test_assay_window_is_the_fold_of_the_emission_ratio():
    r = synthetic_record()
    r['quantities']['ratio_maximum'] = point(0.8, 'ratio', 's', ['s'])        # 0.8 / 0.4 = 2.0: recorded, the grader does not judge it
    graded = grade_fret(r)
    assert graded['native']['ratio_fold'] == pytest.approx(2.0) and graded['native']['window_refs'] == ['span_exp_synthetic_fret_1', 's']
    assert graded['criteria']['assay_window'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['assay_window'] == 'window_recorded_for_the_sheet'
    assert status(r, 'assay_window') == 'supported'
    r['quantities']['ratio_maximum'] = point(0.4, 'ratio', 's', ['s'])        # a fold of 1: no window, the sheet judges it conflicting
    assert grade_fret(r)['native']['ratio_fold'] == pytest.approx(1.0) and status(r, 'assay_window') == 'conflicting'
    # a ratio on a scaled axis (x 10 000) has the same fold: 6000 / 2000 = 3
    r['quantities']['ratio_minimum'] = point(2000.0, 'ratio', 'a', ['s'])
    r['quantities']['ratio_maximum'] = point(6000.0, 'ratio', 'b', ['s'])
    assert status(r, 'assay_window') == 'supported' and grade_fret(r)['native']['ratio_fold'] == pytest.approx(3.0)
    missing(r, 'ratio_maximum')
    assert status(r, 'assay_window') == 'unknown' and reason(r, 'assay_window') == 'minimum_or_maximum_missing'


@pytest.mark.parametrize('criterion, fact_name', [('ratiometric_readout', 'ratiometric_readout_used'), ('compound_interference', 'compound_interference_checked')])
def test_single_fact_criteria_are_the_one_fact(criterion, fact_name):
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('unknown', 'unknown'), ('not_applicable', 'not_applicable')):
        r['facts'][fact_name] = fact(answer, ['s'])
        assert status(r, criterion) == expected


def test_spectral_crosstalk_a_stated_correction_or_both_controls():
    r = synthetic_record()
    assert reason(r, 'spectral_crosstalk') == 'crosstalk_corrected'
    r['facts']['crosstalk_corrected'] = fact('unknown')
    assert reason(r, 'spectral_crosstalk') == 'facts_answered_yes'                 # both controls stated as done
    r['facts']['acceptor_only_control_measured'] = fact('unknown')
    assert status(r, 'spectral_crosstalk') == 'unknown'
    r['facts']['donor_only_control_measured'] = fact('no', ['s'])
    assert status(r, 'spectral_crosstalk') == 'conflicting'
    r['facts']['crosstalk_corrected'] = fact('yes', ['s'])                         # a stated correction is enough
    assert reason(r, 'spectral_crosstalk') == 'crosstalk_corrected'
    r['facts']['crosstalk_corrected'] = fact('no', ['s'])                          # stated as not corrected fails whatever the controls
    r['facts']['donor_only_control_measured'] = fact('yes', ['s'])
    r['facts']['acceptor_only_control_measured'] = fact('yes', ['s'])
    assert status(r, 'spectral_crosstalk') == 'conflicting'
    for name in ('crosstalk_corrected', 'donor_only_control_measured', 'acceptor_only_control_measured'):
        r['facts'][name] = fact('not_applicable')
    assert status(r, 'spectral_crosstalk') == 'not_applicable'
    r['facts']['crosstalk_corrected'] = fact('unknown')                            # the controls do not apply but the correction is not stated
    assert status(r, 'spectral_crosstalk') == 'unknown'


def test_time_gating():
    r = synthetic_record()
    graded = grade_fret(r)
    assert graded['reasons']['time_gating'] == 'gating_recorded_for_the_sheet' and graded['criteria']['time_gating'] == {'status': 'unknown', 'support_refs': []}
    assert graded['native']['delay_us'] == 100.0 and graded['native']['integration_us'] == 400.0 and graded['native']['gating_refs']
    r['quantities']['delay_time'] = point(50.0, 'us', 'd', ['s'])                   # recorded; the sheet judges it
    assert status(r, 'time_gating') == 'supported'
    r['quantities']['delay_time'] = point(0.049, 'ms', 'd', ['s'])                  # 49 us
    assert grade_fret(r)['native']['delay_us'] == pytest.approx(49.0)
    r['quantities']['delay_time'] = point(0.1, 'ms', 'd', ['s'])                    # 100 us
    r['quantities']['integration_time'] = point(0.1, 'ms', 'w', ['s'])              # 100 us
    assert grade_fret(r)['native']['integration_us'] == pytest.approx(100.0) and status(r, 'time_gating') == 'supported'
    r['quantities']['integration_time'] = point(5.0, 'us', 'w', ['s'])
    assert status(r, 'time_gating') == 'conflicting'
    missing(r, 'integration_time')
    assert status(r, 'time_gating') == 'supported'                                  # no window given: the delay decides
    missing(r, 'delay_time')
    assert reason(r, 'time_gating') == 'delay_not_stated'
    r['facts']['time_resolved_read'] = fact('unknown')
    assert reason(r, 'time_gating') == 'time_resolved_read_not_stated'
    r['facts']['time_resolved_read'] = fact('no', ['s'])
    assert reason(r, 'time_gating') == 'not_time_resolved'
    r['facts']['time_resolved_read'] = fact('not_applicable')
    assert reason(r, 'time_gating') == 'fact_not_applicable'


def test_time_gating_needs_a_long_lived_donor():
    r = synthetic_record()
    for pair in ('fluorescent_protein_pair', 'organic_dye_pair'):
        r['donor_acceptor_pair'] = pair
        assert reason(r, 'time_gating') == 'time_gating_with_short_lived_donor'
    r['donor_acceptor_pair'] = 'other'
    assert status(r, 'time_gating') == 'supported'
    # a steady-state read with a fluorescent-protein pair is not gated at all
    r['donor_acceptor_pair'] = 'fluorescent_protein_pair'
    r['facts']['time_resolved_read'] = fact('no', ['s'])
    assert status(r, 'time_gating') == 'not_applicable'
    # not stated as time-resolved but a delay is given: it is read as gated, and a delay of a short-lived pair is a contradiction
    r['facts']['time_resolved_read'] = fact('unknown')
    assert reason(r, 'time_gating') == 'time_gating_with_short_lived_donor'


def test_labelled_concentration_by_ratio_and_by_fact():
    r = synthetic_record()                                                           # donor 5 nM, acceptor 30 nM: the smaller, 5 nM, is the limiting one
    r['quantities']['donor_concentration'] = point(20.0, 'nM', 't', ['s'])           # limiting is then the donor 20 nM = 1.0 x KD: exactly the limit, allowed
    graded = grade_fret(r)
    assert graded['native']['labelled_over_kd'] == pytest.approx(1.0) and graded['native']['tight_binding_handled'] is True and graded['native']['labelled_refs']
    assert graded['criteria']['labelled_concentration'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['labelled_concentration'] == 'labelled_over_kd_recorded_for_the_sheet'
    assert status(r, 'labelled_concentration') == 'supported'
    r['quantities']['donor_concentration'] = point(0.1, 'uM', 't', ['s'])            # 100 nM
    r['quantities']['acceptor_concentration'] = point(0.2, 'uM', 't', ['s'])         # 200 nM: the limiting is 100 nM = 5 x KD
    assert grade_fret(r)['native']['labelled_over_kd'] == pytest.approx(5.0) and status(r, 'labelled_concentration') == 'supported'      # tight binding considered: yes
    r['facts']['tight_binding_considered'] = fact('unknown')
    assert grade_fret(r)['native']['tight_binding_handled'] is False
    r['fit_model'] = 'quadratic'
    assert grade_fret(r)['native']['tight_binding_handled'] is True
    r['fit_model'] = '1:1'
    # no ratio (both labelled concentrations missing): the fact decides
    missing(r, 'donor_concentration')
    missing(r, 'acceptor_concentration')
    r['facts']['labelled_partner_at_or_below_kd'] = fact('yes', ['s'])
    assert reason(r, 'labelled_concentration') == 'labelled_at_or_below_kd'
    r['facts']['labelled_partner_at_or_below_kd'] = fact('no', ['s'])
    assert reason(r, 'labelled_concentration') == 'labelled_above_kd_without_tight_binding_analysis'
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])
    assert status(r, 'labelled_concentration') == 'supported'
    r['facts']['labelled_partner_at_or_below_kd'] = fact('unknown')
    assert reason(r, 'labelled_concentration') == 'labelled_or_kd_missing'
    # a Ki is not the labelled partner's KD: with only a Ki the ratio cannot be formed
    r = synthetic_record()
    missing(r, 'kd')
    r['facts']['labelled_partner_at_or_below_kd'] = fact('unknown')
    assert reason(r, 'labelled_concentration') == 'labelled_or_kd_missing'


def test_a_single_labelled_concentration_is_the_limiting_one():
    r = synthetic_record()
    missing(r, 'donor_concentration')                   # only the acceptor 30 nM is given: 1.5 x KD, above the full-agreement limit (the sheet gives a degree)
    r['facts']['tight_binding_considered'] = fact('no', ['s'])
    graded = grade_fret(r)
    assert graded['native']['labelled_over_kd'] == pytest.approx(1.5) and graded['native']['tight_binding_handled'] is False
    verdict = _criterion(graded, 'labelled_concentration')
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx((1.5 - 10.0) / (1.0 - 10.0))


def test_concentration_series():
    r = synthetic_record()
    r['concentration_series']['value'] = [2.0, 6.0, 20.0, 60.0, 200.0, 400.0, 800.0]     # seven: recorded, the sheet judges the count
    graded = grade_fret(r)
    assert graded['native']['concentration_count'] == 7 and graded['reasons']['concentration_series'] == 'series_recorded_for_the_sheet' and graded['criteria']['concentration_series']['status'] == 'unknown'
    assert graded['native']['series_refs'] == ['span_exp_synthetic_fret_1']
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [30.0, 40.0, 60.0, 100.0, 200.0, 300.0, 400.0, 500.0]   # lowest 1.5 x KD
    assert grade_fret(r)['native']['concentration_low_over_constant'] == pytest.approx(1.5) and status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 190.0]         # highest 9.5 x KD
    assert grade_fret(r)['native']['concentration_high_over_constant'] == pytest.approx(9.5)
    r['concentration_series']['value'] = [4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 200.0, 400.0]       # lowest 0.2 x KD and highest 20 x KD
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = [0.004, 0.008, 0.016, 0.032, 0.064, 0.128, 0.2, 0.4]    # the same in uM
    r['concentration_series']['unit'] = 'uM'
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = [0.4, 4.0, 40.0, 100.0, 200.0, 2000.0, 3000.0, 4000.0]  # all pM: the highest 4 nM = 0.2 x KD
    r['concentration_series']['unit'] = 'pM'
    assert grade_fret(r)['native']['concentration_high_over_constant'] == pytest.approx(0.2) and status(r, 'concentration_series') == 'conflicting'
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert status(r, 'concentration_series') == 'unknown'


def test_the_series_is_judged_against_the_ki_then_the_ec50_then_the_ic50_when_there_is_no_kd():
    r = synthetic_record()
    missing(r, 'kd')       # Ki 40 nM is the constant: 2 nM is 0.05 x Ki, 2000 nM is 50 x Ki
    graded = grade_fret(r)
    assert graded['native']['constant_name'] == 'ki' and graded['native']['constant_nM'] == 40.0
    assert _criterion(graded, 'concentration_series')['status'] == 'supported'
    assert graded['native']['concentration_high_over_constant'] == pytest.approx(50.0)
    missing(r, 'ki')       # EC50 30 nM
    assert grade_fret(r)['native']['constant_name'] == 'ec50' and grade_fret(r)['native']['constant_nM'] == 30.0
    missing(r, 'ec50')     # IC50 80 nM: 2000 / 80 = 25
    graded = grade_fret(r)
    assert graded['native']['constant_name'] == 'ic50' and graded['native']['concentration_high_over_constant'] == pytest.approx(25.0)
    missing(r, 'ic50')
    assert grade_fret(r)['native']['constant_name'] is None and status(r, 'concentration_series') == 'unknown'


def test_equilibrium():
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('not_applicable', 'not_applicable')):
        r['facts']['equilibrium_reached'] = fact(answer, ['s'])
        assert status(r, 'equilibrium') == expected
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert status(r, 'equilibrium') == 'unknown'                    # 60 min, but nothing says equilibrium
    r['quantities']['incubation_time'] = point(14.0, 'min', 'i', ['s'])
    graded = grade_fret(r)
    assert graded['reasons']['equilibrium'] == 'incubation_recorded_for_the_sheet' and graded['native']['incubation_min'] == 14.0 and graded['native']['incubation_refs'] == ['s']
    assert graded['criteria']['equilibrium'] == {'status': 'unknown', 'support_refs': []}
    assert _criterion(graded, 'equilibrium') == {'status': 'conflicting', 'support_refs': ['s']}
    r['quantities']['incubation_time'] = point(900.0, 's', 'i', ['s'])      # 15 min exactly: allowed, so unknown
    assert status(r, 'equilibrium') == 'unknown'
    r['quantities']['incubation_time'] = point(840.0, 's', 'i', ['s'])      # 14 min
    assert status(r, 'equilibrium') == 'conflicting'
    r['quantities']['incubation_time'] = point(2.0, 'h', 'i', ['s'])
    assert status(r, 'equilibrium') == 'unknown'


def test_labelling_scheme():
    r = synthetic_record()
    assert reason(r, 'labelling_scheme') == 'labelling_shown_not_to_alter_binding'
    r['facts']['labelling_does_not_alter_binding'] = fact('no', ['s'])
    assert reason(r, 'labelling_scheme') == 'labelling_alters_binding' and status(r, 'labelling_scheme') == 'conflicting'
    r['facts']['labelling_does_not_alter_binding'] = fact('unknown')
    assert reason(r, 'labelling_scheme') == 'direct_labelling' and status(r, 'labelling_scheme') == 'supported'
    r['facts']['indirect_labelling_used'] = fact('yes', ['s'])
    assert reason(r, 'labelling_scheme') == 'indirect_labelling_not_shown_harmless' and status(r, 'labelling_scheme') == 'unknown'
    r['facts']['labelling_does_not_alter_binding'] = fact('yes', ['s'])            # an indirect labelling shown harmless is supported
    assert status(r, 'labelling_scheme') == 'supported'
    r['facts']['indirect_labelling_used'] = fact('unknown')
    r['facts']['labelling_does_not_alter_binding'] = fact('unknown')
    assert reason(r, 'labelling_scheme') == 'labelling_not_stated'
    r['facts']['indirect_labelling_used'] = fact('not_applicable')
    r['facts']['labelling_does_not_alter_binding'] = fact('not_applicable')
    assert status(r, 'labelling_scheme') == 'not_applicable'


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
    graded = grade_fret(r)                                                                    # the count and the independence are recorded, the sheet judges them
    assert graded['reasons']['replicates'] == 'replicate_count_recorded_for_the_sheet' and graded['criteria']['replicates']['status'] == 'unknown'
    assert graded['native']['replicate_count'] == 2 and graded['native']['replicate_independent'] == 'yes' and graded['native']['replicate_refs']
    assert status(r, 'replicates') == 'conflicting'
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported'
    r['facts']['independent_titrations'] = fact('no', ['s'])                                 # a stated 'no' is a fact the grader judges
    assert grade_fret(r)['criteria']['replicates']['status'] == 'conflicting' and reason(r, 'replicates') == 'replicates_not_independent'
    r['facts']['independent_titrations'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown' and grade_fret(r)['native']['replicate_independent'] == 'unknown'
    missing(r, 'replicate_count')
    assert reason(r, 'replicates') == 'replicate_count_or_independence_unknown'


def test_direct_vs_competition():
    r = synthetic_record()                                            # 20 nM against 40 nM: ratio 2
    graded = grade_fret(r)
    assert graded['native']['estimate_fold'] == pytest.approx(2.0) and graded['reasons']['direct_vs_competition'] == 'estimates_recorded_for_the_sheet' and graded['criteria']['direct_vs_competition']['status'] == 'unknown'
    assert status(r, 'direct_vs_competition') == 'supported'
    r['quantities']['ki'] = point(60.0, 'nM', 'k', ['s'])             # ratio exactly 3: recorded
    assert grade_fret(r)['native']['estimate_fold'] == pytest.approx(3.0) and status(r, 'direct_vs_competition') == 'supported'
    r['quantities']['ki'] = point(0.0061, 'uM', 'k', ['s'])           # 6.1 nM: 20 / 6.1 = 3.28
    assert grade_fret(r)['native']['estimate_fold'] == pytest.approx(3.2787, abs=1e-3) and grade_fret(r)['native']['estimate_refs']
    assert status(r, 'direct_vs_competition') == 'supported'          # the fold gap is between 3 and 10: supported with a degree (see the converter test)
    missing(r, 'ki')
    assert reason(r, 'direct_vs_competition') == 'kd_or_ki_missing'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    assert status(r, 'direct_vs_competition') == 'not_applicable'
