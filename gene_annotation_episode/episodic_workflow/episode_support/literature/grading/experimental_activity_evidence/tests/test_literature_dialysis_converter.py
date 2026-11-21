"""Dialysis converter: the quantitative effect and variance (a KD, else a Ki), the qualitative effect (no KD and no Ki), the criteria mapping and the null reasons."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dialysis_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_converter import CRITERIA_MAP, convert_dialysis
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
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # fewer than three: not supported
    converted = convert(record)
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


def test_the_degree_travels_into_the_sheet_criterion_and_is_the_weakest_member_degree():
    record = synthetic_record()
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['degree'] == 1.0 and interpretations['binding_regime']['degree'] == 1.0 and interpretations['calibration_applicability']['degree'] == 1.0      # all the continuous members at full agreement
    assert 'degree' not in interpretations['sampling_basis'] and 'degree' not in interpretations['binding_parameter_definition']      # a count and facts carry none (binding is decided by its fact)
    record['quantities']['recovery'] = point(65.0, 'percent', 'r', ['s'])                 # 0.5
    record['quantities']['membrane_adsorption'] = point(27.5, 'percent', 'a', ['s'])      # 0.5 (binding_controls)
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
    assert base['binding_controls']['status'] == base['sampling_basis']['status'] == 'supported' and 'degree' not in base['sampling_basis']
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
