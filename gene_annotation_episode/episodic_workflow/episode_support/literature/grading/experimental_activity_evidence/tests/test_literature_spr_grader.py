"""SPR grader: each criterion's rule on real records (the PopZ case is in test_literature_spr_popz_case.py)."""
from copy import deepcopy
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spr_grader import CRITERIA, grade_spr
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spr_cases import synthetic_record


def status(record, criterion):
    """The status after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_spr(record), criterion)['status']


def grader_status(record, criterion):
    return grade_spr(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_spr(record)['reasons'][criterion]


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_the_recorded_facts():
    graded = grade_spr(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == {'concentration_series', 'fit_model', 'rmax_consistency', 'replicates', 'kinetic_consistency', 'steady_state_vs_kinetic'}
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'}
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['concentration_count'] == 6 and native['concentration_low_over_kd'] == pytest.approx(0.1) and native['concentration_high_over_kd'] == pytest.approx(30.0)
    assert native['chi2_over_rmax'] == pytest.approx(0.01) and native['steady_kinetic_fold'] == pytest.approx(1.5)
    assert native['replicate_count'] == 3 and native['replicate_independent'] == 'yes'
    assert native['kd_nM'] == 20.0
    assert native['kd_from_rates_nM'] == pytest.approx(20.0)
    assert native['rmax_theoretical'] == 400.0 and native['rmax_ratio'] == 0.5


def test_reference_subtraction():
    r = synthetic_record()
    r['facts']['double_referencing'] = fact('unknown')
    assert status(r, 'reference_subtraction') == 'supported'
    r['facts']['reference_surface'] = fact('no')
    assert status(r, 'reference_subtraction') == 'conflicting'
    r['facts']['reference_surface'] = fact('unknown')
    assert status(r, 'reference_subtraction') == 'unknown'


def test_concentration_series():
    r = synthetic_record()
    r['concentration_series']['value'] = [2.0, 20.0, 200.0, 600.0]
    assert reason(r, 'concentration_series') == 'concentration_series_recorded_for_the_sheet' and grader_status(r, 'concentration_series') == 'unknown'
    native = grade_spr(r)['native']
    assert native['concentration_count'] == 4 and native['concentration_low_over_kd'] == pytest.approx(0.1) and native['concentration_high_over_kd'] == pytest.approx(30.0)
    assert native['concentration_refs'] == ['span_exp_synthetic_spr_1']
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [30.0, 40.0, 60.0, 100.0, 200.0]
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [0.002, 0.006, 0.02, 0.06, 0.2, 0.6]
    r['concentration_series']['unit'] = 'uM'
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = None
    assert status(r, 'concentration_series') == 'unknown' and reason(r, 'concentration_series') == 'kd_or_series_missing'


def test_fit_model():
    r = synthetic_record()
    r['facts']['analyte_bivalent_or_oligomeric'] = fact('yes')
    assert status(r, 'fit_model') == 'conflicting'
    r['fit_model'] = 'bivalent_analyte'
    assert status(r, 'fit_model') == 'supported'
    r = synthetic_record()
    r['quantities']['chi_squared'] = point(25.0, 'RU^2', 'chi', ['s'])
    assert reason(r, 'fit_model') == 'chi_squared_over_rmax_recorded_for_the_sheet' and grade_spr(r)['native']['chi2_over_rmax'] == pytest.approx(0.125)
    assert status(r, 'fit_model') == 'supported'                                            # 0.125 is above the full limit but short of the zero limit: a degree, no conflict
    r['quantities']['chi_squared'] = point(70.0, 'RU^2', 'chi', ['s'])
    assert status(r, 'fit_model') == 'conflicting'
    r = synthetic_record()
    r['facts']['analyte_bivalent_or_oligomeric'] = fact('unknown')
    assert status(r, 'fit_model') == 'unknown'
    r = synthetic_record()
    r['fit_model'] = None
    assert status(r, 'fit_model') == 'unknown'


def test_rmax_consistency():
    r = synthetic_record()
    # theoretical = 20 kDa / 50 kDa * 1000 RU * 1 = 400 RU; the record gives 200 RU (ratio 0.5)
    assert grade_spr(r)['native']['rmax_theoretical'] == 400.0
    assert status(r, 'rmax_consistency') == 'supported' and reason(r, 'rmax_consistency') == 'rmax_ratio_recorded_for_the_sheet'
    r['quantities']['rmax'] = point(30.0, 'RU', 'rmax', ['s'])
    assert grade_spr(r)['native']['rmax_ratio'] == pytest.approx(0.075)
    assert status(r, 'rmax_consistency') == 'conflicting'
    r['quantities']['rmax'] = point(900.0, 'RU', 'rmax', ['s'])
    assert status(r, 'rmax_consistency') == 'conflicting'


def test_mass_transport_baseline_replicates_activity():
    r = synthetic_record()
    r['facts']['mass_transport'] = fact('checked_limited')
    assert status(r, 'mass_transport') == 'conflicting'
    r['facts']['mass_transport'] = fact('not_checked')
    assert status(r, 'mass_transport') == 'unknown'
    r['facts']['regeneration'] = fact('not_applicable')
    assert status(r, 'baseline_regeneration') == 'supported'
    r['facts']['baseline_drift'] = fact('no')
    assert status(r, 'baseline_regeneration') == 'conflicting'
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'conflicting' and grader_status(r, 'replicates') == 'unknown'      # the count is judged on the sheet side
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    r['facts']['independent_surfaces'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown'
    r['facts']['independent_surfaces'] = fact('no', ['s'])
    assert grader_status(r, 'replicates') == 'conflicting' and reason(r, 'replicates') == 'replicates_not_independent'
    r['facts']['immobilized_activity'] = fact('no')
    assert status(r, 'immobilized_activity') == 'conflicting'


def test_kinetic_consistency_and_steady_state_agreement():
    r = synthetic_record()
    r['quantities']['koff'] = point(5e-3, 's^-1', 'koff', ['s'])
    assert grade_spr(r)['native']['kd_from_rates_nM'] == 50.0 and reason(r, 'kinetic_consistency') == 'kd_from_rates_recorded_for_the_sheet'
    assert status(r, 'kinetic_consistency') == 'conflicting'                              # a relative gap of 1.5 is beyond the zero limit
    r['quantities']['kd_steady_state'] = point(0.06, 'uM', 'ss', ['s'])
    assert grade_spr(r)['native']['steady_kinetic_fold'] == pytest.approx(3.0) and reason(r, 'steady_state_vs_kinetic') == 'estimate_fold_recorded_for_the_sheet'
    assert status(r, 'steady_state_vs_kinetic') == 'supported'                            # threefold: beyond the full limit, short of the zero limit
    r['quantities']['kd_steady_state'] = point(0.3, 'uM', 'ss', ['s'])
    assert status(r, 'steady_state_vs_kinetic') == 'conflicting'
    r['quantities']['kd_steady_state'] = point(0.03, 'uM', 'ss', ['s'])
    assert status(r, 'steady_state_vs_kinetic') == 'supported'
    r = synthetic_record()
    r['quantities']['kon'] = deepcopy(r['quantities']['kd_spread'])
    r['quantities']['kon']['status'] = 'unavailable'
    r['quantities']['kon']['value'] = None
    assert status(r, 'kinetic_consistency') == 'unknown'
    r['quantities']['kd_steady_state']['status'] = 'unavailable'
    r['quantities']['kd_steady_state']['value'] = None
    assert status(r, 'steady_state_vs_kinetic') == 'unknown'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    assert status(r, 'steady_state_vs_kinetic') == 'not_applicable'
