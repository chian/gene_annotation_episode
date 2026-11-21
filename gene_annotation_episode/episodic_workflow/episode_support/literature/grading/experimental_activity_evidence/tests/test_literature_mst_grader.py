"""MST grader: each criterion's rule on records, with the arithmetic worked by hand."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_mst_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_grader import CRITERIA, grade_mst
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.mst_cases import sparse_record, synthetic_record


def status(record, criterion):
    """The status after the sheet's judgement where the grader handed the recorded facts over, else the grader's own (threshold-boundary cases are judged on the sheet side)."""
    return _criterion(grade_mst(record), criterion)['status']


def reason(record, criterion):
    return grade_mst(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere():
    graded = grade_mst(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 13
    handed_over = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed_over == {'signal_amplitude', 'labelled_concentration', 'concentration_series', 'readout_window', 'replicates', 'direct_vs_competition'}      # equilibrium is decided by its stated fact
    assert all(graded['criteria'][name] == {'status': 'unknown', 'support_refs': []} for name in handed_over)                      # the grader holds no threshold
    judged = {name: _criterion(graded, name) for name in CRITERIA}
    assert {c['status'] for c in judged.values()} == {'supported'}
    assert all(c['support_refs'] for c in judged.values())
    native = graded['native']
    assert native['kd_nM'] == 20.0 and native['ki_nM'] == 40.0 and native['constant_name'] == 'kd' and graded['experiment_type'] == 'mst'
    assert native['labelled_over_kd'] == pytest.approx(0.25) and native['labelled_nM'] == 5.0 and native['fhot_s'] == 1.5
    assert native['concentration_count'] == 12 and native['concentration_low_over_constant'] == pytest.approx(0.05) and native['concentration_high_over_constant'] == pytest.approx(102.4)
    assert native['incubation_min'] == 15.0 and native['capillary_type'] == 'hydrophilic' and native['label_type'] == 'covalent_nhs_dye' and native['readout_signal'] == 'thermophoresis'


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_mst(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['criteria']['signal_amplitude']['status'] == 'unknown' and graded['native']['kd_nM'] == 20.0


def test_signal_amplitude_records_every_given_number_and_the_sheet_judges_them():
    r = synthetic_record()
    r['quantities']['signal_to_noise'] = point(5.0, 'ratio', 's', ['s'])             # recorded; the grader does not judge it
    r['quantities']['fnorm_amplitude'] = point(5.0, 'permille', 'a', ['s'])
    graded = grade_mst(r)
    assert graded['native']['signal_to_noise'] == 5.0 and graded['native']['fnorm_amplitude'] == 5.0 and set(graded['native']['signal_refs']) >= {'s'}
    assert graded['criteria']['signal_amplitude'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['signal_amplitude'] == 'signal_recorded_for_the_sheet'
    assert status(r, 'signal_amplitude') == 'supported'
    r['quantities']['signal_to_noise'] = point(1.0, 'ratio', 's', ['s'])
    assert status(r, 'signal_amplitude') == 'conflicting'
    r['quantities']['signal_to_noise'] = point(18.0, 'ratio', 's', ['s'])
    r['quantities']['fnorm_amplitude'] = point(1.0, 'permille', 'a', ['s'])
    assert status(r, 'signal_amplitude') == 'conflicting'
    missing(r, 'signal_to_noise')                                                     # the amplitude alone is recorded
    graded = grade_mst(r)
    assert graded['native']['signal_to_noise'] is None and graded['native']['fnorm_amplitude'] == 1.0 and graded['reasons']['signal_amplitude'] == 'signal_recorded_for_the_sheet'
    r['quantities']['fnorm_amplitude'] = point(12.0, 'permille', 'a', ['s'])
    assert status(r, 'signal_amplitude') == 'supported'
    missing(r, 'fnorm_amplitude')
    assert reason(r, 'signal_amplitude') == 'signal_not_given'
    r['quantities']['signal_to_noise'] = point(18.0, 'ratio', 's', ['s'])             # the signal-to-noise alone is recorded
    assert status(r, 'signal_amplitude') == 'supported'


def test_initial_fluorescence_consistency_decides_and_a_check_without_a_result_is_unknown():
    r = synthetic_record()
    assert reason(r, 'initial_fluorescence') == 'initial_fluorescence_consistent'
    r['facts']['initial_fluorescence_consistent'] = fact('no', ['s'])
    assert reason(r, 'initial_fluorescence') == 'initial_fluorescence_changes_with_titrant' and status(r, 'initial_fluorescence') == 'conflicting'
    r['facts']['initial_fluorescence_consistent'] = fact('unknown')
    assert reason(r, 'initial_fluorescence') == 'initial_fluorescence_result_not_stated' and status(r, 'initial_fluorescence') == 'unknown'      # checked: yes, no result
    r['facts']['initial_fluorescence_checked'] = fact('no', ['s'])
    assert reason(r, 'initial_fluorescence') == 'initial_fluorescence_not_checked' and status(r, 'initial_fluorescence') == 'conflicting'
    r['facts']['initial_fluorescence_checked'] = fact('unknown')
    assert status(r, 'initial_fluorescence') == 'unknown'
    r['facts']['initial_fluorescence_consistent'] = fact('yes', ['s'])                 # a stated consistency is enough without the check fact
    assert status(r, 'initial_fluorescence') == 'supported'
    for name in ('initial_fluorescence_consistent', 'initial_fluorescence_checked'):
        r['facts'][name] = fact('not_applicable')
    assert status(r, 'initial_fluorescence') == 'not_applicable'
    r['facts']['initial_fluorescence_checked'] = fact('unknown')
    assert status(r, 'initial_fluorescence') == 'unknown'


@pytest.mark.parametrize('criterion, fact_name', [('fluorescence_level', 'fluorescence_intensity_in_range'), ('aggregation_adsorption', 'aggregation_or_adsorption_checked'), ('specificity_control', 'nonspecific_binding_checked')])
def test_single_fact_criteria_are_the_one_fact(criterion, fact_name):
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('unknown', 'unknown'), ('not_applicable', 'not_applicable')):
        r['facts'][fact_name] = fact(answer, ['s'])
        assert status(r, criterion) == expected


def test_labelled_concentration_by_ratio_and_by_fact():
    r = synthetic_record()                                                           # detected partner 5 nM, KD 20 nM: 0.25 x KD
    r['quantities']['labelled_concentration'] = point(20.0, 'nM', 't', ['s'])        # 1.0 x KD: exactly the limit, allowed
    graded = grade_mst(r)
    assert graded['native']['labelled_over_kd'] == pytest.approx(1.0) and graded['native']['tight_binding_handled'] is True and graded['native']['labelled_refs']
    assert graded['criteria']['labelled_concentration'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['labelled_concentration'] == 'labelled_over_kd_recorded_for_the_sheet'
    assert status(r, 'labelled_concentration') == 'supported'
    r['quantities']['labelled_concentration'] = point(0.1, 'uM', 't', ['s'])         # 100 nM = 5 x KD
    assert grade_mst(r)['native']['labelled_over_kd'] == pytest.approx(5.0) and status(r, 'labelled_concentration') == 'supported'      # tight binding considered: yes
    r['facts']['tight_binding_considered'] = fact('unknown')
    assert grade_mst(r)['native']['tight_binding_handled'] is False
    r['fit_model'] = 'quadratic'
    assert grade_mst(r)['native']['tight_binding_handled'] is True
    r['fit_model'] = '1:1'
    missing(r, 'labelled_concentration')                                              # no ratio: the fact decides
    r['facts']['labelled_partner_at_or_below_kd'] = fact('yes', ['s'])
    assert reason(r, 'labelled_concentration') == 'labelled_at_or_below_kd'
    r['facts']['labelled_partner_at_or_below_kd'] = fact('no', ['s'])
    assert reason(r, 'labelled_concentration') == 'labelled_above_kd_without_tight_binding_analysis'
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])
    assert status(r, 'labelled_concentration') == 'supported'
    r['facts']['labelled_partner_at_or_below_kd'] = fact('unknown')
    assert reason(r, 'labelled_concentration') == 'labelled_or_kd_missing'
    # a Ki is not the detected partner's KD: with only a Ki the ratio cannot be formed
    r = synthetic_record()
    missing(r, 'kd')
    r['facts']['labelled_partner_at_or_below_kd'] = fact('unknown')
    assert reason(r, 'labelled_concentration') == 'labelled_or_kd_missing'


def test_concentration_series_by_count_and_span():
    r = synthetic_record()
    r['concentration_series']['value'] = [4.0, 8.0, 16.0, 32.0, 64.0, 100.0, 150.0, 180.0, 190.0, 200.0]   # ten values, lowest 0.2 x KD, highest 10 x KD: on the limits
    graded = grade_mst(r)
    assert graded['native']['concentration_count'] == 10 and graded['reasons']['concentration_series'] == 'series_recorded_for_the_sheet' and graded['criteria']['concentration_series'] == {'status': 'unknown', 'support_refs': []}
    assert graded['native']['count_refs'] and graded['native']['series_refs'] == ['span_exp_synthetic_mst_1']
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = [4.0, 8.0, 16.0, 32.0, 64.0, 100.0, 150.0, 180.0, 200.0]          # nine: recorded, the sheet judges the count
    assert grade_mst(r)['native']['concentration_count'] == 9 and status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [6.0, 8.0, 16.0, 32.0, 64.0, 100.0, 150.0, 180.0, 190.0, 400.0]   # lowest 0.3 x KD
    assert grade_mst(r)['native']['concentration_low_over_constant'] == pytest.approx(0.3)
    r['concentration_series']['value'] = [4.0, 8.0, 16.0, 32.0, 64.0, 100.0, 150.0, 180.0, 190.0, 199.0]   # highest 9.95 x KD
    assert grade_mst(r)['native']['concentration_high_over_constant'] == pytest.approx(9.95)
    r['concentration_series']['value'] = [0.004, 0.008, 0.016, 0.032, 0.064, 0.1, 0.15, 0.18, 0.19, 0.2]    # the same in uM
    r['concentration_series']['unit'] = 'uM'
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert reason(r, 'concentration_series') == 'series_recorded_for_the_sheet' and status(r, 'concentration_series') == 'unknown'    # 12 points counted, no list: the count is recorded, the span is not known
    assert grade_mst(r)['native']['concentration_low_over_constant'] is None
    r['quantities']['titration_point_count'] = point(9, 'count', 'n', ['s'])           # a count below the minimum fails without a list
    assert grade_mst(r)['native']['concentration_count'] == 9 and status(r, 'concentration_series') == 'conflicting'
    r['quantities']['titration_point_count'] = point(10, 'count', 'n', ['s'])
    assert status(r, 'concentration_series') == 'unknown'
    missing(r, 'titration_point_count')
    assert status(r, 'concentration_series') == 'unknown' and grade_mst(r)['native']['concentration_count'] is None and reason(r, 'concentration_series') == 'constant_or_series_missing'


def test_the_series_is_judged_against_the_ki_then_the_ec50_when_there_is_no_kd():
    r = synthetic_record()
    missing(r, 'kd')       # Ki 40 nM is the constant: 1 nM is 0.025 x Ki, 2048 nM is 51.2 x Ki
    graded = grade_mst(r)
    assert graded['native']['constant_name'] == 'ki' and graded['native']['constant_nM'] == 40.0
    assert _criterion(graded, 'concentration_series')['status'] == 'supported'
    assert graded['native']['concentration_high_over_constant'] == pytest.approx(51.2)
    missing(r, 'ki')       # EC50 30 nM: 2048 / 30 = 68.27
    graded = grade_mst(r)
    assert graded['native']['constant_name'] == 'ec50' and graded['native']['constant_nM'] == 30.0
    assert graded['native']['concentration_high_over_constant'] == pytest.approx(2048 / 30)
    missing(r, 'ec50')
    assert grade_mst(r)['native']['constant_name'] is None and status(r, 'concentration_series') == 'unknown'


def test_equilibrium():
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('not_applicable', 'not_applicable')):
        r['facts']['equilibrium_reached'] = fact(answer, ['s'])
        assert status(r, 'equilibrium') == expected
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert status(r, 'equilibrium') == 'unknown'                    # 15 min, but nothing says equilibrium
    r['quantities']['incubation_time'] = point(9.0, 'min', 'i', ['s'])
    graded = grade_mst(r)
    assert graded['reasons']['equilibrium'] == 'incubation_recorded_for_the_sheet' and graded['native']['incubation_min'] == 9.0 and graded['native']['incubation_refs'] == ['s']
    assert graded['criteria']['equilibrium'] == {'status': 'unknown', 'support_refs': []}
    assert _criterion(graded, 'equilibrium') == {'status': 'conflicting', 'support_refs': ['s']}
    r['quantities']['incubation_time'] = point(600.0, 's', 'i', ['s'])      # 10 min exactly: allowed, so unknown
    assert status(r, 'equilibrium') == 'unknown'
    r['quantities']['incubation_time'] = point(540.0, 's', 'i', ['s'])      # 9 min
    assert status(r, 'equilibrium') == 'conflicting'
    r['quantities']['incubation_time'] = point(1.0, 'h', 'i', ['s'])
    assert status(r, 'equilibrium') == 'unknown'


def test_labelling_scheme():
    r = synthetic_record()
    assert reason(r, 'labelling_scheme') == 'labelling_shown_not_to_alter_binding'
    r['facts']['labelling_does_not_alter_binding'] = fact('no', ['s'])
    assert reason(r, 'labelling_scheme') == 'labelling_alters_binding' and status(r, 'labelling_scheme') == 'conflicting'
    r['facts']['labelling_does_not_alter_binding'] = fact('unknown')
    for kind in ('covalent_nhs_dye', 'his_tag_nta_dye', 'fluorescent_protein_fusion', 'other'):       # a label without the control: not shown harmless
        r['label_type'] = kind
        assert reason(r, 'labelling_scheme') == 'label_not_shown_harmless' and status(r, 'labelling_scheme') == 'unknown'
    r['label_type'] = 'label_free_intrinsic_fluorescence'
    assert reason(r, 'labelling_scheme') == 'label_free_stated_without_a_span' and status(r, 'labelling_scheme') == 'unknown'      # the label type holds no span: no decision on it alone
    r['facts']['labelling_does_not_alter_binding'] = fact('no', ['s'])                # a stated alteration beats label-free
    assert status(r, 'labelling_scheme') == 'conflicting'
    r['facts']['labelling_does_not_alter_binding'] = fact('yes', ['s'])
    r['label_type'] = 'covalent_nhs_dye'
    assert status(r, 'labelling_scheme') == 'supported'
    r['facts']['labelling_does_not_alter_binding'] = fact('unknown')
    r['label_type'] = None
    assert reason(r, 'labelling_scheme') == 'labelling_not_stated'
    r['facts']['labelling_does_not_alter_binding'] = fact('not_applicable')
    assert status(r, 'labelling_scheme') == 'not_applicable'


def test_readout_window():
    r = synthetic_record()
    graded = grade_mst(r)                                                            # the F-hot time is recorded, the sheet judges it
    assert graded['reasons']['readout_window'] == 'fhot_time_recorded_for_the_sheet' and graded['criteria']['readout_window'] == {'status': 'unknown', 'support_refs': []}
    assert graded['native']['fhot_s'] == 1.5 and graded['native']['fhot_refs']
    r['quantities']['fhot_time'] = point(1.0, 's', 'f', ['s'])
    assert status(r, 'readout_window') == 'supported'
    r['quantities']['fhot_time'] = point(0.0, 's', 'f', ['s'])                       # the window starts with the laser: the sheet judges it conflicting
    assert status(r, 'readout_window') == 'conflicting'
    r['quantities']['fhot_time'] = point(999.0, 'ms', 'f', ['s'])                    # 0.999 s
    assert grade_mst(r)['native']['fhot_s'] == pytest.approx(0.999)
    r['quantities']['fhot_time'] = point(1500.0, 'ms', 'f', ['s'])
    assert status(r, 'readout_window') == 'supported' and grade_mst(r)['native']['fhot_s'] == pytest.approx(1.5)
    missing(r, 'fhot_time')
    assert reason(r, 'readout_window') == 'fhot_time_not_stated' and status(r, 'readout_window') == 'unknown'
    r['readout_signal'] = 't_jump'                                                    # a temperature-jump readout is stated: no F-hot time is asked
    assert reason(r, 'readout_window') == 'temperature_jump_readout_stated_without_a_span' and status(r, 'readout_window') == 'unknown'      # the readout holds no span: no decision on it alone
    r['readout_signal'] = 'initial_fluorescence'
    assert reason(r, 'readout_window') == 'initial_fluorescence_readout' and status(r, 'readout_window') == 'not_applicable'
    r['readout_signal'] = None
    assert reason(r, 'readout_window') == 'readout_signal_not_stated' and status(r, 'readout_window') == 'unknown'


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
    assert grade_mst(r)['criteria']['fit_model']['support_refs'] == ['span_exp_synthetic_mst_1']                    # supported on the quoted spans of the reported constants
    r['fit_model'] = '1:1'
    r['assay_format'] = 'competition'
    assert grade_mst(r)['criteria']['fit_model']['support_refs'] == ['span_exp_synthetic_mst_1']                    # a conflict rests on them too
    for name in ('kd', 'ki', 'ec50'):
        missing(r, name)
        r['quantities'][name]['source_refs'] = []                                           # a constant that is not reported quotes no span
    for model, form in (('1:1', 'competition'), ('competitive_binding', 'direct_titration'), ('quadratic', None)):      # no reported constant: no span, so no decision
        r['fit_model'], r['assay_format'] = model, form
        assert reason(r, 'fit_model') == 'model_stated_without_a_reported_constant' and grade_mst(r)['criteria']['fit_model'] == {'status': 'unknown', 'support_refs': []}
    r['fit_model'] = None
    assert reason(r, 'fit_model') == 'fit_model_not_stated'


def test_replicates():
    r = synthetic_record()
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    graded = grade_mst(r)                                                                     # the count and the independence are recorded, the sheet judges them
    assert graded['reasons']['replicates'] == 'replicate_count_recorded_for_the_sheet' and graded['criteria']['replicates']['status'] == 'unknown'
    assert graded['native']['replicate_count'] == 2 and graded['native']['replicate_independent'] == 'yes' and graded['native']['replicate_refs']
    assert status(r, 'replicates') == 'conflicting'
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported'
    r['facts']['independent_titrations'] = fact('no', ['s'])                                 # a stated 'no' is a fact the grader judges
    assert grade_mst(r)['criteria']['replicates']['status'] == 'conflicting' and reason(r, 'replicates') == 'replicates_not_independent'
    r['facts']['independent_titrations'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown' and grade_mst(r)['native']['replicate_independent'] == 'unknown'
    missing(r, 'replicate_count')
    assert reason(r, 'replicates') == 'replicate_count_or_independence_unknown'


def test_direct_vs_competition():
    r = synthetic_record()                                            # 20 nM against 40 nM: ratio 2
    graded = grade_mst(r)
    assert graded['native']['estimate_fold'] == pytest.approx(2.0) and graded['reasons']['direct_vs_competition'] == 'estimates_recorded_for_the_sheet' and graded['criteria']['direct_vs_competition']['status'] == 'unknown'
    assert status(r, 'direct_vs_competition') == 'supported'
    r['quantities']['ki'] = point(60.0, 'nM', 'k', ['s'])             # ratio exactly 3: recorded
    assert grade_mst(r)['native']['estimate_fold'] == pytest.approx(3.0) and status(r, 'direct_vs_competition') == 'supported'
    r['quantities']['ki'] = point(0.0061, 'uM', 'k', ['s'])           # 6.1 nM: 20 / 6.1 = 3.28
    assert grade_mst(r)['native']['estimate_fold'] == pytest.approx(3.2787, abs=1e-3) and grade_mst(r)['native']['estimate_refs']
    assert status(r, 'direct_vs_competition') == 'supported'          # the fold gap is between 3 and 10: supported with a degree (see the converter test)
    missing(r, 'ki')
    assert reason(r, 'direct_vs_competition') == 'kd_or_ki_missing'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    assert status(r, 'direct_vs_competition') == 'not_applicable'
