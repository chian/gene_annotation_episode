"""BLI grader: each criterion's rule on records, with the arithmetic worked by hand."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bli_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_grader import CRITERIA, grade_bli
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.bli_cases import sparse_record, synthetic_record


def status(record, criterion):
    """The status after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_bli(record), criterion)['status']


def grader_status(record, criterion):
    return grade_bli(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_bli(record)['reasons'][criterion]


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_the_recorded_facts():
    graded = grade_bli(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 12
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == {'loading_and_response', 'concentration_series', 'fit_model', 'dissociation_window', 'replicates', 'kinetic_consistency', 'steady_state_vs_kinetic'}
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'}
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['loading_level_nm'] == 1.0 and native['response_max_nm'] == 0.8 and native['fit_r_squared'] == 0.99 and native['replicate_count'] == 3
    assert native['kd_nM'] == 20.0 and graded['experiment_type'] == 'bli'
    # koff / kon = 2.0e-3 / 1.0e5 = 2.0e-8 M = 20 nM
    assert native['kd_from_rates_nM'] == pytest.approx(20.0)
    # decayed fraction = 1 - exp(-2.0e-3 x 600) = 1 - exp(-1.2)
    assert native['dissociation_decay'] == pytest.approx(1 - math.exp(-1.2)) and native['dissociation_time_s'] == 600.0
    assert native['concentration_count'] == 6 and native['concentration_low_over_kd'] == pytest.approx(0.1) and native['concentration_high_over_kd'] == pytest.approx(30.0)
    assert native['biosensor_type'] == 'streptavidin'


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_bli(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['criteria']['dissociation_window']['status'] == 'unknown' and graded['native']['kd_nM'] == 20.0


def test_reference_subtraction():
    r = synthetic_record()
    r['facts']['buffer_reference_subtracted'] = fact('unknown')
    assert status(r, 'reference_subtraction') == 'supported'
    r['facts']['reference_sensor_subtracted'] = fact('no')
    assert status(r, 'reference_subtraction') == 'conflicting' and reason(r, 'reference_subtraction') == 'fact_answered_no'
    r['facts']['reference_sensor_subtracted'] = fact('unknown')
    assert status(r, 'reference_subtraction') == 'unknown'
    for name in ('reference_sensor_subtracted', 'buffer_reference_subtracted'):
        r['facts'][name] = fact('not_applicable')
    assert status(r, 'reference_subtraction') == 'not_applicable'


def test_nonspecific_binding_control_is_the_one_fact():
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('unknown', 'unknown'), ('not_applicable', 'not_applicable')):
        r['facts']['nonspecific_binding_checked'] = fact(answer, ['s'])
        assert status(r, 'nonspecific_binding_control') == expected


def test_baseline_and_regeneration():
    r = synthetic_record()
    r['facts']['regeneration'] = fact('not_applicable')
    assert status(r, 'baseline_and_regeneration') == 'supported'
    r['facts']['regeneration'] = fact('unknown')
    assert status(r, 'baseline_and_regeneration') == 'unknown'
    r['facts']['baseline_stable'] = fact('no')
    assert status(r, 'baseline_and_regeneration') == 'conflicting'


def test_loading_and_response():
    r = synthetic_record()
    r['quantities']['loading_level'] = point(5.0, 'nm', 'l', ['s'])        # far above 2.0 nm: a saturated sensor
    assert reason(r, 'loading_and_response') == 'loading_and_response_recorded_for_the_sheet' and grade_bli(r)['native']['loading_level_nm'] == 5.0
    assert grader_status(r, 'loading_and_response') == 'unknown' and status(r, 'loading_and_response') == 'conflicting'
    r['quantities']['loading_level'] = point(2.0, 'nm', 'l', ['s'])        # exactly the maximum is allowed
    assert status(r, 'loading_and_response') == 'supported'
    r['quantities']['response_max'] = point(0.02, 'nm', 'r', ['s'])        # below 0.05 nm but above the zero limit: a degree, no conflict
    assert status(r, 'loading_and_response') == 'supported'
    r['quantities']['response_max'] = point(0.005, 'nm', 'r', ['s'])       # below the noise level
    assert status(r, 'loading_and_response') == 'conflicting'
    r = synthetic_record()
    r['facts']['loading_step_documented'] = fact('no')
    assert grader_status(r, 'loading_and_response') == 'conflicting' and reason(r, 'loading_and_response') == 'loading_step_not_documented'
    r['facts']['loading_step_documented'] = fact('unknown')
    assert status(r, 'loading_and_response') == 'unknown' and reason(r, 'loading_and_response') == 'loading_and_response_recorded_for_the_sheet'
    r = synthetic_record()
    r['quantities']['response_max'] = {**r['quantities']['response_max'], 'status': 'unavailable', 'value': None}
    assert status(r, 'loading_and_response') == 'unknown' and grade_bli(r)['native']['response_max_nm'] is None
    r['quantities']['loading_level'] = {**r['quantities']['loading_level'], 'status': 'unavailable', 'value': None}
    assert grader_status(r, 'loading_and_response') == 'unknown' and reason(r, 'loading_and_response') == 'loading_or_response_missing'


def test_concentration_series():
    r = synthetic_record()
    r['concentration_series']['value'] = [2.0, 20.0, 200.0, 600.0]            # four: one fewer than five, partial credit (no longer a conflict)
    assert reason(r, 'concentration_series') == 'concentration_series_recorded_for_the_sheet' and grade_bli(r)['native']['concentration_count'] == 4
    assert grader_status(r, 'concentration_series') == 'unknown' and status(r, 'concentration_series') == 'supported' and 0 < _criterion(grade_bli(r), 'concentration_series')['degree'] < 1
    r['concentration_series']['value'] = [20.0]                                # one concentration: no series at all
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [30.0, 40.0, 60.0, 100.0, 200.0]     # lowest 1.5 x KD, above the zero limit
    assert grade_bli(r)['native']['concentration_low_over_kd'] == pytest.approx(1.5) and status(r, 'concentration_series') == 'supported'      # a kinetic (1:1) fit: gentle low end, never conflicting
    r['fit_model'] = 'steady_state'
    assert status(r, 'concentration_series') == 'conflicting'                 # an isotherm needs its lower arm: past the zero limit
    r['fit_model'] = '1:1'
    r['concentration_series']['value'] = [0.002, 0.006, 0.02, 0.06, 0.2, 0.6]  # in uM: the same series as nM values
    r['concentration_series']['unit'] = 'uM'
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert status(r, 'concentration_series') == 'unknown'


def test_fit_model():
    r = synthetic_record()
    r['facts']['analyte_bivalent_or_oligomeric'] = fact('yes', ['s'])
    assert reason(r, 'fit_model') == 'one_to_one_model_for_bivalent_or_oligomeric_analyte'
    r['fit_model'] = '2:1_bivalent_analyte'
    assert status(r, 'fit_model') == 'supported'
    r['quantities']['fit_r_squared'] = point(0.90, 'dimensionless', 'r2', ['s'])      # below 0.95 but above the zero limit: a degree, no conflict
    assert reason(r, 'fit_model') == 'r_squared_recorded_for_the_sheet' and status(r, 'fit_model') == 'supported'
    r['quantities']['fit_r_squared'] = point(0.70, 'dimensionless', 'r2', ['s'])      # beyond the zero limit
    assert grader_status(r, 'fit_model') == 'unknown' and status(r, 'fit_model') == 'conflicting'
    r['quantities']['fit_r_squared'] = point(0.95, 'dimensionless', 'r2', ['s'])      # exactly the minimum is allowed
    assert status(r, 'fit_model') == 'supported'
    r['quantities']['fit_r_squared'] = {**r['quantities']['fit_r_squared'], 'status': 'unavailable', 'value': None}
    assert reason(r, 'fit_model') == 'no_fit_quality_evidence'
    r['fit_model'] = None
    assert reason(r, 'fit_model') == 'fit_model_not_stated'
    r = synthetic_record()
    r['facts']['analyte_bivalent_or_oligomeric'] = fact('unknown')
    assert status(r, 'fit_model') == 'unknown' and grade_bli(r)['native']['fit_bivalent_answer'] == 'unknown'      # the sheet keeps the 1:1 bivalence question


def test_avidity_and_mass_transport_either_consideration_is_enough():
    r = synthetic_record()
    r['facts']['mass_transport_considered'] = fact('no')
    assert status(r, 'avidity_and_mass_transport') == 'supported'
    r['facts']['avidity_rebinding_considered'] = fact('unknown')
    assert status(r, 'avidity_and_mass_transport') == 'conflicting'
    r['facts']['mass_transport_considered'] = fact('unknown')
    assert status(r, 'avidity_and_mass_transport') == 'unknown'


def test_dissociation_window():
    r = synthetic_record()
    # koff 2.0e-3 s^-1 over 10 s: 1 - exp(-0.02) = 0.0198, below 0.05 but above the zero limit 0.01: supported with a degree
    r['quantities']['dissociation_time'] = point(10.0, 's', 't', ['s'])
    assert status(r, 'dissociation_window') == 'supported' and reason(r, 'dissociation_window') == 'dissociation_decay_recorded_for_the_sheet'
    # over 2 s: 1 - exp(-0.004) = 0.004, below the zero limit: koff is not measured at all
    r['quantities']['dissociation_time'] = point(2.0, 's', 't', ['s'])
    assert grader_status(r, 'dissociation_window') == 'unknown' and status(r, 'dissociation_window') == 'conflicting'
    # the same window written as 0.5 min = 30 s: 1 - exp(-0.06) = 0.0582, at least 0.05
    r['quantities']['dissociation_time'] = point(0.5, 'min', 't', ['s'])
    assert status(r, 'dissociation_window') == 'supported'
    assert grade_bli(r)['native']['dissociation_time_s'] == 30.0 and grade_bli(r)['native']['dissociation_decay'] == pytest.approx(1 - math.exp(-0.06))
    r['quantities']['dissociation_time'] = {**r['quantities']['dissociation_time'], 'status': 'unavailable', 'value': None}
    assert status(r, 'dissociation_window') == 'unknown'


def test_replicates():
    r = synthetic_record()
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported' and grader_status(r, 'replicates') == 'unknown'      # the count is judged on the sheet side: one fewer than three, partial credit (no longer a conflict)
    assert 0 < _criterion(grade_bli(r), 'replicates')['degree'] < 1
    r['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported' and 0 < _criterion(grade_bli(r), 'replicates')['degree'] < 1      # n >= 1 is never conflicting (rule 1): precision sqrt(1/3)
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported'
    r['facts']['independent_sensors'] = fact('no')
    assert grader_status(r, 'replicates') == 'conflicting' and reason(r, 'replicates') == 'replicates_not_independent'
    r['facts']['independent_sensors'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown'


def test_immobilized_activity():
    r = synthetic_record()
    r['facts']['immobilized_partner_active'] = fact('no')
    assert status(r, 'immobilized_activity') == 'conflicting'


def test_kinetic_consistency():
    r = synthetic_record()
    r['quantities']['koff'] = point(2.4e-3, 's^-1', 'k', ['s'])    # koff / kon = 24 nM, 20 % above 20 nM: on the limit, allowed
    assert status(r, 'kinetic_consistency') == 'supported'
    r['quantities']['koff'] = point(2.5e-3, 's^-1', 'k', ['s'])    # 25 nM: 25 % above, short of the zero limit: a degree, no conflict
    assert reason(r, 'kinetic_consistency') == 'kd_from_rates_recorded_for_the_sheet' and grade_bli(r)['native']['kd_from_rates_nM'] == pytest.approx(25.0)
    assert status(r, 'kinetic_consistency') == 'supported'
    r['quantities']['koff'] = point(4.0e-3, 's^-1', 'k', ['s'])    # 40 nM: 100 % above
    assert grader_status(r, 'kinetic_consistency') == 'unknown' and status(r, 'kinetic_consistency') == 'conflicting'
    r['quantities']['kon'] = {**r['quantities']['kon'], 'status': 'unavailable', 'value': None}
    assert status(r, 'kinetic_consistency') == 'unknown'


def test_steady_state_vs_kinetic():
    r = synthetic_record()
    r['quantities']['kd_steady_state'] = point(41.0, 'nM', 's', ['s'])       # ratio 2.05: short of the zero limit, a degree and no conflict
    assert grade_bli(r)['native']['steady_kinetic_fold'] == pytest.approx(2.05) and reason(r, 'steady_state_vs_kinetic') == 'estimate_fold_recorded_for_the_sheet'
    assert status(r, 'steady_state_vs_kinetic') == 'supported'
    r['quantities']['kd_steady_state'] = point(400.0, 'nM', 's', ['s'])      # twentyfold
    assert grader_status(r, 'steady_state_vs_kinetic') == 'unknown' and status(r, 'steady_state_vs_kinetic') == 'conflicting'
    r['quantities']['kd_steady_state'] = point(0.04, 'uM', 's', ['s'])       # 40 nM, ratio exactly 2: allowed
    assert status(r, 'steady_state_vs_kinetic') == 'supported'
    r['quantities']['kd_steady_state'] = {**r['quantities']['kd_steady_state'], 'status': 'unavailable', 'value': None}
    assert status(r, 'steady_state_vs_kinetic') == 'unknown'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    assert status(r, 'steady_state_vs_kinetic') == 'not_applicable'
