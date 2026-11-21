"""ITC grader: each criterion's rule on real records, with the arithmetic worked by hand."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_itc_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_grader import CRITERIA, grade_itc
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import sparse_record, synthetic_record


def status(record, criterion):
    """The status after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_itc(record), criterion)['status']


def grader_status(record, criterion):
    return grade_itc(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_itc(record)['reasons'][criterion]


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_the_recorded_facts():
    graded = grade_itc(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == {'concentration_accuracy_and_active_fraction', 'c_value_window', 'injections_sufficient', 'temperature_stated_and_controlled', 'replicate_titrations_independent', 'stoichiometry_consistency', 'thermodynamic_consistency'}
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'}
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['injection_count'] == 20 and native['replicate_count'] == 3 and native['stoichiometry_n'] == 1.0 and native['n_over_expected'] == 1.0
    assert native['kd_nM'] == 20.0
    # c = n x [cell] / KD = 1.0 x 10 uM (10000 nM) / 20 nM = 500
    assert native['c_value'] == pytest.approx(500.0)
    # dG from KD = R T ln(KD in M) = 8.314462618 x 298.15 x ln(20e-9) / 1000 = -43.948 kJ/mol
    assert native['dg_from_kd_kJ_per_mol'] == pytest.approx(-43.948, abs=0.01)
    # dG from parts = dH - T dS = -50 - 298.15 x (-20.3) / 1000 = -43.948 kJ/mol
    assert native['dg_from_parts_kJ_per_mol'] == pytest.approx(-43.948, abs=0.01)
    assert native['dg_gap_kJ_per_mol'] == pytest.approx(0.0, abs=0.01)


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_itc(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['criteria']['thermodynamic_consistency']['status'] == 'unknown'
    assert graded['native']['kd_nM'] == 20.0 and graded['native']['c_value'] is None


def test_heat_of_dilution_control():
    r = synthetic_record()
    r['facts']['baseline_corrected'] = fact('unknown')
    assert status(r, 'heat_of_dilution_control') == 'unknown'
    r['facts']['dilution_control_performed'] = fact('no')
    assert status(r, 'heat_of_dilution_control') == 'conflicting'
    assert reason(r, 'heat_of_dilution_control') == 'fact_answered_no'
    r = synthetic_record()
    for name in ('dilution_control_performed', 'dilution_control_subtracted', 'baseline_corrected'):
        r['facts'][name] = fact('not_applicable')
    assert status(r, 'heat_of_dilution_control') == 'not_applicable'


def test_concentration_accuracy_and_active_fraction():
    r = synthetic_record()
    # n 0.25 / expected 1.0 = 0.25, beyond the sheet's zero limit: an inactive fraction or a concentration error
    r['quantities']['stoichiometry'] = point(0.25, 'dimensionless', 'n', ['s'])
    assert grade_itc(r)['native']['n_over_expected'] == 0.25 and reason(r, 'concentration_accuracy_and_active_fraction') == 'n_over_expected_recorded_for_the_sheet'
    assert grader_status(r, 'concentration_accuracy_and_active_fraction') == 'unknown'
    assert status(r, 'concentration_accuracy_and_active_fraction') == 'conflicting'
    r['quantities']['stoichiometry'] = point(2.2, 'dimensionless', 'n', ['s'])
    assert status(r, 'concentration_accuracy_and_active_fraction') == 'conflicting'
    r['quantities']['stoichiometry'] = point(1.4, 'dimensionless', 'n', ['s'])
    assert status(r, 'concentration_accuracy_and_active_fraction') == 'supported'          # beyond the full limit, short of the zero limit: a degree, no conflict
    r['quantities']['stoichiometry'] = point(0.8, 'dimensionless', 'n', ['s'])
    assert status(r, 'concentration_accuracy_and_active_fraction') == 'supported'
    r['facts']['active_fraction_determined'] = fact('no')
    assert grader_status(r, 'concentration_accuracy_and_active_fraction') == 'conflicting' and reason(r, 'concentration_accuracy_and_active_fraction') == 'fact_answered_no'
    r['facts']['active_fraction_determined'] = fact('unknown')
    assert status(r, 'concentration_accuracy_and_active_fraction') == 'unknown'
    r = synthetic_record()
    r['quantities']['expected_stoichiometry']['status'] = 'unavailable'
    r['quantities']['expected_stoichiometry']['value'] = None
    assert reason(r, 'concentration_accuracy_and_active_fraction') == 'n_or_expected_stoichiometry_missing'


def test_c_value_window():
    r = synthetic_record()
    # c = 1.0 x 1 nM / 20 nM = 0.05, below the sheet's zero limit
    r['quantities']['cell_concentration'] = point(1.0, 'nM', 'cell', ['s'])
    assert grade_itc(r)['native']['c_value'] == pytest.approx(0.05) and reason(r, 'c_value_window') == 'c_value_recorded_for_the_sheet'
    assert grader_status(r, 'c_value_window') == 'unknown' and status(r, 'c_value_window') == 'conflicting'
    # c = 1.0 x 20 nM / 20 nM = 1: the lower end is inside the window
    r['quantities']['cell_concentration'] = point(20.0, 'nM', 'cell', ['s'])
    assert status(r, 'c_value_window') == 'supported'
    # c = 1.0 x 100 uM (100000 nM) / 20 nM = 5000, above 1000 but short of the zero limit
    r['quantities']['cell_concentration'] = point(100.0, 'uM', 'cell', ['s'])
    assert grade_itc(r)['native']['c_value'] == pytest.approx(5000.0) and status(r, 'c_value_window') == 'supported'
    r['quantities']['cell_concentration'] = point(500.0, 'uM', 'cell', ['s'])                 # c = 25000
    assert status(r, 'c_value_window') == 'conflicting'
    r['quantities']['cell_concentration']['value'] = None
    r['quantities']['cell_concentration']['status'] = 'unavailable'
    assert status(r, 'c_value_window') == 'unknown'


def test_fit_model_appropriate():
    r = synthetic_record()
    r['facts']['binding_sites_heterogeneous'] = fact('yes')
    assert status(r, 'fit_model_appropriate') == 'conflicting'
    r['fit_model'] = 'two_sets_of_sites'
    assert status(r, 'fit_model_appropriate') == 'supported'
    r = synthetic_record()
    r['facts']['residuals_reported'] = fact('no')
    assert reason(r, 'fit_model_appropriate') == 'no_residual_evidence'
    r = synthetic_record()
    r['facts']['binding_sites_heterogeneous'] = fact('unknown')
    assert status(r, 'fit_model_appropriate') == 'unknown'
    r['fit_model'] = None
    assert reason(r, 'fit_model_appropriate') == 'fit_model_not_stated'


def test_injections_sufficient():
    r = synthetic_record()
    r['quantities']['injection_count'] = point(14, 'count', 'inj', ['s'])
    assert status(r, 'injections_sufficient') == 'supported'                                # one short of the researched 15: partial credit, no conflict
    assert _criterion(grade_itc(r), 'injections_sufficient')['degree'] == pytest.approx((11 / 12) ** 0.5)
    r['quantities']['injection_count'] = point(3, 'count', 'inj', ['s'])
    assert status(r, 'injections_sufficient') == 'supported' and _criterion(grade_itc(r), 'injections_sufficient')['degree'] == 0.0      # as many points as fitted parameters: no credit, but a short run is weaker evidence, never conflicting
    r['quantities']['injection_count'] = point(15, 'count', 'inj', ['s'])
    assert status(r, 'injections_sufficient') == 'supported'
    r['quantities']['injection_count']['status'] = 'unavailable'
    r['quantities']['injection_count']['value'] = None
    assert status(r, 'injections_sufficient') == 'unknown'


def test_buffer_matching():
    r = synthetic_record()
    r['facts']['buffer_matching'] = fact('matched_by_stated_procedure', ['s'])
    assert status(r, 'buffer_matching') == 'supported'
    r['facts']['buffer_matching'] = fact('not_matched', ['s'])
    assert status(r, 'buffer_matching') == 'conflicting'
    r['facts']['buffer_matching'] = fact('unknown')
    assert status(r, 'buffer_matching') == 'unknown'


def test_temperature_stated_and_controlled():
    r = synthetic_record()
    r['quantities']['temperature'] = point(25.0, 'C', 't', ['s'])
    assert grade_itc(r)['native']['temperature_K'] == pytest.approx(298.15)
    assert status(r, 'temperature_stated_and_controlled') == 'supported'
    r['quantities']['temperature'] = point(350.0, 'K', 't', ['s'])
    assert reason(r, 'temperature_stated_and_controlled') == 'temperature_recorded_for_the_sheet' and grade_itc(r)['native']['temperature_K'] == 350.0
    # 350 K (76.85 C) is past the usual 50 C, short of the 80 C instrument limit: little credit, no conflict
    assert status(r, 'temperature_stated_and_controlled') == 'supported'
    assert _criterion(grade_itc(r), 'temperature_stated_and_controlled')['degree'] == pytest.approx((353.15 - 350.0) / 30.0)
    r['quantities']['temperature'] = point(90.0, 'C', 't', ['s'])
    assert status(r, 'temperature_stated_and_controlled') == 'conflicting'
    r['quantities']['temperature'] = point(6.0, 'C', 't', ['s'])
    assert status(r, 'temperature_stated_and_controlled') == 'supported'
    r = synthetic_record()
    r['facts']['temperature_controlled'] = fact('no')
    assert grader_status(r, 'temperature_stated_and_controlled') == 'conflicting' and reason(r, 'temperature_stated_and_controlled') == 'fact_answered_no'
    r['facts']['temperature_controlled'] = fact('not_applicable')
    assert status(r, 'temperature_stated_and_controlled') == 'not_applicable'
    r['facts']['temperature_controlled'] = fact('unknown')
    assert status(r, 'temperature_stated_and_controlled') == 'unknown'
    r['quantities']['temperature']['status'] = 'unavailable'
    r['quantities']['temperature']['value'] = None
    assert reason(r, 'temperature_stated_and_controlled') == 'temperature_not_stated'


def test_replicate_titrations_independent():
    r = synthetic_record()
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert status(r, 'replicate_titrations_independent') == 'supported'                     # one short of the researched 3: partial credit, no conflict
    assert _criterion(grade_itc(r), 'replicate_titrations_independent')['degree'] == pytest.approx((2 / 3) ** 0.5)
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    r['facts']['independent_titrations'] = fact('no')
    assert grader_status(r, 'replicate_titrations_independent') == 'conflicting' and reason(r, 'replicate_titrations_independent') == 'replicates_not_independent'
    r['facts']['independent_titrations'] = fact('unknown')
    assert status(r, 'replicate_titrations_independent') == 'unknown'
    r['facts']['independent_titrations'] = fact('yes', ['s'])
    assert status(r, 'replicate_titrations_independent') == 'supported'


def test_stoichiometry_consistency():
    r = synthetic_record()
    # expected n stated (1.0): the deviation is judged once, in concentration_accuracy_and_active_fraction; here only the free fit is asked
    for n in (1.1, 0.5, 2.0, 1.25, 0.2):
        r['quantities']['stoichiometry'] = point(n, 'dimensionless', 'n', ['s'])
        assert status(r, 'stoichiometry_consistency') == 'supported', n
    # no expected n: the fallback grid; 1.25 is exactly between two halves (degree 0, never conflicting), 0.2 is at the size floor (conflicting)
    r['quantities']['expected_stoichiometry']['status'] = 'unavailable'
    r['quantities']['expected_stoichiometry']['value'] = None
    for n, expected in ((1.1, 'supported'), (0.5, 'supported'), (2.0, 'supported'), (1.25, 'supported'), (0.2, 'conflicting')):
        r['quantities']['stoichiometry'] = point(n, 'dimensionless', 'n', ['s'])
        assert status(r, 'stoichiometry_consistency') == expected, n
    assert reason(r, 'stoichiometry_consistency') == 'stoichiometry_recorded_for_the_sheet' and grade_itc(r)['native']['stoichiometry_n'] == 0.2
    r['quantities']['stoichiometry'] = point(1.0, 'dimensionless', 'n', ['s'])
    r['facts']['n_fitted_freely'] = fact('no')
    assert reason(r, 'stoichiometry_consistency') == 'stoichiometry_was_fixed'
    r['facts']['n_fitted_freely'] = fact('unknown')
    assert status(r, 'stoichiometry_consistency') == 'unknown'


def test_thermodynamic_consistency():
    r = synthetic_record()
    # dS +50 J/mol/K: dG from parts = -50 - 298.15 x 50 / 1000 = -64.91, gap to -43.95 is 20.96 kJ/mol
    r['quantities']['entropy'] = point(50.0, 'J/mol/K', 's', ['s'])
    assert status(r, 'thermodynamic_consistency') == 'conflicting' and reason(r, 'thermodynamic_consistency') == 'free_energy_gap_recorded_for_the_sheet'
    assert grade_itc(r)['native']['dg_gap_kJ_per_mol'] == pytest.approx(20.96, abs=0.01)
    # unit conversion: -11.95 kcal/mol = -50.0 kJ/mol, -4.85 cal/mol/K = -20.29 J/mol/K
    r['quantities']['enthalpy'] = point(-11.95, 'kcal/mol', 'h', ['s'])
    r['quantities']['entropy'] = point(-4.85, 'cal/mol/K', 's', ['s'])
    assert status(r, 'thermodynamic_consistency') == 'supported'
    # entropy not given: the check cannot be made
    r['quantities']['entropy']['status'] = 'unavailable'
    r['quantities']['entropy']['value'] = None
    assert status(r, 'thermodynamic_consistency') == 'not_applicable'
    r['quantities']['enthalpy']['status'] = 'unavailable'
    r['quantities']['enthalpy']['value'] = None
    assert status(r, 'thermodynamic_consistency') == 'unknown'


def test_the_published_hsp90_hop_case_decides_only_what_its_legend_supports():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.itc_cases import hsp90_hop_record
    graded = grade_itc(hsp90_hop_record())
    statuses = {name: _criterion(graded, name)['status'] for name in CRITERIA}      # as the sheet judges what the grader recorded
    assert graded['native']['kd_nM'] == pytest.approx(578.0)
    assert statuses['replicate_titrations_independent'] == 'supported'      # three independent experiments
    assert statuses['stoichiometry_consistency'] == 'unknown'               # n = 0.544 is simple, but the legend does not say n was free
    assert graded['reasons']['stoichiometry_consistency'] == 'stoichiometry_recorded_for_the_sheet' and graded['native']['stoichiometry_free'] == 'unknown'
    assert statuses['fit_model_appropriate'] == 'unknown' and graded['reasons']['fit_model_appropriate'] == 'no_residual_evidence'
    assert statuses['c_value_window'] == 'unknown'                          # no cell concentration in the legend
    assert statuses['thermodynamic_consistency'] == 'unknown'               # the signs of dH and -T dS, not values
    assert 'conflicting' not in statuses.values()


def test_the_final_ratio_gives_the_final_ligand_over_kd_and_the_mode_and_ionization_answers_are_recorded():
    r = synthetic_record()                                                                     # c = 500, n 1.0
    r['quantities']['final_molar_ratio'] = point(2.0, 'dimensionless', 'r', ['s_r'])
    native = grade_itc(r)['native']
    assert native['final_ligand_over_kd'] == pytest.approx(1000.0) and native['final_ratio_refs'] == ['s_r']      # r c / n = 2.0 x 500 / 1.0
    assert native['c_value_refs'] == ['span_exp_synthetic_itc_1']                              # the ratio is not part of c
    assert grade_itc(synthetic_record())['native']['final_ligand_over_kd'] is None
    assert grade_itc(r)['native']['titration_mode'] == 'incremental' and grade_itc(r)['native']['enthalpy_ionization_corrected'] == 'no'


def test_a_stated_single_injection_or_continuous_mode_is_recorded_instead_of_the_count():
    r = synthetic_record()
    for mode in ('single_injection', 'continuous'):
        r['titration_mode'] = mode
        assert reason(r, 'injections_sufficient') == 'titration_mode_recorded_for_the_sheet' and grader_status(r, 'injections_sufficient') == 'unknown'
        assert grade_itc(r)['native']['titration_mode'] == mode
    r['titration_mode'] = 'incremental'
    assert reason(r, 'injections_sufficient') == 'injection_count_recorded_for_the_sheet'
    r['titration_mode'] = None
    assert reason(r, 'injections_sufficient') == 'injection_count_recorded_for_the_sheet'


def test_the_ionization_answer_is_recorded_beside_the_free_energy_gap():
    r = synthetic_record()
    for answer in ('yes', 'no', 'unknown'):
        r['facts']['enthalpy_buffer_ionization_corrected'] = fact(answer, ['s'])
        assert grade_itc(r)['native']['enthalpy_ionization_corrected'] == answer and reason(r, 'thermodynamic_consistency') == 'free_energy_gap_recorded_for_the_sheet'
