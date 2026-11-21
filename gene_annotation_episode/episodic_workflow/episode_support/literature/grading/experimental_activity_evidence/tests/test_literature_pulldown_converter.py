"""Pull-down / co-IP converter: the qualitative effect, the empty sheet cells, the criteria mapping and the null reasons."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pulldown_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_converter import CRITERIA_MAP, convert_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_grader import CRITERIA, grade_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.pulldown_cases import sparse_record, synthetic_record


def convert(record):
    return convert_pulldown(grade_pulldown(record))


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped)) == 16


def test_a_pulldown_has_no_effect_and_no_variance_but_a_qualitative_effect():
    converted = convert(synthetic_record())
    assert converted['extraction']['quantities']['effect'] is None and converted['extraction']['quantities']['effect_variance'] is None
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None and cells['effect_precision']['value'] is None
    assert converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant' and converted['null_components']['effect_variance'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_exp_synthetic_pulldown_1'], 'fold_enrichment': 12.0}
    assert converted['extraction']['assay_type'] == 'ligand_binding' and converted['extraction']['quantity_kind'] == 'relative_binding_response' and converted['experiment_type'] == 'pulldown'
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_prey_a', 'immobilized_preparation_ref': 'prep_bait_a', 'surface_ref': None, 'dataset_ref': 'dataset_pulldown_1'}
    assert converted['null_components']['recovery'] == 'a_pulldown_has_no_matrix_recovery_measurement'
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(CRITERIA_MAP, 'supported')
    assert all(item['support_refs'] for item in converted['extraction']['interpretations'].values())


def test_no_number_of_the_record_is_put_into_the_effect():
    converted = convert(synthetic_record())                      # the fold enrichment (12) and the percent of the input (4) are not binding constants
    assert 12.0 not in [cell['value'] for cell in converted['sheet']['cells'].values()]
    assert converted['sheet']['cells']['measured_effect']['reasons'] == ['effect_not_selected']


def test_the_statement_is_detected_not_detected_or_not_stated():
    record = synthetic_record()
    record['facts']['prey_detected_in_eluate'] = fact('no', ['s'])
    assert convert(record)['qualitative_effect'] == {'statement': 'interaction_not_detected', 'support_refs': ['s'], 'fold_enrichment': 12.0}
    record['facts']['prey_detected_in_eluate'] = fact('unknown')
    assert convert(record)['qualitative_effect'] == {'statement': 'interaction_not_stated', 'support_refs': [], 'fold_enrichment': 12.0}
    assert convert(sparse_record())['qualitative_effect']['fold_enrichment'] is None


def test_a_conflicting_member_makes_its_sheet_criterion_conflicting_an_unknown_one_unknown():
    record = synthetic_record()
    record['facts']['prey_absent_in_negative_control'] = fact('no', ['s'])                 # a sticky prey
    record['facts']['input_lane_shown'] = fact('unknown')
    record['quantities']['wash_count'] = point(1, 'count', 'w', ['s'])
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['binding_regime']['status'] == 'conflicting'
    assert interpretations['binding_species']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'
    record = synthetic_record()
    record['facts']['input_lane_shown'] = fact('unknown')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'supported'


def test_a_lysate_coip_without_direct_binding_leaves_the_species_criterion_unknown_not_conflicting():
    record = synthetic_record()
    record['facts']['direct_interaction_shown'] = fact('unknown')
    assert convert(record)['extraction']['interpretations']['binding_species']['status'] == 'unknown'


def test_a_not_applicable_member_is_dropped():
    record = synthetic_record()
    record['facts']['quantification_with_normalization'] = fact('not_applicable')
    interpretations = convert(record)['extraction']['interpretations']
    assert 'calibration_applicability' not in interpretations                    # its only member is not applicable: the sheet criterion is not selected
    record = synthetic_record()
    record['facts']['direct_interaction_shown'] = fact('not_applicable')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_species']['status'] == 'supported' and interpretations['binding_species']['support_refs'] == ['span_exp_synthetic_pulldown_1']


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_pulldown_converter as sheet
    assert (sheet.MIN_WASH_NACL_MM, sheet.WASH_NACL_ZERO_AGREEMENT_MM, sheet.MIN_WASH_DETERGENT_PERCENT, sheet.WASH_DETERGENT_ZERO_AGREEMENT_PERCENT, sheet.MIN_WASHES) == (150.0, 50.0, 0.05, 0.0, 3)
    assert (sheet.MIN_INCUBATION_MIN, sheet.INCUBATION_ZERO_AGREEMENT_MIN, sheet.MIN_FOLD_ENRICHMENT, sheet.ENRICHMENT_ZERO_AGREEMENT_FOLD, sheet.MIN_REPLICATES) == (30.0, 5.0, 3.0, 1.0, 3)


def test_the_degree_travels_into_the_sheet_criterion_and_is_the_weakest_member_degree():
    record = synthetic_record()
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['degree'] == 1.0 and interpretations['binding_parameter_definition']['degree'] == 1.0     # continuous members at full agreement
    assert 'degree' not in interpretations['sampling_basis'] and 'degree' not in interpretations['binding_controls']                  # a count and facts carry none
    record['quantities']['incubation_time'] = point(17.5, 'min', 'i', ['s'])                      # 0.5
    record['quantities']['nacl_wash'] = point(125.0, 'mM', 'n', ['s'])                            # 0.75
    record['quantities']['fold_enrichment'] = point(2.0, 'ratio', 'f', ['s'])                     # 0.5
    converted = convert(record)
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['degree'] == pytest.approx(0.5)
    assert interpretations['binding_parameter_definition']['degree'] == pytest.approx(0.5)
    assert converted['sheet']['interpretations']['binding_regime']['degree'] == interpretations['binding_regime']['degree']            # it travels into the sheet
    record['quantities']['incubation_time'] = point(3.0, 'min', 'i', ['s'])                       # conflicting: no degree
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'conflicting' and 'degree' not in interpretations['binding_regime']


def test_a_criterion_resting_on_a_weak_quote_gets_the_support_degree_and_a_direct_one_is_unchanged():
    base = convert(synthetic_record())['extraction']['interpretations']
    assert 'degree' not in base['sampling_basis'] and 'degree' not in base['binding_controls']
    record = synthetic_record()
    record['facts']['reciprocal_done']['support'] = 'implied'                                  # a fact: supported with no degree before
    record['quantities']['replicate_count']['support'] = 'about_something_else'
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'supported' and interpretations['binding_controls']['degree'] == pytest.approx(0.7)
    assert interpretations['sampling_basis']['status'] == 'supported' and interpretations['sampling_basis']['degree'] == pytest.approx(0.3)
    assert interpretations['binding_regime'] == base['binding_regime'] and interpretations['calibration_applicability'] == base['calibration_applicability']
    record['facts']['competition_disrupts_interaction']['support'] = 'about_something_else'      # the weakest member decides
    assert convert(record)['extraction']['interpretations']['binding_controls']['degree'] == pytest.approx(0.3)


def test_the_support_degree_multiplies_a_degree_the_sheet_already_gave_and_never_changes_a_status():
    record = synthetic_record()
    record['quantities']['incubation_time'] = point(17.5, 'min', 'i', ['s'], support='implied')      # 0.5 from the comparison, times 0.7
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['degree'] == pytest.approx(0.35)
    record['quantities']['incubation_time'] = point(3.0, 'min', 'i', ['s'], support='about_something_else')      # conflicting: no degree
    verdict = convert(record)['extraction']['interpretations']['binding_regime']
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    record = synthetic_record()
    record['facts']['prey_detected_in_eluate']['support'] = 'implied'
    converted = convert(record)
    assert converted['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.7)
    assert converted['qualitative_effect']['statement'] == 'interaction_detected' and converted['qualitative_effect']['support_refs']      # the qualitative effect stays as it was
