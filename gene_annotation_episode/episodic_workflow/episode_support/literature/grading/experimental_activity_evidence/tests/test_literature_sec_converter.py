"""SEC converter: the quantitative effect and variance (an apparent KD from peak areas), the qualitative effect (no KD), the criteria mapping and the null reasons."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_converter import (
    CRITERIA_MAP, MASS_FULL_AGREEMENT_PERCENT, MASS_ZERO_AGREEMENT_PERCENT, MAX_POLYDISPERSITY, MIN_ELUTION_SHIFT_ML, MIN_LOAD_OVER_KD, MIN_REPLICATES, MIN_SALT_MM, STOICHIOMETRY_TOLERANCE, _criterion, convert_sec)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_grader import CRITERIA, grade_sec
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.sec_cases import qualitative_record, sparse_record, synthetic_record

SHEET_CRITERIA = ('binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis')


def convert(record):
    return convert_sec(grade_sec(record))


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped)) == 13


def test_the_apparent_kd_is_the_effect_and_its_standard_error_squared_is_the_variance():
    converted = convert(synthetic_record())
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 200.0 and effect['unit'] == 'nM' and effect['measurement_keys'] == ['sec_kd:exp_synthetic_sec_1'] and effect['native_component'] == 'kd'
    variance = converted['extraction']['quantities']['effect_variance']
    assert variance['value'] == pytest.approx(400.0) and variance['unit'] == 'nM_squared' and variance['origin'] == 'derived'      # 20 nM squared
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(200.0) and cells['effect_variance']['value'] == pytest.approx(400.0) and cells['effect_precision']['value'] == pytest.approx(1 / 400.0)
    assert converted['extraction']['assay_type'] == 'ligand_binding' and converted['extraction']['quantity_kind'] == 'binding_parameter' and converted['experiment_type'] == 'sec'
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys((*SHEET_CRITERIA, 'variance_correspondence'), 'supported')
    assert all(item['support_refs'] for item in converted['extraction']['interpretations'].values())
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_component_a', 'immobilized_preparation_ref': 'prep_component_b', 'surface_ref': None, 'dataset_ref': 'dataset_sec_1'}
    assert converted['null_components']['recovery'] == 'an_sec_has_no_matrix_recovery_measurement'
    assert 'qualitative_effect' not in converted and 'effect' not in converted['null_components']                          # a quantitative result is pooled, never also counted as qualitative


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


def test_without_a_kd_the_effect_is_empty_and_the_result_is_qualitative():
    converted = convert(qualitative_record())
    assert converted['extraction']['quantities']['effect'] is None and converted['extraction']['quantities']['effect_variance'] is None
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None and cells['effect_precision']['value'] is None
    assert converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant' and converted['null_components']['effect_variance'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_exp_qualitative_sec_1'], 'elution_shift_ml': 1.3}
    assert converted['extraction']['quantity_kind'] == 'relative_binding_response' and converted['experiment_type'] == 'sec'
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_component_aq', 'immobilized_preparation_ref': 'prep_component_bq', 'surface_ref': None, 'dataset_ref': 'dataset_sec_q'}
    # the KD criteria do not apply to it, so the sheet criteria that they belong to are decided by the other members
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(SHEET_CRITERIA, 'supported')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_no_number_of_a_qualitative_record_is_put_into_the_effect_but_the_shift_is_carried_beside_it():
    converted = convert(qualitative_record())
    values = [cell['value'] for cell in converted['sheet']['cells'].values()]
    assert 1.3 not in values and 52.0 not in values and 54.0 not in values                       # a shift in mL and a molar mass in kDa are not binding constants
    assert converted['sheet']['cells']['measured_effect']['reasons'] == ['effect_not_selected']
    record = qualitative_record()
    missing(record, 'elution_volume_shift')                                                      # no stated shift: the difference of the two volumes (12.5 - 11.2)
    assert convert(record)['qualitative_effect']['elution_shift_ml'] == pytest.approx(1.3)
    missing(record, 'complex_elution_volume')
    assert convert(record)['qualitative_effect']['elution_shift_ml'] is None


def test_the_statement_is_detected_not_detected_or_not_stated():
    record = qualitative_record()
    record['facts']['complex_peak_detected'] = fact('no', ['s'])
    assert convert(record)['qualitative_effect']['statement'] == 'interaction_not_detected' and convert(record)['qualitative_effect']['support_refs'] == ['s']
    record['facts']['complex_peak_detected'] = fact('unknown')
    assert convert(record)['qualitative_effect']['statement'] == 'interaction_not_stated' and convert(record)['qualitative_effect']['support_refs'] == []
    sparse = convert(sparse_record())
    assert sparse['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_peak'], 'elution_shift_ml': None}
    assert sparse['extraction']['interpretations']['binding_parameter_definition']['status'] == 'unknown'     # the shift and the mass are not stated


def test_a_conflicting_member_makes_its_sheet_criterion_conflicting_an_unknown_one_unknown():
    record = synthetic_record()
    record['facts']['single_component_control_done'] = fact('no', ['s'])                  # the non-binding mutant co-eluted
    record['facts']['components_run_alone'] = fact('unknown')
    record['quantities']['loaded_concentration'] = point(1000.0, 'nM', 'l', ['s'])        # five times the KD: the complex does not survive the dilution
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['binding_regime']['status'] == 'conflicting'
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'
    record = synthetic_record()
    record['facts']['components_run_alone'] = fact('unknown')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'supported'


def test_the_sheet_judges_the_recorded_mass_deviation_with_its_own_thresholds():
    assert MASS_FULL_AGREEMENT_PERCENT == 10.0 and MASS_ZERO_AGREEMENT_PERCENT == 50.0
    record = synthetic_record()
    record['quantities']['complex_mass_theoretical'] = point(100.0, 'kDa', 't', ['s_theory'])
    for measured, expected, degree in ((100.0, 'supported', 1.0), (90.0, 'supported', 1.0), (110.0, 'supported', 1.0), (85.0, 'supported', 0.875), (115.0, 'supported', 0.875), (70.0, 'supported', 0.5),
                                       (51.0, 'supported', 0.025), (50.0, 'conflicting', None), (150.0, 'conflicting', None)):
        record['quantities']['complex_mass_measured'] = point(measured, 'kDa', 'm', ['s_mass'])
        graded = grade_sec(record)
        assert _criterion(graded, 'mals_mass')['status'] == expected, measured
        assert _criterion(graded, 'mals_mass').get('degree') == (pytest.approx(degree) if degree is not None else None), measured
        interpretation = convert_sec(graded)['extraction']['interpretations']['binding_parameter_definition']
        assert interpretation['status'] == expected, measured
        assert interpretation.get('degree') == (pytest.approx(degree) if degree is not None else None), measured       # the other members have no degree
    record['quantities']['complex_mass_measured'] = point(50.0, 'kDa', 'm', ['s_mass'])
    assert _criterion(grade_sec(record), 'mals_mass')['support_refs'] == ['s_mass', 's_theory']
    missing(record, 'complex_mass_theoretical')                                            # not both stated: the fact path, as the grader answered
    record['facts']['mals_mass_matches_complex'] = fact('yes', ['s'])
    assert _criterion(grade_sec(record), 'mals_mass')['status'] == 'supported'


def judged(record, name):
    return _criterion(grade_sec(record), name)


def test_the_real_mass_pair_of_the_paper_is_supported_with_a_degree_of_about_085():
    record = synthetic_record()
    record['quantities']['complex_mass_measured'] = point(21.7, 'kDa', 'm', ['s_mass'])
    record['quantities']['complex_mass_theoretical'] = point(12.0098 + 13.8637, 'kDa', 't', ['s_theory'])
    graded = grade_sec(record)
    assert graded['native']['mass_deviation_percent'] == pytest.approx(-16.13, abs=0.01) and graded['criteria']['mals_mass']['status'] == 'unknown'      # the grader only records it
    verdict = _criterion(graded, 'mals_mass')
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(0.847, abs=1e-3) and verdict['support_refs'] == ['s_mass', 's_theory']
    interpretation = convert_sec(graded)['extraction']['interpretations']['binding_parameter_definition']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.847, abs=1e-3)
    assert convert_sec(graded)['sheet']['interpretations']['binding_parameter_definition']['degree'] == interpretation['degree']        # it travels into the sheet


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (MIN_ELUTION_SHIFT_ML, MAX_POLYDISPERSITY, MIN_LOAD_OVER_KD, MIN_SALT_MM, STOICHIOMETRY_TOLERANCE, MIN_REPLICATES) == (0.3, 1.05, 10.0, 100.0, 0.1, 3)


def test_the_sheet_judges_the_elution_shift():
    record = synthetic_record()
    for value, expected in ((0.3, 'supported'), (0.29, 'conflicting'), (5.0, 'supported'), (-0.5, 'conflicting')):
        record['quantities']['elution_volume_shift'] = point(value, 'mL', 'sh', ['s'])
        assert judged(record, 'elution_shift') == {'status': expected, 'support_refs': ['s']}, value
        assert convert(record)['extraction']['interpretations']['binding_parameter_definition']['status'] == ('supported' if expected == 'supported' else 'conflicting')
    missing(record, 'elution_volume_shift')
    missing(record, 'complex_elution_volume')
    assert judged(record, 'elution_shift') == {'status': 'unknown', 'support_refs': []}


def test_the_sheet_judges_the_stoichiometry_only_with_a_kd():
    record = synthetic_record()
    for ratio, expected in ((1.0, 'supported'), (1.09, 'supported'), (0.91, 'supported'), (1.12, 'conflicting'), (0.88, 'conflicting'), (2.0, 'conflicting')):
        record['quantities']['stoichiometry_ratio'] = point(ratio, 'ratio', 'r', ['s'])
        assert judged(record, 'stoichiometry')['status'] == expected, ratio
    assert judged(record, 'stoichiometry')['support_refs'] == ['s']
    missing(record, 'kd')
    assert judged(record, 'stoichiometry')['status'] == 'not_applicable'


def test_the_sheet_judges_the_salt_only_when_the_buffer_fact_is_unknown_and_a_low_salt_is_unknown():
    record = synthetic_record()
    record['facts']['buffer_rules_out_resin_interaction'] = fact('unknown')
    for value, unit, expected in ((100.0, 'mM', 'supported'), (0.1, 'M', 'supported'), (99.0, 'mM', 'unknown'), (0.05, 'M', 'unknown')):
        record['quantities']['salt_concentration'] = point(value, unit, 'salt', ['s'])
        assert judged(record, 'resin_interaction') == {'status': expected, 'support_refs': ['s'] if expected == 'supported' else []}, (value, unit)
    record['facts']['buffer_rules_out_resin_interaction'] = fact('no', ['s'])
    assert judged(record, 'resin_interaction')['status'] == 'conflicting'                  # the fact is the grader's, whatever the salt


def test_the_sheet_judges_the_load_over_the_kd():
    record = synthetic_record()                                                              # KD 200 nM
    for loaded, unit, expected in ((2000.0, 'nM', 'supported'), (1999.0, 'nM', 'conflicting'), (2.0, 'uM', 'supported'), (1.0, 'uM', 'conflicting')):
        record['quantities']['loaded_concentration'] = point(loaded, unit, 'l', ['s'])
        assert judged(record, 'complex_stable_on_column')['status'] == expected, (loaded, unit)
    assert len(judged(record, 'complex_stable_on_column')['support_refs']) == 2


def test_the_sheet_judges_the_polydispersity():
    record = synthetic_record()
    for value, expected in ((1.05, 'supported'), (1.0, 'supported'), (1.06, 'conflicting'), (1.5, 'conflicting')):
        record['quantities']['polydispersity'] = point(value, 'ratio', 'p', ['s'])
        assert judged(record, 'monodispersity') == {'status': expected, 'support_refs': ['s']}, value


def test_the_sheet_judges_the_replicate_count_and_its_independence():
    record = synthetic_record()
    for count, independent, expected in ((3, 'yes', 'supported'), (10, 'yes', 'supported'), (2, 'yes', 'conflicting'), (2, 'unknown', 'conflicting'), (3, 'unknown', 'unknown')):
        record['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        record['facts']['independent_experiments'] = fact(independent, ['s'] if independent != 'unknown' else [])
        assert judged(record, 'replicates')['status'] == expected, (count, independent)
    record['facts']['independent_experiments'] = fact('no', ['s'])                           # a stated 'no' is a fact the grader judges
    assert judged(record, 'replicates')['status'] == 'conflicting'
    missing(record, 'replicate_count')
    record['facts']['independent_experiments'] = fact('yes', ['s'])
    assert judged(record, 'replicates')['status'] == 'unknown'


def test_a_not_applicable_member_is_dropped():
    record = synthetic_record()
    record['facts']['free_peak_decreases_with_titration'] = fact('not_applicable')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['support_refs'] == ['span_exp_synthetic_sec_1']
    record['facts']['free_peak_decreases_with_titration'] = fact('not_applicable')
    record['facts']['complex_stable_on_column'] = fact('not_applicable')
    missing(record, 'loaded_concentration')
    assert 'binding_regime' not in convert(record)['extraction']['interpretations']        # both members not applicable: the sheet criterion is not selected
    record['facts']['complex_stable_on_column'] = fact('unknown')
    assert convert(record)['extraction']['interpretations']['binding_regime']['status'] == 'unknown'


def test_a_criterion_resting_on_a_weak_quote_gets_the_support_degree_and_a_direct_one_is_unchanged():
    base = convert(synthetic_record())['extraction']['interpretations']
    assert base['binding_controls']['status'] == base['sampling_basis']['status'] == 'supported' and 'degree' not in base['sampling_basis']
    record = synthetic_record()
    record['facts']['components_run_alone']['support'] = 'implied'            # a fact: supported with no degree before
    record['quantities']['replicate_count']['support'] = 'about_something_else'
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'supported' and interpretations['binding_controls']['degree'] == pytest.approx(min(base['binding_controls'].get('degree', 1.0), 0.7))
    assert interpretations['sampling_basis']['status'] == 'supported' and interpretations['sampling_basis']['degree'] == pytest.approx(0.3)
    assert interpretations['binding_regime'] == base['binding_regime'] and interpretations['calibration_applicability'] == base['calibration_applicability']
    record['facts']['components_run_alone'] = fact('no', ['s'], 'about_something_else')      # a status is never changed by support: conflicting keeps no degree
    verdict = convert(record)['extraction']['interpretations']['binding_controls']
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    record = synthetic_record()
    record['quantities']['kd_spread']['support'] = 'implied'
    assert convert(record)['extraction']['interpretations']['variance_correspondence']['degree'] == pytest.approx(0.7)


def test_the_support_degree_multiplies_the_degree_of_the_mass_criterion_from_the_deviation():
    record = synthetic_record()
    record['quantities']['complex_mass_theoretical'] = point(100.0, 'kDa', 't', ['s_theory'])
    record['quantities']['complex_mass_measured'] = point(70.0, 'kDa', 'm', ['s_mass'], support='implied')      # deviation 30 percent: degree 0.5, times 0.7
    graded = grade_sec(record)
    verdict = _criterion(graded, 'mals_mass')
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(0.5)                          # the sheet's own judgement of the deviation
    interpretation = convert_sec(graded)['extraction']['interpretations']['binding_parameter_definition']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.35)
    record['quantities']['complex_mass_measured'] = point(70.0, 'kDa', 'm', ['s_mass'], support='about_something_else')
    assert convert_sec(grade_sec(record))['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.15)
    record['quantities']['complex_mass_measured'] = point(150.0, 'kDa', 'm', ['s_mass'], support='about_something_else')      # conflicting: no degree
    interpretation = convert_sec(grade_sec(record))['extraction']['interpretations']['binding_parameter_definition']
    assert interpretation['status'] == 'conflicting' and 'degree' not in interpretation


def test_the_qualitative_effect_is_not_touched_by_support():
    record = qualitative_record()
    record['facts']['complex_peak_detected']['support'] = 'about_something_else'
    effect = convert(record)['qualitative_effect']
    assert effect['statement'] == 'interaction_detected' and effect['support_refs']
