"""EMSA converter: the quantitative effect and variance (an apparent KD), the qualitative effect (no KD), the criteria mapping and the null reasons."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_emsa_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_converter import CRITERIA_MAP, convert_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_grader import CRITERIA, grade_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.emsa_cases import qualitative_record, sparse_record, synthetic_record

SHEET_CRITERIA = ('binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis')


def convert(record):
    return convert_emsa(grade_emsa(record))


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped)) == 17


def test_the_apparent_kd_is_the_effect_and_its_standard_error_squared_is_the_variance():
    converted = convert(synthetic_record())
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 20.0 and effect['unit'] == 'nM' and effect['measurement_keys'] == ['emsa_kd:exp_synthetic_emsa_1'] and effect['native_component'] == 'kd'
    variance = converted['extraction']['quantities']['effect_variance']
    assert variance['value'] == pytest.approx(4.0) and variance['unit'] == 'nM_squared' and variance['origin'] == 'derived'      # 2 nM squared
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(20.0) and cells['effect_variance']['value'] == pytest.approx(4.0) and cells['effect_precision']['value'] == pytest.approx(0.25)
    assert converted['extraction']['assay_type'] == 'ligand_binding' and converted['extraction']['quantity_kind'] == 'binding_parameter' and converted['experiment_type'] == 'emsa'
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys((*SHEET_CRITERIA, 'variance_correspondence'), 'supported')
    assert all(item['support_refs'] for item in converted['extraction']['interpretations'].values())
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_protein_a', 'immobilized_preparation_ref': 'prep_probe_a', 'surface_ref': None, 'dataset_ref': 'dataset_emsa_1'}
    assert converted['null_components']['recovery'] == 'an_emsa_has_no_matrix_recovery_measurement'
    assert 'qualitative_effect' not in converted and 'effect' not in converted['null_components']                          # a quantitative result is pooled, never also counted as qualitative


def test_the_kind_of_the_spread_decides_whether_a_variance_exists():
    record = synthetic_record()
    record['spread_kind'] = 'standard_deviation'                                 # sd 2 nM over 3 independent experiments: 4 / 3
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(4.0 / 3)
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # fewer than three: not supported
    converted = convert(record)
    assert converted['extraction']['quantities']['effect_variance'] is None and converted['null_components']['effect_variance'] == 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate'
    assert converted['extraction']['quantities']['effect']['value'] == 20.0     # the effect stays, only the variance is null
    record['spread_kind'] = 'confidence_interval'
    assert convert(record)['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    record['spread_kind'] = None
    assert convert(record)['null_components']['effect_variance'] == 'spread_kind_not_stated'
    record['spread_kind'] = 'standard_error'
    missing(record, 'kd_spread')
    assert convert(record)['null_components']['effect_variance'] == 'kd_spread_not_given'
    record['quantities']['kd_spread'] = point(0.002, 'uM', 's', ['s'])          # 2 nM
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(4.0)


def test_the_kd_in_another_unit_is_converted_to_nm():
    record = synthetic_record()
    record['quantities']['kd'] = point(0.02, 'uM', 'k', ['s'])
    assert convert(record)['extraction']['quantities']['effect']['value'] == pytest.approx(20.0)


def test_without_a_kd_the_effect_is_empty_and_the_result_is_qualitative():
    converted = convert(qualitative_record())
    assert converted['extraction']['quantities']['effect'] is None and converted['extraction']['quantities']['effect_variance'] is None
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None and cells['effect_precision']['value'] is None
    assert converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant' and converted['null_components']['effect_variance'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_exp_qualitative_emsa_1'], 'fraction_shifted': None}
    assert converted['extraction']['quantity_kind'] == 'relative_binding_response' and converted['experiment_type'] == 'emsa'
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_protein_q', 'immobilized_preparation_ref': 'prep_probe_q', 'surface_ref': None, 'dataset_ref': 'dataset_emsa_q'}
    # the KD criteria do not apply to it, so the sheet criteria that they belong to are decided by the other members
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(SHEET_CRITERIA, 'supported')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_no_number_of_a_qualitative_record_is_put_into_the_effect_but_the_fraction_shifted_is_carried_beside_it():
    record = qualitative_record()
    record['quantities']['fraction_shifted_highest'] = point(92.0, 'percent', 'f', ['s'])         # a shifted fraction is not a binding constant
    converted = convert(record)
    assert 92.0 not in [cell['value'] for cell in converted['sheet']['cells'].values()]
    assert converted['sheet']['cells']['measured_effect']['reasons'] == ['effect_not_selected']
    assert converted['qualitative_effect']['fraction_shifted'] == 92.0


def test_the_statement_is_detected_not_detected_or_not_stated():
    record = qualitative_record()
    record['facts']['shift_detected'] = fact('no', ['s'])
    assert convert(record)['qualitative_effect'] == {'statement': 'interaction_not_detected', 'support_refs': ['s'], 'fraction_shifted': None}
    record['facts']['shift_detected'] = fact('unknown')
    assert convert(record)['qualitative_effect'] == {'statement': 'interaction_not_stated', 'support_refs': [], 'fraction_shifted': None}
    sparse = convert(sparse_record())
    assert sparse['qualitative_effect']['statement'] == 'interaction_detected' and sparse['extraction']['interpretations']['binding_parameter_definition']['status'] == 'unknown'     # the number of shifted species is not stated


def test_a_conflicting_member_makes_its_sheet_criterion_conflicting_an_unknown_one_unknown():
    record = synthetic_record()
    record['facts']['mutant_probe_does_not_shift'] = fact('no', ['s'])                    # the mutant probe shifted
    record['facts']['probe_alone_lane_shown'] = fact('unknown')
    record['quantities']['protein_concentration_highest'] = point(20.0, 'nM', 'h', ['s'])      # only the KD: the plateau is not reached (the zero-agreement limit)
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['binding_regime']['status'] == 'conflicting'
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'
    record = synthetic_record()
    record['facts']['probe_alone_lane_shown'] = fact('unknown')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'supported'


def test_a_not_applicable_member_is_dropped():
    record = synthetic_record()
    record['facts']['free_probe_quantified'] = fact('not_applicable')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'supported' and interpretations['calibration_applicability']['support_refs'] == ['span_exp_synthetic_emsa_1']
    record['facts']['free_probe_quantified'] = fact('not_applicable')
    missing(record, 'fraction_shifted_highest')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'unknown'          # the saturation criterion is unknown without the fraction
    missing(record, 'kd')
    interpretations = convert(record)['extraction']['interpretations']
    assert 'calibration_applicability' not in interpretations                           # both members not applicable: the sheet criterion is not selected


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_emsa_converter as sheet
    assert (sheet.MIN_COMPETITOR_EXCESS, sheet.MIN_INCUBATION_MIN, sheet.MAX_PROBE_OVER_KD, sheet.PROBE_OVER_KD_ZERO_AGREEMENT) == (50.0, 15.0, 1.0, 10.0)
    assert (sheet.LOW_FACTOR, sheet.LOW_ZERO_AGREEMENT_FACTOR, sheet.HIGH_FACTOR, sheet.HIGH_ZERO_AGREEMENT_FACTOR) == (0.25, 1.0, 5.0, 1.0)
    assert (sheet.MIN_TITRATION_POINTS, sheet.MIN_FRACTION_SHIFTED_HIGHEST, sheet.FRACTION_SHIFTED_ZERO_AGREEMENT, sheet.MAX_SHIFTED_SPECIES, sheet.ONE_SITE_MODELS, sheet.MIN_REPLICATES) == (6, 80.0, 50.0, 1, ('one_site', 'quadratic'), 3)


def test_the_degree_travels_into_the_sheet_criterion_and_is_the_weakest_member_degree():
    record = synthetic_record()                                                          # KD 20 nM
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['degree'] == 1.0 and interpretations['calibration_applicability']['degree'] == 1.0 and interpretations['binding_parameter_definition']['degree'] == 1.0
    assert 'degree' not in interpretations['sampling_basis'] and 'degree' not in interpretations['binding_controls']
    record['quantities']['probe_concentration'] = point(110.0, 'nM', 'p', ['s'])         # 5.5 x the KD: degree 0.5 (and the same for the one-site model)
    record['quantities']['fraction_shifted_highest'] = point(65.0, 'percent', 'f', ['s'])  # degree 0.5
    record['quantities']['protein_concentration_highest'] = point(60.0, 'nM', 'h', ['s'])  # 3 x the KD: degree 0.5
    converted = convert(record)
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['degree'] == pytest.approx(0.5)
    assert interpretations['calibration_applicability']['degree'] == pytest.approx(0.5) and interpretations['binding_parameter_definition']['degree'] == pytest.approx(0.5)
    assert converted['sheet']['interpretations']['binding_regime']['degree'] == interpretations['binding_regime']['degree']      # it travels into the sheet
    record['quantities']['fraction_shifted_highest'] = point(40.0, 'percent', 'f', ['s'])
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'conflicting' and 'degree' not in interpretations['calibration_applicability']


def test_several_species_with_no_kd_are_not_applicable_and_dropped_by_the_sheet():
    record = synthetic_record()
    record['quantities']['shifted_species_count'] = point(2, 'count', 's', ['s'])
    assert convert(record)['extraction']['interpretations']['binding_parameter_definition']['status'] == 'conflicting'      # one-site fit for two species
    record['fit_model'] = 'hill'
    assert convert(record)['extraction']['interpretations']['binding_parameter_definition']['status'] == 'supported'
    missing(record, 'kd')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['binding_parameter_definition']['support_refs'] == ['span_exp_synthetic_emsa_1']      # only the shift is left


def test_a_criterion_resting_on_a_weak_quote_gets_the_support_degree_and_a_direct_one_is_unchanged():
    base = convert(synthetic_record())['extraction']['interpretations']
    assert base['binding_controls']['status'] == base['sampling_basis']['status'] == 'supported' and 'degree' not in base['sampling_basis']
    record = synthetic_record()
    record['facts']['shift_abolished_by_specific_competitor']['support'] = 'implied'            # a fact: supported with no degree before
    record['quantities']['replicate_count']['support'] = 'about_something_else'
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'supported' and interpretations['binding_controls']['degree'] == pytest.approx(min(base['binding_controls'].get('degree', 1.0), 0.7))
    assert interpretations['sampling_basis']['status'] == 'supported' and interpretations['sampling_basis']['degree'] == pytest.approx(0.3)
    assert interpretations['binding_regime'] == base['binding_regime'] and interpretations['calibration_applicability'] == base['calibration_applicability']
    record['facts']['shift_abolished_by_specific_competitor'] = fact('no', ['s'], 'about_something_else')      # a status is never changed by support: conflicting keeps no degree
    verdict = convert(record)['extraction']['interpretations']['binding_controls']
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    record = synthetic_record()
    record['quantities']['kd_spread']['support'] = 'implied'
    assert convert(record)['extraction']['interpretations']['variance_correspondence']['degree'] == pytest.approx(0.7)
    record = synthetic_record()
    record['choice_support']['fit_model'] = 'implied'
    assert convert(record)['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.7)


def test_the_qualitative_effect_is_not_touched_by_support():
    record = qualitative_record()
    record['facts']['shift_detected']['support'] = 'about_something_else'
    effect = convert(record)['qualitative_effect']
    assert effect['statement'] == 'interaction_detected' and effect['support_refs']
