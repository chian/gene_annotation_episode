"""Trp grader: each criterion's rule on records, with the arithmetic worked by hand."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_trp_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_grader import CRITERIA, grade_trp
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.trp_cases import sparse_record, synthetic_record


def status(record, criterion):
    """The status after the sheet's judgement where the grader handed the recorded facts over, else the grader's own (threshold-boundary cases are judged on the sheet side)."""
    return _criterion(grade_trp(record), criterion)['status']


def reason(record, criterion):
    return grade_trp(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere():
    graded = grade_trp(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 15
    handed_over = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed_over == {'signal_amplitude', 'excitation_selectivity', 'concentration_series', 'protein_concentration', 'replicates'}      # the inner filter, the dilution and the equilibrium are decided by their stated facts
    assert all(graded['criteria'][name] == {'status': 'unknown', 'support_refs': []} for name in handed_over)                      # the grader holds no threshold
    judged = {name: _criterion(graded, name) for name in CRITERIA}
    assert {c['status'] for c in judged.values()} == {'supported'}
    assert all(c['support_refs'] for c in judged.values())
    native = graded['native']
    assert native['kd_nM'] == 20.0 and native['constant_name'] == 'kd' and native['constant_nM'] == 20.0 and graded['experiment_type'] == 'trp_quenching'
    assert native['protein_over_kd'] == pytest.approx(0.25) and native['protein_nM'] == 5.0 and native['excitation_nm'] == 295.0
    assert native['concentration_count'] == 12 and native['concentration_low_over_constant'] == pytest.approx(0.05) and native['concentration_high_over_constant'] == pytest.approx(102.4)
    assert native['incubation_min'] == 5.0 and native['change_direction'] == 'quenching' and native['emission_shift_direction'] == 'blue'


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_trp(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['criteria']['signal_amplitude']['status'] == 'unknown' and graded['native']['kd_nM'] == 20.0


def test_signal_amplitude_records_the_change_and_the_sheet_judges_it():
    r = synthetic_record()
    r['quantities']['fluorescence_change'] = point(5.0, 'percent', 'c', ['s'])        # recorded; the grader does not judge it
    graded = grade_trp(r)
    assert graded['native']['fluorescence_change_percent'] == 5.0 and graded['native']['change_refs'] == ['s']
    assert graded['criteria']['signal_amplitude'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['signal_amplitude'] == 'fluorescence_change_recorded_for_the_sheet'
    assert status(r, 'signal_amplitude') == 'supported'
    r['quantities']['fluorescence_change'] = point(1.0, 'percent', 'c', ['s'])
    assert status(r, 'signal_amplitude') == 'conflicting'
    missing(r, 'fluorescence_change')
    assert reason(r, 'signal_amplitude') == 'fluorescence_change_not_given' and status(r, 'signal_amplitude') == 'unknown'


def test_excitation_is_recorded_and_the_sheet_judges_the_tyrosine_excitation():
    r = synthetic_record()
    graded = grade_trp(r)
    assert graded['reasons']['excitation_selectivity'] == 'excitation_recorded_for_the_sheet' and graded['criteria']['excitation_selectivity'] == {'status': 'unknown', 'support_refs': []}
    assert graded['native']['excitation_nm'] == 295.0 and graded['native']['excitation_refs']
    assert status(r, 'excitation_selectivity') == 'supported'
    r['quantities']['excitation_wavelength'] = point(300.0, 'nm', 'e', ['s'])
    assert status(r, 'excitation_selectivity') == 'supported'
    r['quantities']['excitation_wavelength'] = point(280.0, 'nm', 'e', ['s'])
    assert grade_trp(r)['native']['excitation_nm'] == 280.0 and status(r, 'excitation_selectivity') == 'unknown'
    r['quantities']['excitation_wavelength'] = point(294.9, 'nm', 'e', ['s'])
    assert status(r, 'excitation_selectivity') == 'unknown'
    missing(r, 'excitation_wavelength')
    assert reason(r, 'excitation_selectivity') == 'excitation_wavelength_not_stated'


def test_inner_filter_a_correction_then_the_absorbance_then_the_facts_decide():
    r = synthetic_record()
    assert reason(r, 'inner_filter') == 'inner_filter_corrected'
    r['facts']['inner_filter_corrected'] = fact('no', ['s'])                       # not corrected, absorbance 0.02 AU
    graded = grade_trp(r)                                                          # the absorbance is recorded, the sheet judges it
    assert graded['reasons']['inner_filter'] == 'ligand_absorbance_recorded_for_the_sheet' and graded['criteria']['inner_filter'] == {'status': 'unknown', 'support_refs': []}
    assert graded['native']['ligand_absorbance'] == 0.02 and graded['native']['absorbance_refs'] and status(r, 'inner_filter') == 'supported'
    r['quantities']['ligand_absorbance'] = point(0.05, 'AU', 'a', ['s'])           # recorded
    assert status(r, 'inner_filter') == 'supported'
    r['quantities']['ligand_absorbance'] = point(0.5, 'AU', 'a', ['s'])
    assert grade_trp(r)['native']['ligand_absorbance'] == 0.5 and status(r, 'inner_filter') == 'conflicting'
    r['facts']['inner_filter_corrected'] = fact('yes', ['s'])                      # a correction makes a large absorbance acceptable
    assert reason(r, 'inner_filter') == 'inner_filter_corrected'
    r['facts']['inner_filter_corrected'] = fact('unknown')
    missing(r, 'ligand_absorbance')
    assert reason(r, 'inner_filter') == 'ligand_absorbance_negligible'            # negligible: yes
    r['facts']['ligand_absorbance_negligible'] = fact('no', ['s'])
    assert reason(r, 'inner_filter') == 'inner_filter_not_corrected' and status(r, 'inner_filter') == 'conflicting'
    r['facts']['ligand_absorbance_negligible'] = fact('unknown')
    assert reason(r, 'inner_filter') == 'inner_filter_not_addressed' and status(r, 'inner_filter') == 'unknown'
    r['facts']['inner_filter_corrected'] = fact('no', ['s'])
    assert reason(r, 'inner_filter') == 'inner_filter_not_corrected'
    for name in ('inner_filter_corrected', 'ligand_absorbance_negligible'):
        r['facts'][name] = fact('not_applicable')
    assert status(r, 'inner_filter') == 'not_applicable'


def test_dilution_a_correction_then_the_added_volume_then_the_fact_decide():
    r = synthetic_record()
    assert reason(r, 'dilution') == 'dilution_corrected'
    r['facts']['dilution_corrected'] = fact('no', ['s'])                           # 3 percent added
    graded = grade_trp(r)                                                          # the added volume is recorded, the sheet judges it
    assert graded['reasons']['dilution'] == 'added_volume_recorded_for_the_sheet' and graded['criteria']['dilution'] == {'status': 'unknown', 'support_refs': []}
    assert graded['native']['added_volume_percent'] == 3.0 and graded['native']['added_volume_refs'] and status(r, 'dilution') == 'supported'
    r['quantities']['added_volume_fraction'] = point(5.0, 'percent', 'v', ['s'])   # recorded
    assert status(r, 'dilution') == 'supported'
    r['quantities']['added_volume_fraction'] = point(60.0, 'percent', 'v', ['s'])
    assert grade_trp(r)['native']['added_volume_percent'] == 60.0 and status(r, 'dilution') == 'conflicting'
    missing(r, 'added_volume_fraction')
    assert reason(r, 'dilution') == 'dilution_not_corrected'
    r['facts']['dilution_corrected'] = fact('unknown')
    assert reason(r, 'dilution') == 'dilution_not_addressed' and status(r, 'dilution') == 'unknown'
    r['facts']['dilution_corrected'] = fact('not_applicable')
    assert status(r, 'dilution') == 'not_applicable'


@pytest.mark.parametrize('criterion, fact_name', [('buffer_blank', 'buffer_blank_subtracted'), ('ligand_fluorescence', 'ligand_only_control_measured'), ('photobleaching', 'photobleaching_checked'), ('saturation', 'signal_saturates'), ('quenching_mechanism', 'quenching_is_static')])
def test_single_fact_criteria_are_the_one_fact(criterion, fact_name):
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('unknown', 'unknown'), ('not_applicable', 'not_applicable')):
        r['facts'][fact_name] = fact(answer, ['s'])
        assert status(r, criterion) == expected


def test_specificity_one_control_is_enough_and_a_no_fails_only_when_none_is_done():
    r = synthetic_record()
    names = ('nonbinding_control_done', 'trp_analogue_control_done', 'signal_localised_to_binding_site')
    assert reason(r, 'specificity_control') == 'a_specificity_control_done'
    r['facts']['nonbinding_control_done'] = fact('no', ['s'])
    r['facts']['trp_analogue_control_done'] = fact('unknown')
    assert status(r, 'specificity_control') == 'supported'                          # the binding-site fact is still yes
    r['facts']['signal_localised_to_binding_site'] = fact('unknown')
    assert reason(r, 'specificity_control') == 'fact_answered_no' and status(r, 'specificity_control') == 'conflicting'
    r['facts']['nonbinding_control_done'] = fact('unknown')
    assert reason(r, 'specificity_control') == 'fact_unknown' and status(r, 'specificity_control') == 'unknown'
    r['facts']['trp_analogue_control_done'] = fact('yes', ['s'])
    assert status(r, 'specificity_control') == 'supported'
    for name in names:
        r['facts'][name] = fact('not_applicable')
    assert status(r, 'specificity_control') == 'not_applicable'


def test_concentration_series_by_count_and_span():
    r = synthetic_record()
    r['concentration_series']['value'] = [4.0, 16.0, 40.0, 80.0, 120.0, 160.0, 190.0, 200.0]   # eight values, lowest 0.2 x KD, highest 10 x KD: on the limits
    graded = grade_trp(r)
    assert graded['native']['concentration_count'] == 8 and graded['reasons']['concentration_series'] == 'series_recorded_for_the_sheet' and graded['criteria']['concentration_series'] == {'status': 'unknown', 'support_refs': []}
    assert graded['native']['count_refs'] and graded['native']['series_refs'] == ['span_exp_synthetic_trp_1']
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = [4.0, 16.0, 40.0, 80.0, 120.0, 160.0, 200.0]          # seven: recorded, the sheet judges the count
    assert grade_trp(r)['native']['concentration_count'] == 7 and status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [6.0, 16.0, 40.0, 80.0, 120.0, 160.0, 190.0, 400.0]   # lowest 0.3 x KD
    assert grade_trp(r)['native']['concentration_low_over_constant'] == pytest.approx(0.3)
    r['concentration_series']['value'] = [4.0, 16.0, 40.0, 80.0, 120.0, 160.0, 190.0, 199.0]   # highest 9.95 x KD
    assert grade_trp(r)['native']['concentration_high_over_constant'] == pytest.approx(9.95)
    r['concentration_series']['value'] = [0.004, 0.016, 0.04, 0.08, 0.12, 0.16, 0.19, 0.2]      # the same in uM
    r['concentration_series']['unit'] = 'uM'
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert reason(r, 'concentration_series') == 'series_recorded_for_the_sheet' and status(r, 'concentration_series') == 'unknown'    # 12 points counted, no list: the count is recorded, the span is not known
    assert grade_trp(r)['native']['concentration_low_over_constant'] is None
    r['quantities']['titration_point_count'] = point(7, 'count', 'n', ['s'])           # a count below the minimum fails without a list
    assert grade_trp(r)['native']['concentration_count'] == 7 and status(r, 'concentration_series') == 'conflicting'
    r['quantities']['titration_point_count'] = point(8, 'count', 'n', ['s'])
    assert status(r, 'concentration_series') == 'unknown'
    missing(r, 'titration_point_count')
    assert status(r, 'concentration_series') == 'unknown' and grade_trp(r)['native']['concentration_count'] is None and reason(r, 'concentration_series') == 'kd_or_series_missing'


def test_without_a_kd_the_span_cannot_be_judged_and_a_ksv_is_never_the_constant():
    r = synthetic_record()
    missing(r, 'kd')       # the Stern-Volmer constant 2.0e4 M^-1 is present but is no binding constant
    graded = grade_trp(r)
    assert graded['native']['constant_name'] is None and graded['native']['constant_nM'] is None
    assert _criterion(graded, 'concentration_series')['status'] == 'unknown'


def test_protein_concentration_by_ratio_and_by_fact():
    r = synthetic_record()                                                           # protein 5 nM, KD 20 nM: 0.25 x KD
    r['quantities']['protein_concentration'] = point(20.0, 'nM', 'p', ['s'])         # 1.0 x KD: exactly the limit, allowed
    graded = grade_trp(r)
    assert graded['native']['protein_over_kd'] == pytest.approx(1.0) and graded['native']['tight_binding_handled'] is True and graded['native']['protein_refs']
    assert graded['criteria']['protein_concentration'] == {'status': 'unknown', 'support_refs': []} and graded['reasons']['protein_concentration'] == 'protein_over_kd_recorded_for_the_sheet'
    assert status(r, 'protein_concentration') == 'supported'
    r['quantities']['protein_concentration'] = point(0.1, 'uM', 'p', ['s'])          # 100 nM = 5 x KD
    assert grade_trp(r)['native']['protein_over_kd'] == pytest.approx(5.0) and status(r, 'protein_concentration') == 'supported'      # tight binding considered: yes
    r['facts']['tight_binding_considered'] = fact('unknown')
    assert grade_trp(r)['native']['tight_binding_handled'] is False
    r['fit_model'] = 'quadratic'
    assert grade_trp(r)['native']['tight_binding_handled'] is True
    r['fit_model'] = '1:1'
    missing(r, 'protein_concentration')                                               # no ratio: the fact decides
    r['facts']['protein_at_or_below_kd'] = fact('yes', ['s'])
    assert reason(r, 'protein_concentration') == 'protein_at_or_below_kd'
    r['facts']['protein_at_or_below_kd'] = fact('no', ['s'])
    assert reason(r, 'protein_concentration') == 'protein_above_kd_without_tight_binding_analysis'
    r['facts']['tight_binding_considered'] = fact('yes', ['s'])
    assert status(r, 'protein_concentration') == 'supported'
    r['facts']['protein_at_or_below_kd'] = fact('unknown')
    assert reason(r, 'protein_concentration') == 'protein_or_kd_missing'


def test_equilibrium():
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('not_applicable', 'not_applicable')):
        r['facts']['equilibrium_reached'] = fact(answer, ['s'])
        assert status(r, 'equilibrium') == expected
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert status(r, 'equilibrium') == 'unknown'                    # 5 min, but nothing says equilibrium
    r['quantities']['incubation_time'] = point(1.0, 'min', 'i', ['s'])
    graded = grade_trp(r)
    assert graded['reasons']['equilibrium'] == 'incubation_recorded_for_the_sheet' and graded['native']['incubation_min'] == 1.0 and graded['native']['incubation_refs'] == ['s']
    assert graded['criteria']['equilibrium'] == {'status': 'unknown', 'support_refs': []}
    assert _criterion(graded, 'equilibrium') == {'status': 'conflicting', 'support_refs': ['s']}
    r['quantities']['incubation_time'] = point(120.0, 's', 'i', ['s'])      # 2 min exactly: allowed, so unknown
    assert status(r, 'equilibrium') == 'unknown'
    r['quantities']['incubation_time'] = point(90.0, 's', 'i', ['s'])       # 1.5 min
    assert status(r, 'equilibrium') == 'conflicting'
    r['quantities']['incubation_time'] = point(1.0, 'h', 'i', ['s'])
    assert status(r, 'equilibrium') == 'unknown'


def test_fit_model_a_stern_volmer_fit_gives_ksv_not_a_kd():
    r = synthetic_record()
    assert reason(r, 'fit_model') == 'model_stated'
    for model in ('hill', 'quadratic', 'other'):
        r['fit_model'] = model
        assert status(r, 'fit_model') == 'supported'
    r['fit_model'] = 'stern_volmer'
    assert reason(r, 'fit_model') == 'stern_volmer_fit_gives_ksv_not_kd' and status(r, 'fit_model') == 'conflicting'
    r['fit_model'] = None
    assert reason(r, 'fit_model') == 'fit_model_not_stated' and status(r, 'fit_model') == 'unknown'


def test_replicates():
    r = synthetic_record()
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    graded = grade_trp(r)                                                                     # the count and the independence are recorded, the sheet judges them
    assert graded['reasons']['replicates'] == 'replicate_count_recorded_for_the_sheet' and graded['criteria']['replicates']['status'] == 'unknown'
    assert graded['native']['replicate_count'] == 2 and graded['native']['replicate_independent'] == 'yes' and graded['native']['replicate_refs']
    assert status(r, 'replicates') == 'conflicting'
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported'
    r['facts']['independent_titrations'] = fact('no', ['s'])                                 # a stated 'no' is a fact the grader judges
    assert grade_trp(r)['criteria']['replicates']['status'] == 'conflicting' and reason(r, 'replicates') == 'replicates_not_independent'
    r['facts']['independent_titrations'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown' and grade_trp(r)['native']['replicate_independent'] == 'unknown'
    missing(r, 'replicate_count')
    assert reason(r, 'replicates') == 'replicate_count_or_independence_unknown'
