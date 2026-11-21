"""GCI grader: each criterion's rule on records, with the arithmetic worked by hand."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_gci_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_grader import CRITERIA, grade_gci
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.gci_cases import sparse_record, synthetic_record


def status(record, criterion):
    """The status after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_gci(record), criterion)['status']


def grader_status(record, criterion):
    return grade_gci(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_gci(record)['reasons'][criterion]


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_the_recorded_facts():
    graded = grade_gci(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 14
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == {'surface_level_and_response', 'rmax_consistency', 'concentration_series', 'dissociation_window', 'replicates', 'kinetic_consistency', 'steady_state_vs_kinetic'}
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'}
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['pulse_kinetics'] is False and native['replicate_count'] == 3 and native['steady_kinetic_fold'] == pytest.approx(1.5)
    assert native['kd_nM'] == 20.0 and graded['experiment_type'] == 'gci'
    # koff / kon = 2.0e-3 / 1.0e5 = 2.0e-8 M = 20 nM
    assert native['kd_from_rates_nM'] == pytest.approx(20.0)
    assert native['immobilization_level_pg_mm2'] == 500.0 and native['response_max_pg_mm2'] == 40.0
    assert native['concentration_count'] == 6 and native['concentration_low_over_kd'] == pytest.approx(0.1) and native['concentration_high_over_kd'] == pytest.approx(30.0)
    assert native['chip_type'] == 'streptavidin'
    # theoretical maximum response 20 / 100 x 500 x 1 = 100 pg/mm2, observed 40: ratio 0.4; decay 1 - exp(-2.0e-3 x 600)
    assert native['rmax_theoretical_pg_mm2'] == pytest.approx(100.0) and native['rmax_ratio'] == pytest.approx(0.4)
    assert native['dissociation_time_s'] == 600.0 and native['dissociation_decay'] == pytest.approx(1 - math.exp(-1.2)) and native['dissociation_response_pg_mm2'] == 40.0


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_gci(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['criteria']['surface_level_and_response']['status'] == 'unknown' and graded['native']['kd_nM'] == 20.0


def test_reference_subtraction_either_is_enough():
    r = synthetic_record()
    r['facts']['double_referenced'] = fact('unknown')
    assert status(r, 'reference_subtraction') == 'supported'
    r['facts']['reference_channel_subtracted'] = fact('no')
    assert status(r, 'reference_subtraction') == 'conflicting' and reason(r, 'reference_subtraction') == 'fact_answered_no'
    r['facts']['reference_channel_subtracted'] = fact('unknown')
    assert status(r, 'reference_subtraction') == 'unknown'
    for name in ('reference_channel_subtracted', 'double_referenced'):
        r['facts'][name] = fact('not_applicable')
    assert status(r, 'reference_subtraction') == 'not_applicable'


@pytest.mark.parametrize('criterion, fact_name', [('bulk_solvent_correction', 'bulk_solvent_corrected'), ('nonspecific_binding_control', 'nonspecific_binding_checked'), ('mass_transport', 'mass_transport_checked'), ('immobilized_activity', 'immobilized_partner_active')])
def test_single_fact_criteria_are_the_one_fact(criterion, fact_name):
    r = synthetic_record()
    for answer, expected in (('yes', 'supported'), ('no', 'conflicting'), ('unknown', 'unknown'), ('not_applicable', 'not_applicable')):
        r['facts'][fact_name] = fact(answer, ['s'])
        assert status(r, criterion) == expected


def test_baseline_and_regeneration():
    r = synthetic_record()
    r['facts']['regeneration'] = fact('not_applicable')
    assert status(r, 'baseline_and_regeneration') == 'supported'
    r['facts']['regeneration'] = fact('unknown')
    assert status(r, 'baseline_and_regeneration') == 'unknown'
    r['facts']['baseline_stable'] = fact('no')
    assert status(r, 'baseline_and_regeneration') == 'conflicting'


def test_surface_level_and_response():
    r = synthetic_record()
    r['quantities']['immobilization_level'] = point(5000.0, 'pg/mm2', 'l', ['s'])     # far above 2000 pg/mm2: a saturated surface
    assert reason(r, 'surface_level_and_response') == 'surface_level_and_response_recorded_for_the_sheet' and grader_status(r, 'surface_level_and_response') == 'unknown'
    assert status(r, 'surface_level_and_response') == 'supported' and _criterion(grade_gci(r), 'surface_level_and_response')['degree'] == 0.0      # a dense surface: no credit, never conflicting (range review)
    r['quantities']['immobilization_level'] = point(2.0, 'ng/mm2', 'l', ['s'])        # 2 ng/mm2 = 2000 pg/mm2: exactly the maximum is allowed
    assert status(r, 'surface_level_and_response') == 'supported' and grade_gci(r)['native']['immobilization_level_pg_mm2'] == 2000.0
    r['quantities']['immobilization_level'] = point(2.5, 'ng/mm2', 'l', ['s'])        # 2500 pg/mm2: above the full limit, short of the zero limit
    assert status(r, 'surface_level_and_response') == 'supported'
    r['quantities']['immobilization_level'] = point(4100.0, 'RU', 'l', ['s'])         # 1 RU = 1 pg/mm2
    assert grade_gci(r)['native']['immobilization_level_pg_mm2'] == 4100.0 and status(r, 'surface_level_and_response') == 'supported'
    r['quantities']['immobilization_level'] = point(500.0, 'RU', 'l', ['s'])
    r['quantities']['response_max'] = point(0.5, 'pg/mm2', 'r', ['s'])                # below 1 pg/mm2 but above the noise: a degree, no conflict
    assert status(r, 'surface_level_and_response') == 'supported'
    r['quantities']['response_max'] = point(0.05, 'pg/mm2', 'r', ['s'])               # below the noise
    assert status(r, 'surface_level_and_response') == 'conflicting'
    r['quantities']['response_max'] = point(0.001, 'ng/mm2', 'r', ['s'])              # 1 pg/mm2: exactly the minimum is allowed
    assert status(r, 'surface_level_and_response') == 'supported'
    r['quantities']['response_max'] = {**r['quantities']['response_max'], 'status': 'unavailable', 'value': None}
    assert status(r, 'surface_level_and_response') == 'unknown' and reason(r, 'surface_level_and_response') == 'surface_level_and_response_recorded_for_the_sheet'
    r['quantities']['immobilization_level'] = {**r['quantities']['immobilization_level'], 'status': 'unavailable', 'value': None}
    assert status(r, 'surface_level_and_response') == 'unknown' and reason(r, 'surface_level_and_response') == 'level_or_response_missing'


def test_concentration_series_titration():
    r = synthetic_record()
    r['concentration_series']['value'] = [2.0, 20.0, 200.0, 600.0]            # four: one short of five, partial credit on the concave curve 1 - (1/4)^2, no conflict
    assert reason(r, 'concentration_series') == 'concentration_series_recorded_for_the_sheet' and grade_gci(r)['native']['concentration_count'] == 4
    assert status(r, 'concentration_series') == 'supported' and _criterion(grade_gci(r), 'concentration_series')['degree'] == pytest.approx(0.9375)
    r['concentration_series']['value'] = [30.0, 40.0, 60.0, 100.0, 200.0]     # lowest 1.5 x KD, beyond the zero limit
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [2.0, 6.0, 20.0, 60.0, 80.0]         # highest 4 x KD, below 5 x KD but above the zero limit: a degree, no conflict
    assert grade_gci(r)['native']['concentration_high_over_kd'] == pytest.approx(4.0) and status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = [2.0, 6.0, 10.0, 15.0, 20.0]         # highest at the KD
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [0.002, 0.006, 0.02, 0.06, 0.2, 0.6]  # in uM: the same series as nM values
    r['concentration_series']['unit'] = 'uM'
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = [2000.0, 6000.0, 20000.0, 60000.0, 200000.0]   # in pM: 2 to 200 nM against KD 20 nM (0.1 x to 10 x)
    r['concentration_series']['unit'] = 'pM'
    assert status(r, 'concentration_series') == 'supported' and grade_gci(r)['native']['concentration_high_over_kd'] == pytest.approx(10.0)
    r['concentration_series'] = {**r['concentration_series'], 'value': None, 'status': 'unavailable'}
    assert status(r, 'concentration_series') == 'unknown'


def test_concentration_series_for_waverapid_is_one_concentration_high_enough():
    r = synthetic_record()
    r['facts']['repeated_pulse_kinetics_used'] = fact('yes', ['s'])
    r['concentration_series']['value'] = [200.0]                                # one concentration, 10 x KD: allowed for waveRAPID
    assert status(r, 'concentration_series') == 'supported' and reason(r, 'concentration_series') == 'concentration_series_recorded_for_the_sheet' and grade_gci(r)['native']['pulse_kinetics'] is True
    r['concentration_series']['value'] = [100.0]                                # exactly 5 x KD: allowed
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = [90.0]                                 # 4.5 x KD: above the zero limit, a degree and no conflict
    assert status(r, 'concentration_series') == 'supported'
    r['concentration_series']['value'] = [20.0]                                 # at the KD
    assert status(r, 'concentration_series') == 'conflicting'
    r['facts']['repeated_pulse_kinetics_used'] = fact('no')
    r['concentration_series']['value'] = [200.0]                                # the same single concentration is not a series (the zero end of the count curve)
    assert grade_gci(r)['native']['pulse_kinetics'] is False and status(r, 'concentration_series') == 'conflicting'


def test_fit_model():
    r = synthetic_record()
    r['facts']['analyte_bivalent_or_oligomeric'] = fact('yes', ['s'])
    assert reason(r, 'fit_model') == 'one_to_one_model_for_bivalent_or_oligomeric_analyte'
    r['fit_model'] = 'bivalent_analyte'
    assert status(r, 'fit_model') == 'supported' and reason(r, 'fit_model') == 'model_stated'
    r['fit_model'] = None
    assert reason(r, 'fit_model') == 'fit_model_not_stated'
    r = synthetic_record()
    r['facts']['analyte_bivalent_or_oligomeric'] = fact('unknown')
    assert reason(r, 'fit_model') == 'bivalence_or_oligomer_state_unknown_for_one_to_one_model'
    r['fit_model'] = 'heterogeneous_ligand'
    assert status(r, 'fit_model') == 'supported'


def test_replicates():
    r = synthetic_record()
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert grader_status(r, 'replicates') == 'unknown'      # the count is judged on the sheet side
    assert status(r, 'replicates') == 'supported' and _criterion(grade_gci(r), 'replicates')['degree'] == pytest.approx((2 / 3) ** 0.5)      # one short of three: partial credit, no conflict
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported'
    r['facts']['independent_channels_or_chips'] = fact('no')
    assert grader_status(r, 'replicates') == 'conflicting' and reason(r, 'replicates') == 'replicates_not_independent'
    r['facts']['independent_channels_or_chips'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown'


def test_kinetic_consistency():
    r = synthetic_record()
    r['quantities']['koff'] = point(2.4e-3, 's^-1', 'k', ['s'])    # koff / kon = 24 nM, 20 % above 20 nM: on the limit, allowed
    assert status(r, 'kinetic_consistency') == 'supported'
    r['quantities']['koff'] = point(2.5e-3, 's^-1', 'k', ['s'])    # 25 nM: 25 % above, short of the zero limit: a degree, no conflict
    assert reason(r, 'kinetic_consistency') == 'kd_from_rates_recorded_for_the_sheet' and grade_gci(r)['native']['kd_from_rates_nM'] == pytest.approx(25.0)
    assert status(r, 'kinetic_consistency') == 'supported'
    r['quantities']['koff'] = point(4.0e-3, 's^-1', 'k', ['s'])    # 40 nM: 100 % above
    assert grader_status(r, 'kinetic_consistency') == 'unknown' and status(r, 'kinetic_consistency') == 'conflicting'
    r['quantities']['kon'] = {**r['quantities']['kon'], 'status': 'unavailable', 'value': None}
    assert status(r, 'kinetic_consistency') == 'unknown'


def test_rmax_consistency_records_the_theoretical_maximum_response_and_the_sheet_judges_the_ratio():
    r = synthetic_record()                                                       # theoretical 100 pg/mm2, observed 40: ratio 0.4
    assert grader_status(r, 'rmax_consistency') == 'unknown' and reason(r, 'rmax_consistency') == 'rmax_ratio_recorded_for_the_sheet'
    assert status(r, 'rmax_consistency') == 'supported' and _criterion(grade_gci(r), 'rmax_consistency')['degree'] == 1.0
    r['quantities']['response_max'] = point(20.0, 'pg/mm2', 'r', ['s'])          # ratio 0.2: halfway down the ramp 0.3 -> 0.1
    assert _criterion(grade_gci(r), 'rmax_consistency')['degree'] == pytest.approx(0.5)
    r['quantities']['response_max'] = point(10.0, 'pg/mm2', 'r', ['s'])          # ratio 0.1: the zero end, conflicting
    assert status(r, 'rmax_consistency') == 'conflicting'
    r['quantities']['response_max'] = point(0.16, 'ng/mm2', 'r', ['s'])          # 160 pg/mm2, ratio 1.6: halfway down the ramp 1.2 -> 2.0
    assert grade_gci(r)['native']['rmax_ratio'] == pytest.approx(1.6) and _criterion(grade_gci(r), 'rmax_consistency')['degree'] == pytest.approx(0.5)
    r['quantities']['response_max'] = point(200.0, 'RU', 'r', ['s'])             # ratio 2.0: the zero end
    assert status(r, 'rmax_consistency') == 'conflicting'
    for name in ('analyte_mass', 'ligand_mass', 'stoichiometry', 'immobilization_level', 'response_max'):
        r = synthetic_record()
        r['quantities'][name] = {**r['quantities'][name], 'status': 'unavailable', 'value': None}
        assert status(r, 'rmax_consistency') == 'unknown' and reason(r, 'rmax_consistency') == 'rmax_operand_missing', name


def test_dissociation_window_records_the_decay_and_the_sheet_judges_it():
    r = synthetic_record()                                                       # koff 2.0e-3 s^-1, 600 s
    assert grader_status(r, 'dissociation_window') == 'unknown' and reason(r, 'dissociation_window') == 'dissociation_decay_recorded_for_the_sheet'
    assert status(r, 'dissociation_window') == 'supported' and _criterion(grade_gci(r), 'dissociation_window')['degree'] == 1.0
    r['quantities']['dissociation_time'] = point(10.0, 'min', 't', ['s'])        # minutes are read as seconds: 600 s
    assert grade_gci(r)['native']['dissociation_time_s'] == 600.0
    r['quantities']['dissociation_time'] = point(15.0, 's', 't', ['s'])          # decay 1 - exp(-0.03) = 0.0296: between 1 % and 5 %, a degree
    degree = _criterion(grade_gci(r), 'dissociation_window')['degree']
    assert degree == pytest.approx((1 - math.exp(-0.03) - 0.01) / 0.04) and 0 < degree < 1
    r['quantities']['dissociation_time'] = point(2.0, 's', 't', ['s'])           # decay 0.4 %: koff is not measured, conflicting
    assert status(r, 'dissociation_window') == 'conflicting'
    r = synthetic_record()
    r['quantities']['response_max'] = point(1.2, 'pg/mm2', 'r', ['s'])           # decay 0.699 x 1.2 = 0.84 pg/mm2 decayed signal: below the 1 pg/mm2 full-credit end, a degree
    degree = _criterion(grade_gci(r), 'dissociation_window')['degree']
    assert degree == pytest.approx((0.699 * 1.2 - 0.1) / 0.9, abs=1e-3) and 0 < degree < 1
    r = synthetic_record()
    r['quantities']['dissociation_time'] = {**r['quantities']['dissociation_time'], 'status': 'unavailable', 'value': None}
    assert status(r, 'dissociation_window') == 'unknown' and reason(r, 'dissociation_window') == 'koff_or_dissociation_time_missing'
    r = synthetic_record()
    r['quantities']['koff'] = {**r['quantities']['koff'], 'status': 'unavailable', 'value': None}
    assert reason(r, 'dissociation_window') == 'koff_or_dissociation_time_missing'


def test_a_picomolar_kd_is_read_in_nanomolar():
    r = synthetic_record(kd=0.094)       # KD 94 pM written as 0.094 nM
    r['quantities']['kd'] = point(94.0, 'pM', 'kd', ['s'])
    r['quantities']['kd_steady_state'] = point(0.1, 'nM', 's', ['s'])    # 100 pM against 94 pM: ratio 1.0638
    assert grade_gci(r)['native']['kd_nM'] == pytest.approx(0.094) and status(r, 'steady_state_vs_kinetic') == 'supported'
    r['quantities']['kd_steady_state'] = point(0.2, 'nM', 's', ['s'])    # 200 pM against 94 pM: ratio 2.128, short of the zero limit
    assert grade_gci(r)['native']['steady_kinetic_fold'] == pytest.approx(2.1277, abs=1e-3) and status(r, 'steady_state_vs_kinetic') == 'supported'
    r['quantities']['kd_steady_state'] = point(2.0, 'nM', 's', ['s'])    # 2000 pM against 94 pM: ratio 21
    assert status(r, 'steady_state_vs_kinetic') == 'conflicting'


def test_steady_state_vs_kinetic():
    r = synthetic_record()
    r['quantities']['kd_steady_state'] = point(41.0, 'nM', 's', ['s'])       # ratio 2.05: short of the zero limit, a degree and no conflict
    assert reason(r, 'steady_state_vs_kinetic') == 'estimate_fold_recorded_for_the_sheet' and status(r, 'steady_state_vs_kinetic') == 'supported'
    r['quantities']['kd_steady_state'] = point(400.0, 'nM', 's', ['s'])      # twentyfold
    assert grader_status(r, 'steady_state_vs_kinetic') == 'unknown' and status(r, 'steady_state_vs_kinetic') == 'conflicting'
    r['quantities']['kd_steady_state'] = point(0.04, 'uM', 's', ['s'])       # 40 nM, ratio exactly 2: allowed
    assert status(r, 'steady_state_vs_kinetic') == 'supported'
    r['quantities']['kd_steady_state'] = {**r['quantities']['kd_steady_state'], 'status': 'unavailable', 'value': None}
    assert status(r, 'steady_state_vs_kinetic') == 'unknown'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    assert status(r, 'steady_state_vs_kinetic') == 'not_applicable'
