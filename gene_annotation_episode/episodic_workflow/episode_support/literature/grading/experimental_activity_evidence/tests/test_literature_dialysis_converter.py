"""Dialysis converter: the quantitative effect and variance (a KD, else a Ki), the qualitative effect (no KD and no Ki), the criteria mapping and the null reasons."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dialysis_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_converter import CRITERIA_MAP, _criterion, convert_dialysis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_grader import CRITERIA, grade_dialysis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.dialysis_cases import low_binding_record, qualitative_record, sparse_record, synthetic_record

SHEET_CRITERIA = ('binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis')


def convert(record):
    return convert_dialysis(grade_dialysis(record))


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped)) == 15


def test_the_kd_is_the_effect_and_its_standard_error_squared_is_the_variance():
    converted = convert(synthetic_record())
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 200.0 and effect['unit'] == 'nM' and effect['measurement_keys'] == ['dialysis_kd:exp_synthetic_dialysis_1'] and effect['native_component'] == 'kd'
    variance = converted['extraction']['quantities']['effect_variance']
    assert variance['value'] == pytest.approx(400.0) and variance['unit'] == 'nM_squared' and variance['origin'] == 'derived'      # 20 nM squared
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(200.0) and cells['effect_variance']['value'] == pytest.approx(400.0) and cells['effect_precision']['value'] == pytest.approx(1 / 400.0)
    assert converted['extraction']['assay_type'] == 'ligand_binding' and converted['extraction']['quantity_kind'] == 'binding_parameter' and converted['experiment_type'] == 'dialysis'
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys((*SHEET_CRITERIA, 'variance_correspondence'), 'supported')
    assert all(item['support_refs'] for item in converted['extraction']['interpretations'].values())
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_ligand_a', 'immobilized_preparation_ref': 'prep_protein_a', 'surface_ref': None, 'dataset_ref': 'dataset_dialysis_1'}
    assert converted['null_components']['recovery'] == 'a_dialysis_recovery_is_a_mass_balance_not_a_matrix_recovery'
    assert 'qualitative_effect' not in converted and 'effect' not in converted['null_components']                          # a quantitative result is pooled, never also counted as qualitative


def test_a_ki_is_the_effect_only_when_there_is_no_kd_and_it_takes_its_own_spread():
    record = synthetic_record()
    missing(record, 'kd')
    converted = convert(record)
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 500.0 and effect['measurement_keys'] == ['dialysis_ki:exp_synthetic_dialysis_1'] and effect['native_component'] == 'ki'
    variance = converted['extraction']['quantities']['effect_variance']
    assert variance['value'] == pytest.approx(2500.0) and variance['native_component'] == 'ki_spread'                     # 50 nM squared, not the 20 nM of the KD
    assert converted['extraction']['quantity_kind'] == 'binding_parameter' and 'qualitative_effect' not in converted
    record['quantities']['ki'] = point(0.5, 'uM', 'k', ['s'])                    # 500 nM in micromolar
    assert convert(record)['extraction']['quantities']['effect']['value'] == pytest.approx(500.0)


def test_a_bmax_alone_is_never_the_effect():
    record = qualitative_record()
    record['quantities']['bmax'] = point(1.0, 'ratio', 'b', ['s'])
    converted = convert(record)
    assert converted['extraction']['quantities']['effect'] is None and 'qualitative_effect' in converted and converted['sheet']['cells']['measured_effect']['value'] is None


def test_the_kind_of_the_spread_decides_whether_a_variance_exists():
    record = synthetic_record()
    record['spread_kind'] = 'standard_deviation'                                 # sd 20 nM over 3 independent experiments: 400 / 3
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(400.0 / 3)
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # fewer than three: partial credit for sampling_basis, but not a variance of the estimate
    converted = convert(record)
    assert converted['extraction']['interpretations']['sampling_basis']['status'] == 'supported' and converted['extraction']['interpretations']['sampling_basis']['degree'] == pytest.approx(math.sqrt(2 / 3))
    assert converted['extraction']['quantities']['effect_variance'] is None and converted['null_components']['effect_variance'] == 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate'
    assert converted['extraction']['quantities']['effect']['value'] == 200.0    # the effect stays, only the variance is null
    record['spread_kind'] = 'confidence_interval'
    assert convert(record)['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    record['spread_kind'] = None
    assert convert(record)['null_components']['effect_variance'] == 'spread_kind_not_stated'
    record['spread_kind'] = 'standard_error'
    missing(record, 'kd_spread')
    assert convert(record)['null_components']['effect_variance'] == 'kd_spread_not_given'
    record['quantities']['kd_spread'] = point(0.02, 'uM', 's', ['s'])           # 20 nM
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(400.0)


def test_the_kd_in_another_unit_is_converted_to_nm():
    record = synthetic_record()
    record['quantities']['kd'] = point(0.2, 'uM', 'k', ['s'])
    assert convert(record)['extraction']['quantities']['effect']['value'] == pytest.approx(200.0)


def test_without_a_kd_or_a_ki_the_effect_is_empty_and_the_result_is_qualitative():
    converted = convert(qualitative_record())
    assert converted['extraction']['quantities']['effect'] is None and converted['extraction']['quantities']['effect_variance'] is None
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None and cells['effect_precision']['value'] is None
    assert converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant' and converted['null_components']['effect_variance'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_exp_qualitative_dialysis_1'], 'percent_bound': 60.0}
    assert converted['extraction']['quantity_kind'] == 'relative_binding_response' and converted['experiment_type'] == 'dialysis'
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_ligand_aq', 'immobilized_preparation_ref': 'prep_protein_aq', 'surface_ref': None, 'dataset_ref': 'dataset_dialysis_q'}
    # the KD criteria do not apply to it, so the sheet criteria that they belong to are decided by the other members
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(SHEET_CRITERIA, 'supported')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_no_number_of_a_qualitative_record_is_put_into_the_effect_but_the_percent_bound_is_carried_beside_it():
    converted = convert(qualitative_record())
    values = [cell['value'] for cell in converted['sheet']['cells'].values()]
    assert 60.0 not in values and 40.0 not in values and 0.6 not in values and 500.0 not in values and 200.0 not in values      # a percent bound and a concentration of one reading are not binding constants
    assert converted['sheet']['cells']['measured_effect']['reasons'] == ['effect_not_selected']
    record = qualitative_record()
    for name in ('percent_bound', 'fraction_bound', 'fraction_unbound'):
        missing(record, name)                                                                  # only the percent unbound: the percent bound is 100 minus it
    assert convert(record)['qualitative_effect']['percent_bound'] == pytest.approx(60.0)
    missing(record, 'percent_unbound')
    assert convert(record)['qualitative_effect']['percent_bound'] is None


def test_the_statement_is_detected_not_detected_or_not_stated():
    record = qualitative_record()
    record['facts']['binding_detected'] = fact('no', ['s'])
    assert convert(record)['qualitative_effect']['statement'] == 'interaction_not_detected' and convert(record)['qualitative_effect']['support_refs'] == ['s']
    for name in ('percent_bound', 'percent_unbound', 'fraction_bound', 'fraction_unbound'):
        missing(record, name)
    record['facts']['binding_detected'] = fact('unknown')
    assert convert(record)['qualitative_effect']['statement'] == 'interaction_not_stated' and convert(record)['qualitative_effect']['support_refs'] == []
    sparse = convert(sparse_record())
    assert sparse['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_binding'], 'percent_bound': None}
    assert sparse['extraction']['interpretations']['binding_parameter_definition']['status'] == 'supported'
    assert sparse['extraction']['interpretations']['binding_controls']['status'] == 'unknown'
    low = convert(low_binding_record())                                                          # 3 percent bound and no statement: the fraction says binding was not shown
    assert low['qualitative_effect'] == {'statement': 'interaction_not_detected', 'support_refs': ['span_exp_low_binding_dialysis'], 'percent_bound': pytest.approx(3.0)}


def test_a_conflicting_member_makes_its_sheet_criterion_conflicting_an_unknown_one_unknown():
    record = synthetic_record()
    record['facts']['buffer_only_control_equal'] = fact('no', ['s'])                      # the ligand did not equalise without protein
    record['facts']['protein_retained'] = fact('unknown')
    record['quantities']['recovery'] = point(40.0, 'percent', 'r', ['s'])                 # a failed mass balance (below the sheet's zero-agreement limit)
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['calibration_applicability']['status'] == 'conflicting'
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'
    record = synthetic_record()
    record['facts']['protein_retained'] = fact('unknown')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'supported'


def test_a_not_applicable_member_is_dropped():
    record = synthetic_record()
    record['facts']['volume_shift_corrected'] = fact('not_applicable')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'supported' and 'span_exp_synthetic_dialysis_1' in interpretations['binding_regime']['support_refs']
    record = qualitative_record()                                                           # every member of calibration_applicability not applicable: the sheet criterion is not selected
    missing(record, 'recovery')
    for name in ('percent_bound', 'percent_unbound', 'fraction_bound', 'fraction_unbound'):
        missing(record, name)
    record['facts']['recovery_checked'] = fact('not_applicable')
    record['facts']['free_ligand_measured_directly'] = fact('not_applicable')
    record['facts']['binding_detected'] = fact('yes', ['s'])
    assert 'calibration_applicability' not in convert(record)['extraction']['interpretations']
    record['facts']['free_ligand_measured_directly'] = fact('unknown')
    assert convert(record)['extraction']['interpretations']['calibration_applicability']['status'] == 'unknown'
    record['separation_method'] = 'ultrafiltration'                                         # an ultrafiltration with no stated time course: the equilibrium member does not apply, the rest decide
    record['facts']['equilibrium_time_course_shown'] = fact('unknown')
    assert grade_dialysis(record)['criteria']['equilibrium']['status'] == 'not_applicable'
    assert convert(record)['extraction']['interpretations']['binding_regime']['status'] == 'supported'


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_dialysis_converter as sheet
    assert (sheet.MIN_PERCENT_BOUND, sheet.MIN_PERCENT_UNBOUND, sheet.FREE_FRACTION_ZERO_AGREEMENT_PERCENT, sheet.MIN_EQUILIBRATION_H, sheet.EQUILIBRATION_ZERO_AGREEMENT_H) == (5.0, 1.0, 0.0, 4.0, 1.0)
    assert (sheet.MIN_RECOVERY_PERCENT, sheet.RECOVERY_ZERO_AGREEMENT_PERCENT, sheet.MAX_ADSORPTION_PERCENT, sheet.ADSORPTION_ZERO_AGREEMENT_PERCENT) == (80.0, 50.0, 15.0, 40.0)
    assert (sheet.MAX_VOLUME_SHIFT_PERCENT, sheet.VOLUME_SHIFT_ZERO_AGREEMENT_PERCENT, sheet.MIN_SALT_MM, sheet.MAX_BOUND_OVER_PROTEIN, sheet.BOUND_OVER_PROTEIN_ZERO_AGREEMENT) == (10.0, 30.0, 100.0, 1.0, 3.0)
    assert (sheet.MIN_PROTEIN_OVER_KD, sheet.PROTEIN_OVER_KD_ZERO_AGREEMENT, sheet.MIN_CONCENTRATIONS, sheet.LOW_FACTOR, sheet.LOW_ZERO_AGREEMENT_FACTOR, sheet.HIGH_FACTOR, sheet.HIGH_ZERO_AGREEMENT_FACTOR, sheet.MIN_REPLICATES) == (0.2, 0.05, 6, 0.5, 1.0, 4.0, 1.0, 3)
    assert (sheet.SALT_ZERO_AGREEMENT_MM, sheet.FIT_PARAMETERS) == (0.0, 2)      # the zero ends of the softened lone minimums
    assert (sheet.QUANTIFIED_PERCENT_BOUND, sheet.HALF_LIVES_AT_MIN_EQUILIBRATION, sheet.MAX_RECOVERY_PERCENT, sheet.RECOVERY_HIGH_ZERO_AGREEMENT_PERCENT) == (15.0, 5.0, 120.0, 150.0)
    assert (sheet.DEVICE_SHARE_OF_BOUND_FULL, sheet.DEVICE_SHARE_OF_BOUND_ZERO, sheet.PLASMA_PROTEIN_NM) == (0.2, 1.0, 600000.0)
    assert not hasattr(sheet, 'SINGLE_EXPERIMENT') and not hasattr(sheet, 'WEIGHT_UNKNOWN')      # one experiment is no longer a conflict; no unknown weight inside a degree


def test_the_degree_travels_into_the_sheet_criterion_and_is_the_weakest_member_degree():
    record = synthetic_record()
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['degree'] == 1.0 and interpretations['binding_regime']['degree'] == 1.0 and interpretations['calibration_applicability']['degree'] == 1.0      # all the continuous members at full agreement
    assert interpretations['sampling_basis']['degree'] == 1.0 and 'degree' not in interpretations['binding_parameter_definition']      # the replicate count is graded now; facts carry none (binding is decided by its fact)
    record['quantities']['recovery'] = point(65.0, 'percent', 'r', ['s'])                 # 0.5
    record['quantities']['membrane_adsorption'] = point(27.5, 'percent', 'a', ['s'])      # 0.5 (binding_controls)
    record['facts']['adsorption_checked_and_corrected'] = fact('unknown')                 # a stated correction would leave only a residual of it (tested apart)
    record['quantities']['percent_unbound'] = point(0.75, 'percent', 'u', ['s'])          # 0.75
    record['facts']['volume_shift_corrected'] = fact('unknown')                           # the stated shift decides instead
    record['quantities']['volume_shift'] = point(20.0, 'percent', 'v', ['s'])             # 0.5 (binding_regime)
    converted = convert(record)
    interpretations = converted['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'supported' and interpretations['calibration_applicability']['degree'] == pytest.approx(0.5)
    assert interpretations['binding_controls']['degree'] == pytest.approx(0.5)
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['degree'] == pytest.approx(0.5)
    assert converted['sheet']['interpretations']['binding_regime']['degree'] == interpretations['binding_regime']['degree']      # it travels into the sheet
    record['quantities']['recovery'] = point(40.0, 'percent', 'r', ['s'])
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'conflicting' and 'degree' not in interpretations['calibration_applicability']


def test_the_lone_minimums_give_partial_credit_just_below_their_researched_values_and_never_a_step():
    weight = {'conflicting': 0.0, 'unknown': 0.9}      # the row weight of a status without a degree (literature_row_contract WEIGHT_CONFLICTING, WEIGHT_UNKNOWN)

    def credit(verdict):
        return verdict['degree'] if verdict['status'] == 'supported' else weight[verdict['status']]

    # replicates (MIN_REPLICATES 3): sqrt(n / 3), the precision of the mean over n independent experiments; one experiment is weaker, never conflicting
    seen = []
    for count, degree in ((1, math.sqrt(1 / 3)), (2, math.sqrt(2 / 3)), (3, 1.0), (6, 1.0)):
        record = synthetic_record()
        record['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        verdict = convert(record)['extraction']['interpretations']['sampling_basis']
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(degree), count
        seen.append(credit(verdict))
    assert seen == sorted(seen)
    record['facts']['independent_experiments'] = fact('unknown')                          # independence not stated: unknown, not a degree
    assert convert(record)['extraction']['interpretations']['sampling_basis']['status'] == 'unknown'
    record['facts']['independent_experiments'] = fact('no', ['s'])                        # a stated no stays the grader's conflicting
    assert convert(record)['extraction']['interpretations']['sampling_basis']['status'] == 'conflicting'
    # the concentration count (MIN_CONCENTRATIONS 6): linear in the residual degrees of freedom of the one-site fit, (n - 2) / 4, 0 at two points but never conflicting;
    # every series spans 0.25 to 8 x the KD
    seen = []
    for series, degree in (([50.0, 1600.0], 0.0), ([50.0, 400.0, 1600.0], 0.25), ([50.0, 200.0, 400.0, 800.0, 1600.0], 0.75),
                           ([50.0, 100.0, 200.0, 400.0, 800.0, 1600.0], 1.0), ([50.0, 100.0, 200.0, 300.0, 400.0, 800.0, 1200.0, 1600.0], 1.0)):
        record = synthetic_record()
        record['concentration_series'] = point(series, 'nM', 'series', ['s'])
        verdict = convert(record)['extraction']['interpretations']['binding_regime']
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(degree), series
        seen.append(credit(verdict))
    assert seen == sorted(seen)
    # Decision C: both ends are linear in the occupancy x / (1 + x) (KD 200 nM). Lowest 150 nM = 0.75 x KD: (1/2 - 3/7) / (1/2 - 1/3) = 3/7. Highest 400 nM = 2 x KD: (2/3 - 1/2) / (4/5 - 1/2) = 5/9;
    # 600 nM = 3 x KD: (3/4 - 1/2) / (3/10) = 5/6.
    for series, degree in (([150.0, 300.0, 600.0, 900.0, 1200.0, 1600.0], 3 / 7), ([50.0, 100.0, 150.0, 200.0, 300.0, 400.0], 5 / 9), ([50.0, 100.0, 200.0, 300.0, 450.0, 600.0], 5 / 6)):
        record = synthetic_record()
        record['concentration_series'] = point(series, 'nM', 'series', ['s'])
        verdict = convert(record)['extraction']['interpretations']['binding_regime']
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(degree), series
    record['concentration_series'] = point([300.0, 400.0, 600.0], 'nM', 'series', ['s'])  # the span still can conflict: the lowest is above the KD
    assert convert(record)['extraction']['interpretations']['binding_regime']['status'] == 'conflicting'


def judge(record, name):
    return _criterion(grade_dialysis(record), name)


def test_the_salt_is_scaled_by_the_protein_and_never_uses_the_unknown_weight_as_a_degree():
    def salted(salt, protein):
        record = synthetic_record()
        record['facts']['volume_shift_corrected'] = fact('unknown')
        missing(record, 'volume_shift')
        record['quantities']['salt_concentration'] = point(salt, 'mM', 'c', ['s'])
        if protein is None:
            missing(record, 'protein_concentration')
        else:
            record['quantities']['protein_concentration'] = point(protein, 'nM', 'p', ['s'])
        return judge(record, 'volume_shift')
    # protein not stated: the researched plasma level, full from MIN_SALT_MM 100, salt / 100 below it, unknown at no salt, never conflicting
    seen = []
    for salt, degree in ((1.0, 0.01), (10.0, 0.1), (50.0, 0.5), (99.0, 0.99), (100.0, 1.0), (150.0, 1.0)):
        verdict = salted(salt, None)
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(degree) and verdict['support_refs'] == ['s'], salt
        seen.append(verdict['degree'])
    assert seen == sorted(seen)
    assert salted(0.0, None) == {'status': 'unknown', 'support_refs': []}
    # a dilute purified protein (1 uM): the Donnan excess is 600 times smaller, so even 1 mM of salt screens it
    assert salted(1.0, 1000.0)['degree'] == pytest.approx(1.0) and salted(0.1, 1000.0)['degree'] == pytest.approx(0.1 / (100.0 * 1000.0 / 600000.0))
    # a protein above the plasma level needs more salt: 1.2 mM protein at 150 mM is 0.75
    assert salted(150.0, 1200000.0)['degree'] == pytest.approx(0.75)


def test_a_detected_binding_gets_credit_rising_from_the_detection_limit_and_the_statement_still_flips_there():
    record = qualitative_record()
    record['facts']['binding_detected'] = fact('unknown')
    seen = []
    for value, statement, status, degree in ((0.5, 'interaction_not_detected', 'conflicting', None), (4.9, 'interaction_not_detected', 'conflicting', None), (5.0, 'interaction_detected', 'supported', 0.0),
                                             (5.5, 'interaction_detected', 'supported', 0.05), (10.0, 'interaction_detected', 'supported', 0.5), (15.0, 'interaction_detected', 'supported', 1.0), (60.0, 'interaction_detected', 'supported', 1.0)):
        record['quantities']['percent_bound'] = point(value, 'percent', 'p', ['s_p'])
        converted = convert(record)
        assert converted['qualitative_effect']['statement'] == statement, value
        verdict = converted['extraction']['interpretations']['binding_parameter_definition']
        assert verdict['status'] == status and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), value
        seen.append(verdict.get('degree', 0.0))
    assert seen == sorted(seen)      # the row weight does not jump where the statement flips: 0 on both sides of MIN_PERCENT_BOUND
    record['facts']['binding_detected'] = fact('yes', ['s_yes'])                            # a stated fact: no degree
    assert 'degree' not in convert(record)['extraction']['interpretations']['binding_parameter_definition']


def test_the_equilibration_time_follows_the_exponential_approach_to_equilibrium():
    def at(hours):
        record = synthetic_record()
        record['facts']['equilibrium_time_course_shown'] = fact('unknown')
        record['quantities']['equilibration_time'] = point(hours, 'h', 't', ['s'])
        return judge(record, 'equilibrium')
    assert at(1.0) == {'status': 'conflicting', 'support_refs': ['s']} and at(0.5)['status'] == 'conflicting'
    seen = []
    for hours in (1.01, 1.5, 2.0, 2.5, 3.0, 3.9, 4.0, 6.0, 36.0):
        verdict = at(hours)
        assert verdict['status'] == 'supported' and 0.0 <= verdict['degree'] <= 1.0, hours
        seen.append(verdict['degree'])
    assert seen == sorted(seen) and seen[0] < 0.05 and seen[-3:] == [1.0, 1.0, 1.0]
    floor, full = 0.5 ** 1.25, 0.5 ** 5      # the share not yet reached at 1 h and at 4 h (five half-lives at 4 h)
    assert at(2.5)['degree'] == pytest.approx((floor - 0.5 ** 3.125) / (floor - full)) and at(2.5)['degree'] > 0.75      # concave: 2.5 h is about 0.79, not the linear 0.5
    assert 0.95 < at(3.9)['degree'] < 1.0                                                     # just below the researched time: nearly full, no step


def test_the_recovery_is_judged_on_both_sides_of_the_researched_window():
    def at(percent):
        record = synthetic_record()
        record['quantities']['recovery'] = point(percent, 'percent', 'r', ['s'])
        return judge(record, 'recovery')
    for percent, status, degree in ((40.0, 'conflicting', None), (50.0, 'conflicting', None), (65.0, 'supported', 0.5), (80.0, 'supported', 1.0), (100.0, 'supported', 1.0),
                                    (120.0, 'supported', 1.0), (135.0, 'supported', 0.5), (149.0, 'supported', 1 / 30), (150.0, 'conflicting', None), (180.0, 'conflicting', None)):
        verdict = at(percent)
        assert verdict['status'] == status and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None) and verdict['support_refs'] == ['s'], percent


def test_an_ultrafiltration_adsorption_is_also_read_against_the_stated_bound_fraction():
    def at(adsorption, unbound, method='ultrafiltration'):
        record = qualitative_record()
        record['separation_method'] = method
        record['facts']['adsorption_checked_and_corrected'] = fact('unknown')
        for name in ('percent_bound', 'fraction_bound', 'fraction_unbound'):
            missing(record, name)
        record['quantities']['percent_unbound'] = point(unbound, 'percent', 'u', ['s_u'])
        record['quantities']['membrane_adsorption'] = point(adsorption, 'percent', 'a', ['s_a'])
        return judge(record, 'device_adsorption')
    # 95 percent unbound (5 bound): a 5 percent filter loss accounts for 0.95 of the binding; 6 percent for all of it
    assert at(5.0, 95.0)['status'] == 'supported' and at(5.0, 95.0)['degree'] == pytest.approx((1.0 - 0.95) / 0.8) and at(5.0, 95.0)['support_refs'] == ['s_a', 's_u']
    assert at(6.0, 95.0) == {'status': 'conflicting', 'support_refs': ['s_a', 's_u']}
    assert at(5.0, 95.0, 'rapid_equilibrium_dialysis') == {'status': 'supported', 'support_refs': ['s_a'], 'degree': 1.0}      # a dialysis: the absolute ramp only
    # a well-bound ligand (40 percent unbound): the share is small and the absolute ramp decides, as before
    assert at(15.0, 40.0)['degree'] == pytest.approx(1.0) and at(27.5, 40.0)['degree'] == pytest.approx(0.5) and at(40.0, 40.0)['status'] == 'conflicting'
    seen = [at(value, 95.0).get('degree', 0.0) for value in (0.0, 0.5, 1.0, 2.0, 4.0, 5.0, 6.0)]
    assert seen == sorted(seen, reverse=True)                                                 # more adsorption never raises the credit
    assert at(5.0, 100.0)['degree'] == pytest.approx(1.0)                                    # nothing bound: nothing for the device to account for


def test_the_bound_over_protein_limits_scale_with_the_papers_own_sites_per_protein():
    def at(bound, bmax=None):
        record = synthetic_record()                                                            # 1000 nM protein
        record['quantities']['bound_ligand_concentration'] = point(bound, 'nM', 'b', ['s'])
        if bmax is None:
            missing(record, 'bmax')
        else:
            record['quantities']['bmax'] = point(bmax[0], bmax[1], 'm', ['s_m'])
        return judge(record, 'ligand_depletion')
    for bmax in (None, (1.0, 'ratio'), (0.5, 'ratio')):                                       # one site or fewer: the researched limits (1 and 3)
        assert at(2000.0, bmax)['degree'] == pytest.approx(0.5) and at(3000.0, bmax)['status'] == 'conflicting', bmax
    for bmax in ((2.0, 'ratio'), (2000.0, 'nM'), (2.0, 'uM')):                                # two sites: full to 2, zero at 6
        verdict = at(2000.0, bmax)
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(1.0) and verdict['support_refs'][0] == 's' and verdict['support_refs'][-1] == 's_m', bmax      # the stated Bmax is cited
        assert at(4000.0, bmax)['degree'] == pytest.approx(0.5) and at(6000.0, bmax)['status'] == 'conflicting', bmax
        seen = [at(value, bmax).get('degree', 0.0) for value in (1000.0, 2000.0, 2500.0, 4000.0, 5900.0, 6000.0)]
        assert seen == sorted(seen, reverse=True)


def test_the_qualitative_statement_of_a_stated_fraction_is_the_sheets_reading_of_its_judgement_exactly_as_before():
    record = qualitative_record()
    record['facts']['binding_detected'] = fact('unknown')                                   # the percent bound (60) decides, with its own refs
    effect = convert(record)['qualitative_effect']
    assert effect['statement'] == 'interaction_detected' and effect['support_refs'] == ['span_exp_qualitative_dialysis_1'] and effect['percent_bound'] == 60.0
    for value, statement in ((5.0, 'interaction_detected'), (4.9, 'interaction_not_detected'), (0.5, 'interaction_not_detected')):
        record['quantities']['percent_bound'] = point(value, 'percent', 'p', ['s_p'])
        effect = convert(record)['qualitative_effect']
        assert effect['statement'] == statement and effect['support_refs'] == ['s_p'] and effect['percent_bound'] == value, value
    record['facts']['binding_detected'] = fact('yes', ['s_yes'])                            # a stated fact wins over the fraction
    effect = convert(record)['qualitative_effect']
    assert effect['statement'] == 'interaction_detected' and effect['support_refs'] == ['s_yes']


def test_a_criterion_resting_on_a_weak_quote_gets_the_support_degree_and_a_direct_one_is_unchanged():
    base = convert(synthetic_record())['extraction']['interpretations']
    assert base['binding_controls']['status'] == base['sampling_basis']['status'] == 'supported' and base['sampling_basis']['degree'] == 1.0
    record = synthetic_record()
    record['facts']['protein_retained']['support'] = 'implied'            # a fact: supported with no degree before
    record['quantities']['replicate_count']['support'] = 'about_something_else'
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'supported' and interpretations['binding_controls']['degree'] == pytest.approx(min(base['binding_controls'].get('degree', 1.0), 0.7))
    assert interpretations['sampling_basis']['status'] == 'supported' and interpretations['sampling_basis']['degree'] == pytest.approx(0.3)
    assert interpretations['binding_regime'] == base['binding_regime'] and interpretations['calibration_applicability'] == base['calibration_applicability']
    record['facts']['protein_retained'] = fact('no', ['s'], 'about_something_else')      # a status is never changed by support: conflicting keeps no degree
    verdict = convert(record)['extraction']['interpretations']['binding_controls']
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    record = synthetic_record()
    record['quantities']['kd_spread']['support'] = 'implied'
    assert convert(record)['extraction']['interpretations']['variance_correspondence']['degree'] == pytest.approx(0.7)
    record = synthetic_record()
    record['choice_support']['fit_model'] = 'implied'
    assert convert(record)['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(min(base['binding_parameter_definition'].get('degree', 1.0), 0.7))


def test_the_stated_standard_deviation_of_the_percent_bound_moves_the_detection_ramp():
    def at(percent, spread=None):
        record = qualitative_record()
        record['facts']['binding_detected'] = fact('unknown')
        record['quantities']['percent_bound'] = point(percent, 'percent', 'p', ['s_p'])
        if spread is not None:
            record['quantities']['percent_bound_spread'] = point(spread, 'percent', 'sd', ['s_sd'])
        return judge(record, 'binding_observed')
    assert at(10.0) == {'status': 'supported', 'support_refs': ['s_p'], 'degree': pytest.approx(0.5)}      # not stated: the researched ramp, 5 to 15
    # sd 4 points: the ramp starts at 3.3 x 4 = 13.2 and is full at 10 x 4 = 40
    assert at(10.0, 4.0)['degree'] == 0.0 and at(26.6, 4.0)['degree'] == pytest.approx(0.5) and at(40.0, 4.0)['degree'] == 1.0 and at(26.6, 4.0)['support_refs'] == ['s_p', 's_sd']
    assert at(4.0, 4.0)['status'] == 'conflicting'                                           # the direction stays decided at the researched 5
    for percent in (6.0, 12.0, 20.0, 30.0, 60.0):                                            # a noisier measurement never raises the degree
        degrees = [at(percent, spread)['degree'] for spread in (0.1, 1.0, 2.0, 4.0, 8.0)]
        assert degrees == sorted(degrees, reverse=True) and all(0.0 <= d <= 1.0 for d in degrees)
    for spread in (0.5, 4.0):                                                                # more bound never lowers it: no step
        degrees = [at(percent, spread)['degree'] for percent in (5.0, 8.0, 12.0, 20.0, 40.0, 80.0)]
        assert degrees == sorted(degrees)
    assert at(8.0, 0.5)['degree'] == at(8.0)['degree']                                       # a precise detector never moves the researched ramp


def test_the_detector_limit_of_quantification_is_read_against_the_free_concentration():
    def at(lloq, free=None, unbound=None, total=None):
        record = qualitative_record()
        for name in ('percent_unbound', 'percent_bound', 'fraction_bound', 'fraction_unbound', 'free_ligand_concentration', 'ligand_total_concentration'):
            missing(record, name)
        if unbound is not None:
            record['quantities']['percent_unbound'] = point(unbound, 'percent', 'u', ['s_u'])
        if free is not None:
            record['quantities']['free_ligand_concentration'] = point(free, 'nM', 'f', ['s_f'])
        if total is not None:
            record['quantities']['ligand_total_concentration'] = point(total, 'nM', 't', ['s_t'])
        if lloq is not None:
            record['quantities']['detection_lloq'] = point(lloq, 'nM', 'l', ['s_l'])
        return record
    graded = grade_dialysis(at(2.0, free=200.0))
    assert (graded['reasons']['free_fraction_measurable'], graded['native']['free_over_lloq'], graded['native']['free_over_lloq_refs']) == ('free_over_lloq_recorded_for_the_sheet', 100.0, ['s_f', 's_l'])
    for ratio, status, degree in ((100.0, 'supported', 1.0), (3.0, 'supported', 1.0), (2.0, 'supported', 0.5), (1.5, 'supported', 0.25), (1.0, 'conflicting', None), (0.5, 'conflicting', None)):
        verdict = judge(at(1.0, free=ratio), 'free_fraction_measurable')
        assert verdict['status'] == status and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), ratio
    seen = [judge(at(1.0, free=ratio), 'free_fraction_measurable').get('degree', 0.0) for ratio in (0.5, 1.0, 1.5, 2.0, 3.0, 10.0)]
    assert seen == sorted(seen)                                                              # a larger free concentration never lowers the credit
    derived = grade_dialysis(at(2.0, unbound=0.5, total=1000.0))                             # no stated free concentration: total x percent unbound = 5 nM = 2.5 x the limit
    assert derived['native']['free_over_lloq'] == pytest.approx(2.5) and derived['native']['free_over_lloq_refs'] == ['s_t', 's_u', 's_l']
    verdict = judge(at(2.0, unbound=0.5, total=1000.0), 'free_fraction_measurable')           # the weaker of the percent-unbound ramp (0.5 of 1 to 0) and the limit ramp (0.75)
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(0.5) and verdict['support_refs'] == ['s_u', 's_t', 's_l']
    assert judge(at(None, unbound=0.5, total=1000.0), 'free_fraction_measurable')['degree'] == pytest.approx(0.5)      # no limit stated: the researched percent ramp as before
    assert grade_dialysis(at(None, free=200.0))['reasons']['free_fraction_measurable'] == 'no_fraction_reported'      # a free concentration without the limit or a fraction: nothing to judge


def test_a_stated_and_corrected_adsorption_leaves_only_a_residual_of_itself():
    def at(adsorption, corrected, method='equilibrium_dialysis', unbound=None):
        record = qualitative_record()
        record['separation_method'] = method
        record['facts']['adsorption_checked_and_corrected'] = fact(corrected, ['s_c'] if corrected in ('yes', 'no') else [])
        record['quantities']['membrane_adsorption'] = point(adsorption, 'percent', 'a', ['s_a'])
        if unbound is not None:
            for name in ('percent_bound', 'fraction_bound', 'fraction_unbound'):
                missing(record, name)
            record['quantities']['percent_unbound'] = point(unbound, 'percent', 'u', ['s_u'])
        return record
    graded = grade_dialysis(at(27.5, 'yes'))
    assert graded['native']['adsorption_corrected'] == 'yes' and graded['native']['adsorption_corrected_refs'] == ['s_c']
    assert grade_dialysis(at(27.5, 'unknown'))['native']['adsorption_corrected'] is None
    assert judge(at(27.5, 'unknown'), 'device_adsorption')['degree'] == pytest.approx(0.5)     # not stated: whole
    assert judge(at(27.5, 'no'), 'device_adsorption')['degree'] == pytest.approx(0.5)          # stated not corrected: whole
    corrected = judge(at(27.5, 'yes'), 'device_adsorption')                                    # 15 percent of 27.5 = 4.1: inside the researched 15
    assert corrected == {'status': 'supported', 'support_refs': ['s_a', 's_c'], 'degree': 1.0}
    assert judge(at(40.0, 'unknown'), 'device_adsorption')['status'] == 'conflicting' and judge(at(40.0, 'yes'), 'device_adsorption')['status'] == 'supported'      # a corrected 40 percent is not the whole bias
    assert judge(at(95.0, 'yes'), 'device_adsorption')['degree'] == 1.0                       # even 95 percent corrected leaves 14.25 (the residual share can never exceed 15 of 100)
    degrees = [judge(at(value, 'yes'), 'device_adsorption').get('degree', 0.0) for value in (5.0, 50.0, 100.0)]
    assert degrees == sorted(degrees, reverse=True)
    # an ultrafiltration with 95 percent unbound: a 5 percent loss accounts for 0.95 of the bound; corrected, for 0.1425 (inside the 0.2 limit)
    assert judge(at(5.0, 'unknown', 'ultrafiltration', 95.0), 'device_adsorption')['degree'] == pytest.approx(0.0625)
    assert judge(at(5.0, 'yes', 'ultrafiltration', 95.0), 'device_adsorption')['degree'] == 1.0
