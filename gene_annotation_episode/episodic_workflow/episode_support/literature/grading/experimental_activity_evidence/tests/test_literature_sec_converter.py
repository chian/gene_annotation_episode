"""SEC converter: the quantitative effect and variance (an apparent KD from peak areas), the qualitative effect (no KD), the criteria mapping, the null reasons, and the
gradual judgements of the recorded numbers (full credit at each researched value, partial credit on the worse side, no step, monotone)."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_converter import (
    COLUMN_DILUTION_FOLD, CRITERIA_MAP, ELUTION_SHIFT_ZERO_ML, MASS_FULL_AGREEMENT_PERCENT, MASS_RESOLVABLE_PERCENT, MASS_ZERO_AGREEMENT_PERCENT, MAX_POLYDISPERSITY,
    MIN_COUNT_FOR_A_SPREAD, MIN_ELUTION_SHIFT_ML, MIN_LOAD_OVER_KD, MIN_REPLICATES, MIN_SALT_MM, POLYDISPERSITY_ZERO, REFERENCE_ELUTION_VOLUME_ML, SALT_ZERO_MM,
    SECOND_SPECIES_MASS_MULTIPLE, STOICHIOMETRY_TOLERANCE, STOICHIOMETRY_ZERO_FOLD, JUDGES, _criterion, convert_sec)
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
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # two independent experiments: supported with partial credit, so the sd becomes 400 / 2
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(400.0 / 2)
    record['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])      # one experiment: supported (sqrt(1/3)), but an SD needs two experiments to be a spread
    assert judged(record, 'replicates')['status'] == 'supported' and MIN_COUNT_FOR_A_SPREAD == 2
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
    record['facts']['free_peak_decreases_with_titration'] = fact('no', ['s'])             # the free peak did not shrink with the titration
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['binding_regime']['status'] == 'conflicting'
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'
    record = synthetic_record()
    record['facts']['components_run_alone'] = fact('unknown')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'supported'


def test_a_low_load_lowers_the_degree_of_its_sheet_criterion_and_does_not_make_it_conflicting():
    record = synthetic_record()
    missing(record, 'loaded_volume')                                                       # no injected volume: the researched dilution COLUMN_DILUTION_FOLD
    record['quantities']['loaded_concentration'] = point(1000.0, 'nM', 'l', ['s'])        # five times the KD: half the researched multiple, partial credit, no step to conflicting
    regime = convert(record)['extraction']['interpretations']['binding_regime']
    assert regime['status'] == 'supported' and regime['degree'] == pytest.approx(0.7015, abs=1e-4)
    assert convert(synthetic_record())['extraction']['interpretations']['binding_regime']['degree'] == 1.0      # 25 times the KD: full credit


def test_the_sheet_judges_the_recorded_mass_deviation_with_its_own_thresholds():
    assert MASS_FULL_AGREEMENT_PERCENT == 10.0 and MASS_ZERO_AGREEMENT_PERCENT == 50.0
    record = synthetic_record()
    missing(record, 'component_mass_measured_smaller')                                     # no partner mass: the researched 50 percent is the zero end
    record['quantities']['complex_mass_theoretical'] = point(100.0, 'kDa', 't', ['s_theory'])
    for measured, expected, degree in ((100.0, 'supported', 1.0), (90.0, 'supported', 1.0), (110.0, 'supported', 1.0), (85.0, 'supported', 0.875), (115.0, 'supported', 0.875), (70.0, 'supported', 0.5),
                                       (51.0, 'supported', 0.025), (50.0, 'conflicting', None), (150.0, 'conflicting', None)):
        record['quantities']['complex_mass_measured'] = point(measured, 'kDa', 'm', ['s_mass'])
        graded = grade_sec(record)
        assert _criterion(graded, 'mals_mass')['status'] == expected, measured
        assert _criterion(graded, 'mals_mass').get('degree') == (pytest.approx(degree) if degree is not None else None), measured
        interpretation = convert_sec(graded)['extraction']['interpretations']['binding_parameter_definition']
        assert interpretation['status'] == expected, measured
        assert interpretation.get('degree') == (pytest.approx(degree) if degree is not None else None), measured       # the other members are at full credit (1.0)
    record['quantities']['complex_mass_measured'] = point(50.0, 'kDa', 'm', ['s_mass'])
    assert _criterion(grade_sec(record), 'mals_mass')['support_refs'] == ['s_mass', 's_theory']
    missing(record, 'complex_mass_theoretical')                                            # not both stated: the fact path, as the grader answered
    record['facts']['mals_mass_matches_complex'] = fact('yes', ['s'])
    assert _criterion(grade_sec(record), 'mals_mass')['status'] == 'supported'


def judged(record, name):
    return _criterion(grade_sec(record), name)


def test_the_zero_end_of_the_mass_is_the_smaller_partner_when_its_mass_is_stated():
    record = synthetic_record()
    record['quantities']['complex_mass_theoretical'] = point(100.0, 'kDa', 't', ['s_theory'])
    for smaller, measured, expected, degree in ((20.0, 90.0, 'supported', 1.0), (20.0, 85.0, 'supported', 0.5), (20.0, 115.0, 'supported', 0.5), (20.0, 80.0, 'conflicting', None),
                                                (20.0, 120.0, 'conflicting', None),
                                                (50.0, 85.0, 'supported', 0.875),          # equal partners: the researched 50 percent
                                                (60.0, 85.0, 'supported', 0.875),          # never beyond the researched 50 percent
                                                (35.0, 85.0, 'supported', 0.8),            # (35 - 15) / (35 - 10)
                                                (5.0, 85.0, 'supported', 0.5), (5.0, 95.0, 'supported', 1.0), (5.0, 80.0, 'conflicting', None)):      # a tiny partner: the zero end stays at the resolvable 20 percent
        record['quantities']['component_mass_measured_smaller'] = point(smaller, 'kDa', 'ms', ['s_smaller'])
        record['quantities']['complex_mass_measured'] = point(measured, 'kDa', 'm', ['s_mass'])
        verdict = judged(record, 'mals_mass')
        assert (verdict['status'], verdict['support_refs']) == (expected, ['s_mass', 's_theory', 's_smaller']), (smaller, measured)
        assert verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (smaller, measured)
    assert MASS_RESOLVABLE_PERCENT == 2 * MASS_FULL_AGREEMENT_PERCENT
    degrees = []                                                                           # a larger partner (better separation) never lowers the degree of the same deviation
    for smaller in (2.0, 10.0, 20.0, 25.0, 30.0, 40.0, 50.0, 70.0):
        record['quantities']['component_mass_measured_smaller'] = point(smaller, 'kDa', 'ms', ['s_smaller'])
        degrees.append(judged(record, 'mals_mass').get('degree', 0.0))
    assert degrees == sorted(degrees)
    record['quantities']['complex_mass_measured'] = point(85.0, 'kDa', 'm', ['s_mass'])      # the smaller partner's quote support is applied (the grader does not read that field)
    record['quantities']['component_mass_measured_smaller'] = point(20.0, 'kDa', 'ms', ['s_smaller'], support='implied')
    graded = grade_sec(record)
    assert _criterion(graded, 'mals_mass')['degree'] == pytest.approx(0.5)
    assert convert_sec(graded)['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.35)


def test_the_real_mass_pair_of_the_paper_is_supported_with_a_degree_of_about_085():
    record = synthetic_record()
    missing(record, 'component_mass_measured_smaller')                                     # the paper states the larger component's mass only
    record['quantities']['complex_mass_measured'] = point(21.7, 'kDa', 'm', ['s_mass'])
    record['quantities']['complex_mass_theoretical'] = point(12.0098 + 13.8637, 'kDa', 't', ['s_theory'])
    graded = grade_sec(record)
    assert graded['native']['mass_deviation_percent'] == pytest.approx(-16.13, abs=0.01) and graded['criteria']['mals_mass']['status'] == 'unknown'      # the grader only records it
    verdict = _criterion(graded, 'mals_mass')
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(0.847, abs=1e-3) and verdict['support_refs'] == ['s_mass', 's_theory']
    interpretation = convert_sec(graded)['extraction']['interpretations']['binding_parameter_definition']
    assert interpretation['status'] == 'supported' and interpretation['degree'] == pytest.approx(0.847, abs=1e-3)
    assert convert_sec(graded)['sheet']['interpretations']['binding_parameter_definition']['degree'] == interpretation['degree']        # it travels into the sheet


def test_the_sheet_holds_the_researched_constants_with_their_values():
    assert (MIN_ELUTION_SHIFT_ML, MAX_POLYDISPERSITY, MIN_LOAD_OVER_KD, MIN_SALT_MM, STOICHIOMETRY_TOLERANCE, MIN_REPLICATES) == (0.3, 1.05, 10.0, 100.0, 0.1, 3)      # the researched values, kept
    assert (ELUTION_SHIFT_ZERO_ML, POLYDISPERSITY_ZERO, SECOND_SPECIES_MASS_MULTIPLE, COLUMN_DILUTION_FOLD, SALT_ZERO_MM, STOICHIOMETRY_ZERO_FOLD) == (0.0, 1.125, 2.0, 10.0, 50.0, 2.0)
    assert (REFERENCE_ELUTION_VOLUME_ML, MASS_RESOLVABLE_PERCENT, MIN_COUNT_FOR_A_SPREAD) == (13.0, 20.0, 2)      # 2026-11-21: the column scale of the shift, the lowest mass zero end
    k = SECOND_SPECIES_MASS_MULTIPLE                                                       # POLYDISPERSITY_ZERO is the Mw/Mn of equal masses of a species and its dimer
    assert POLYDISPERSITY_ZERO == pytest.approx((1 + (k - 1) / 2) * (1 + (1 / k - 1) / 2))


def test_the_sheet_judges_the_elution_shift_gradually():
    record = synthetic_record()
    missing(record, 'component_elution_volume_earlier')                                    # a stated shift without the component's volume or the column's: the researched absolute 0.3 mL
    missing(record, 'column_volume')
    for value, expected, degree in ((0.3, 'supported', 1.0), (5.0, 'supported', 1.0), (0.29, 'supported', 0.99674), (0.15, 'supported', 0.5), (0.05, 'supported', 0.07407),
                                    (0.0, 'conflicting', None), (-0.5, 'conflicting', None)):
        record['quantities']['elution_volume_shift'] = point(value, 'mL', 'sh', ['s'])
        verdict = judged(record, 'elution_shift')
        assert (verdict['status'], verdict['support_refs']) == (expected, ['s']), value
        assert verdict.get('degree') == (pytest.approx(degree, abs=1e-5) if degree is not None else None), value
        assert convert(record)['extraction']['interpretations']['binding_parameter_definition']['status'] == expected
    missing(record, 'elution_volume_shift')
    missing(record, 'complex_elution_volume')
    assert judged(record, 'elution_shift') == {'status': 'unknown', 'support_refs': []}


def test_the_resolvable_shift_scales_with_the_papers_own_elution_volume():
    record = synthetic_record()                                                            # the earlier component alone elutes at 12.5 mL: full credit from 0.3 * 12.5 / 13 mL
    for value, expected, degree in ((0.29, 'supported', 1.0), (0.28, 'supported', 0.99747), (0.15, 'supported', 0.52998), (0.05, 'supported', 0.07972), (0.0, 'conflicting', None)):
        record['quantities']['elution_volume_shift'] = point(value, 'mL', 'sh', ['s'])
        verdict = judged(record, 'elution_shift')
        assert (verdict['status'], verdict['support_refs']) == (expected, ['s', 'span_exp_synthetic_sec_1']), value      # the volume the scale rests on is cited
        assert verdict.get('degree') == (pytest.approx(degree, abs=1e-5) if degree is not None else None), value
    for volume, shift, degree in ((REFERENCE_ELUTION_VOLUME_ML, 0.15, 0.5),              # on the reference column the scale is the researched value itself
                                  (1.3, 0.1, 1.0),                                         # a 2.4 mL microbore column: 0.1 mL is well resolved (the absolute rule gave 0.26)
                                  (65.0, 0.3, 0.104),                                      # a 120 mL preparative column: 0.3 mL is a fifth of the resolvable 1.5 mL (the absolute rule gave 1.0)
                                  (65.0, 1.5, 1.0)):
        record['quantities']['component_elution_volume_earlier'] = point(volume, 'mL', 'v', ['s_volume'])
        record['quantities']['elution_volume_shift'] = point(shift, 'mL', 'sh', ['s'])
        assert judged(record, 'elution_shift')['degree'] == pytest.approx(degree, abs=1e-5), (volume, shift)
    degrees = []                                                                           # the same shift on a larger column (wider peaks) never earns more
    for volume in (1.0, 5.0, 10.0, 13.0, 20.0, 40.0, 80.0):
        record['quantities']['component_elution_volume_earlier'] = point(volume, 'mL', 'v', ['s_volume'])
        record['quantities']['elution_volume_shift'] = point(0.3, 'mL', 'sh', ['s'])
        degrees.append(judged(record, 'elution_shift')['degree'])
    assert degrees == sorted(degrees, reverse=True)


def test_the_sheet_judges_the_stoichiometry_gradually_and_only_with_a_kd():
    record = synthetic_record()
    for ratio, expected, degree in ((1.0, 'supported', 1.0), (1.09, 'supported', 1.0), (0.91, 'supported', 1.0), (1.12, 'supported', 0.97778), (0.88, 'supported', 0.95960),
                                    (1.5, 'supported', 0.55556), (0.6, 'supported', 0.37037), (2.0, 'conflicting', None), (0.5, 'conflicting', None), (3.0, 'conflicting', None)):
        record['quantities']['stoichiometry_ratio'] = point(ratio, 'ratio', 'r', ['s'])
        verdict = judged(record, 'stoichiometry')
        assert verdict['status'] == expected, ratio
        assert verdict.get('degree') == (pytest.approx(degree, abs=1e-5) if degree is not None else None), ratio
    assert judged(record, 'stoichiometry')['support_refs'] == ['s']
    for ratio in (1.11, 1.25, 1.5, 1.8):                                                  # A:B and B:A name the same complex: the same degree either way round (the fold)
        record['quantities']['stoichiometry_ratio'] = point(ratio, 'ratio', 'r', ['s'])
        forward = judged(record, 'stoichiometry')['degree']
        record['quantities']['stoichiometry_ratio'] = point(1 / ratio, 'ratio', 'r', ['s'])
        assert judged(record, 'stoichiometry')['degree'] == pytest.approx(forward), ratio
    missing(record, 'kd')
    assert judged(record, 'stoichiometry')['status'] == 'not_applicable'


def test_the_sheet_judges_the_salt_only_when_the_buffer_fact_is_unknown_and_a_low_salt_is_conflicting():
    record = synthetic_record()
    record['facts']['buffer_rules_out_resin_interaction'] = fact('unknown')
    for value, unit, expected, degree in ((100.0, 'mM', 'supported', 1.0), (0.1, 'M', 'supported', 1.0), (99.0, 'mM', 'supported', 0.98289), (75.0, 'mM', 'supported', 0.54258),
                                          (51.0, 'mM', 'supported', 0.02402), (50.0, 'mM', 'conflicting', None), (0.04, 'M', 'conflicting', None), (0.0, 'mM', 'conflicting', None)):
        record['quantities']['salt_concentration'] = point(value, unit, 'salt', ['s'])
        verdict = judged(record, 'resin_interaction')
        assert (verdict['status'], verdict['support_refs']) == (expected, ['s']), (value, unit)      # a low salt is the paper's own buffer against the standard: cited
        assert verdict.get('degree') == (pytest.approx(degree, abs=1e-5) if degree is not None else None), (value, unit)
    # the mistake this replaces: at or below SALT_ZERO_MM the verdict was unknown (weighed with the type's unknown weight, 0.9) while 51 mM had a degree of about 0.02;
    # now the weight runs continuously from 1 at MIN_SALT_MM down to 0 at SALT_ZERO_MM, and never rises as the salt falls
    record['quantities']['salt_concentration'] = point(SALT_ZERO_MM, 'mM', 'salt', ['s'])
    assert convert(record)['extraction']['interpretations']['binding_controls']['status'] == 'conflicting'
    record['facts']['buffer_rules_out_resin_interaction'] = fact('no', ['s'])
    assert judged(record, 'resin_interaction')['status'] == 'conflicting'                  # the fact is the grader's, whatever the salt


def test_the_sheet_judges_the_load_over_the_kd_gradually():
    record = synthetic_record()                                                              # KD 200 nM
    missing(record, 'loaded_volume')                                                         # no injected volume: the researched dilution COLUMN_DILUTION_FOLD
    for loaded, unit, degree in ((2000.0, 'nM', 1.0), (2.0, 'uM', 1.0), (1999.0, 'nM', 0.99978), (1.0, 'uM', 0.70150), (200.0, 'nM', 0.21971), (20.0, 'nM', 0.02567)):
        record['quantities']['loaded_concentration'] = point(loaded, unit, 'l', ['s'])
        verdict = judged(record, 'complex_stable_on_column')
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(degree, abs=1e-5), (loaded, unit)
    assert len(judged(record, 'complex_stable_on_column')['support_refs']) == 2


def _fraction(c):
    """The fraction of an equimolar 1:1 pair in the complex at c times the KD, from the quadratic (1 - f)^2 c = f solved directly."""
    return ((2 * c + 1) - math.sqrt(4 * c + 1)) / (2 * c)


def test_the_dilution_on_the_column_comes_from_the_stated_injected_and_column_volumes():
    """The injected volume and the column volume (former grader gaps): dilution = sqrt(peak^2 + sample^2) / sample with the peak a tenth of the column; a bigger sample or a
    smaller column dilutes less, and the credit never falls as the dilution falls."""
    record = synthetic_record()
    record['quantities']['loaded_concentration'] = point(1000.0, 'nM', 'l', ['s_l'])           # five times the KD of 200 nM
    missing(record, 'loaded_volume')
    missing(record, 'column_volume')
    unstated = judged(record, 'complex_stable_on_column')['degree']                            # the researched 10-fold dilution
    assert unstated == pytest.approx(_fraction(5.0 / COLUMN_DILUTION_FOLD) / _fraction(MIN_LOAD_OVER_KD / COLUMN_DILUTION_FOLD))
    record['quantities']['loaded_volume'] = point(0.24, 'mL', 'v', ['s_v'])                      # 0.24 mL on the 24 mL reference column: 2.4 mL peak, dilution 10.05
    stated = judged(record, 'complex_stable_on_column')
    dilution = math.sqrt(2.4 ** 2 + 0.24 ** 2) / 0.24
    assert stated['degree'] == pytest.approx(_fraction(5.0 / dilution) / _fraction(MIN_LOAD_OVER_KD / COLUMN_DILUTION_FOLD))
    assert abs(stated['degree'] - unstated) < 0.01 and 's_v' in stated['support_refs']          # where the sample volume is a usual analytical one the two agree
    record['quantities']['loaded_volume'] = point(240.0, 'uL', 'v', ['s_v'])                     # the same volume in microlitres
    assert judged(record, 'complex_stable_on_column')['degree'] == pytest.approx(stated['degree'])
    degrees = []
    for volume in (0.02, 0.05, 0.1, 0.24, 0.5, 1.0, 2.0):                                        # a larger sample is less diluted: never a lower degree
        record['quantities']['loaded_volume'] = point(volume, 'mL', 'v', ['s_v'])
        verdict = judged(record, 'complex_stable_on_column')
        assert verdict['status'] == 'supported' and 0.0 < verdict['degree'] <= 1.0
        degrees.append(verdict['degree'])
    assert degrees == sorted(degrees) and degrees[0] < 0.2 and degrees[-1] == 1.0
    record['quantities']['loaded_volume'] = point(0.24, 'mL', 'v', ['s_v'])
    previous = None
    for column in (2.4, 6.0, 12.0, 24.0, 120.0):                                                 # a larger column dilutes more: never a higher degree
        record['quantities']['column_volume'] = point(column, 'mL', 'c', ['s_c'])
        verdict = judged(record, 'complex_stable_on_column')
        assert 's_c' in verdict['support_refs'] and (previous is None or verdict['degree'] <= previous + 1e-12)
        previous = verdict['degree']
    record['quantities']['column_volume'] = point(24.0, 'mL', 'c', ['s_c'])
    assert judged(record, 'complex_stable_on_column')['degree'] == pytest.approx(stated['degree'])     # the 24 mL stated is the reference column
    missing(record, 'loaded_volume')                                                             # a column volume alone does not change the researched dilution
    record['quantities']['column_volume'] = point(120.0, 'mL', 'c', ['s_c'])
    assert judged(record, 'complex_stable_on_column')['degree'] == pytest.approx(unstated)


def test_the_stated_column_volume_scales_the_resolvable_shift_when_the_earlier_elution_volume_is_not_stated():
    record = synthetic_record()
    missing(record, 'component_elution_volume_earlier')
    missing(record, 'column_volume')
    record['quantities']['elution_volume_shift'] = point(0.15, 'mL', 's', ['s_s'])
    absolute = judged(record, 'elution_shift')['degree']                                          # 0.15 of 0.3 mL: smoothstep at x = 0.5
    assert absolute == pytest.approx(0.5)
    record['quantities']['column_volume'] = point(12.0, 'mL', 'c', ['s_c'])                      # half the reference column: the full-credit shift is 0.15 mL
    verdict = judged(record, 'elution_shift')
    assert verdict['degree'] == pytest.approx(1.0) and 's_c' in verdict['support_refs']
    record['quantities']['column_volume'] = point(120.0, 'mL', 'c', ['s_c'])                     # five times the reference: the full-credit shift is 1.5 mL, 0.15 mL is x = 0.1
    assert judged(record, 'elution_shift')['degree'] == pytest.approx(0.1 ** 2 * (3 - 2 * 0.1))
    record['quantities']['component_elution_volume_earlier'] = point(13.0, 'mL', 'v', ['s_v'])   # the earlier component's own volume wins over the column volume
    verdict = judged(record, 'elution_shift')
    assert verdict['degree'] == pytest.approx(0.5) and 's_c' not in verdict['support_refs'] and 's_v' in verdict['support_refs']


def test_the_smaller_components_mass_support_comes_from_the_declared_reads():
    record = synthetic_record()
    record['quantities']['component_mass_measured_smaller'] = point(17.6, 'kDa', 'm', ['s_m'], support='implied')
    graded = grade_sec(record)
    assert 'implied' in graded['native']['support']['mals_mass']                                  # the criteria declare the field, so the grader keeps its support
    assert convert_sec(graded)['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.7)


def test_the_sheet_judges_the_polydispersity_gradually():
    record = synthetic_record()
    for value, expected, degree in ((1.05, 'supported', 1.0), (1.0, 'supported', 1.0), (1.06, 'supported', 0.93095), (1.1, 'supported', 0.57735), (1.12, 'supported', 0.25820),
                                    (1.125, 'conflicting', None), (1.5, 'conflicting', None)):
        record['quantities']['polydispersity'] = point(value, 'ratio', 'p', ['s'])
        verdict = judged(record, 'monodispersity')
        assert (verdict['status'], verdict['support_refs']) == (expected, ['s']), value
        assert verdict.get('degree') == (pytest.approx(degree, abs=1e-5) if degree is not None else None), value


def test_the_sheet_judges_the_replicate_count_as_the_precision_of_the_mean_and_its_independence():
    record = synthetic_record()
    for count, independent, expected, degree in ((3, 'yes', 'supported', 1.0), (10, 'yes', 'supported', 1.0), (2, 'yes', 'supported', 0.81650), (2, 'unknown', 'unknown', None),
                                                 (1, 'yes', 'supported', 0.57735),         # one experiment is less evidence, never evidence against (it was conflicting: a mistake)
                                                 (1, 'unknown', 'unknown', None), (3, 'unknown', 'unknown', None)):
        record['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        record['facts']['independent_experiments'] = fact(independent, ['s'] if independent != 'unknown' else [])
        verdict = judged(record, 'replicates')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree, abs=1e-5) if degree is not None else None), (count, independent)
    record['facts']['independent_experiments'] = fact('no', ['s'])                           # a stated 'no' is a fact the grader judges
    assert judged(record, 'replicates')['status'] == 'conflicting'
    missing(record, 'replicate_count')
    record['facts']['independent_experiments'] = fact('yes', ['s'])
    assert judged(record, 'replicates')['status'] == 'unknown'


# each judge on its own native field: (the field, its refs, the researched value, values from worse to better)
SWEEPS = {
    ('elution_shift', 'elution_shift_recorded_for_the_sheet'): ('shift_ml', 'shift_refs', MIN_ELUTION_SHIFT_ML, [0.01 * i for i in range(1, 60)]),
    ('stoichiometry', 'stoichiometry_recorded_for_the_sheet'): ('stoichiometry_ratio', 'stoichiometry_refs', 1 + STOICHIOMETRY_TOLERANCE, [2.0 - 0.02 * i for i in range(1, 50)]),
    ('resin_interaction', 'salt_recorded_for_the_sheet'): ('salt_mM', 'salt_refs', MIN_SALT_MM, [50.0 + 2.0 * i for i in range(1, 50)]),
    ('complex_stable_on_column', 'load_over_kd_recorded_for_the_sheet'): ('load_over_kd', 'load_refs', MIN_LOAD_OVER_KD, [0.25 * i for i in range(1, 80)]),
    ('monodispersity', 'polydispersity_recorded_for_the_sheet'): ('polydispersity', 'polydispersity_refs', MAX_POLYDISPERSITY, [1.124 - 0.002 * i for i in range(0, 60)]),
    ('replicates', 'replicate_count_recorded_for_the_sheet'): ('replicate_count', 'replicate_refs', MIN_REPLICATES, [1, 2, 3, 4, 6]),
    ('mals_mass', 'mass_deviation_recorded_for_the_sheet'): ('mass_deviation_percent', 'mass_support_refs', MASS_FULL_AGREEMENT_PERCENT, [49.0 - 1.0 * i for i in range(0, 49)]),
}


UNSTATED = {'status': 'unavailable', 'value': None, 'source_refs': []}
# the record quantities the judges read beside the grader's facts: unstated (the researched absolute scales), or stated (the paper's own scale)
SCALES = {'unstated': {'component_elution_volume_earlier': UNSTATED, 'component_mass_measured_smaller': UNSTATED},
          'stated': {'component_elution_volume_earlier': point(40.0, 'mL', 'v', ['s_v']), 'component_mass_measured_smaller': point(30.0, 'kDa', 'm', ['s_m'])}}
# the full-credit value of each judge on the stated scales (40 mL: 0.3 * 40 / 13 mL; the 30 kDa partner of a 100 kDa complex only moves the zero end)
STATED_RESEARCHED = {'shift_ml': MIN_ELUTION_SHIFT_ML * 40.0 / REFERENCE_ELUTION_VOLUME_ML}


def _degree(judge, field, refs, value, scale='unstated'):
    verdict = judge({field: value, refs: ['s'], 'replicate_independent': 'yes', 'quantities': SCALES[scale], 'mass_theoretical': 100.0,
                     'loaded_mL': None, 'loaded_refs': [], 'column_mL': None, 'column_refs': []})
    return verdict.get('degree', 0.0 if verdict['status'] == 'conflicting' else None)


@pytest.mark.parametrize('scale', list(SCALES))
@pytest.mark.parametrize('key', list(JUDGES))
def test_every_judge_is_monotone_bounded_and_has_no_step_at_its_researched_value(key, scale):
    field, refs, researched, values = SWEEPS[key]
    if scale == 'stated':
        researched = STATED_RESEARCHED.get(field, researched)
        values = [v * researched / SWEEPS[key][2] for v in values] if field == 'shift_ml' else values
    judge = JUDGES[key]
    degrees = [_degree(judge, field, refs, v, scale) for v in values]
    known = [d for d in degrees if d is not None]
    assert all(0.0 <= d <= 1.0 for d in known)                                              # bounded
    assert known == sorted(known)                                                           # a better value never lowers the degree
    assert _degree(judge, field, refs, researched, scale) == pytest.approx(1.0)             # full credit at the researched value
    step = {'shift_ml': -0.01, 'stoichiometry_ratio': 0.01, 'salt_mM': -1.0, 'load_over_kd': -0.1, 'polydispersity': 0.001, 'replicate_count': -1, 'mass_deviation_percent': 1.0}[field]
    just_worse = _degree(judge, field, refs, researched + step, scale)                      # just on the worse side of the researched value: partial credit, not 0
    assert just_worse is not None and 0.0 < just_worse < 1.0, (key, just_worse)


def test_no_judge_returns_unknown_for_a_stated_value_so_its_weight_never_jumps_above_a_low_degree():
    # unknown is weighed with the type's unknown weight (0.9); a stated value is judged on its curve down to 0 and then conflicting (weight 0), never unknown
    worst = {'shift_ml': [0.0, -0.5], 'stoichiometry_ratio': [2.0, 3.0], 'salt_mM': [0.0, 30.0, 50.0], 'load_over_kd': [0.01], 'polydispersity': [1.125, 1.4], 'mass_deviation_percent': [50.0, 80.0]}
    for key, (field, refs, researched, values) in SWEEPS.items():
        if field == 'replicate_count':
            assert _degree(JUDGES[key], field, refs, 1) == pytest.approx(math.sqrt(1 / MIN_REPLICATES))      # one stated experiment: low partial credit, not conflicting
            continue                                                                        # unknown there means the independence is not stated, another fact
        for scale in SCALES:
            degrees = [_degree(JUDGES[key], field, refs, v, scale) for v in worst[field] + values + [researched]]
            assert None not in degrees, (key, scale)
            if field == 'load_over_kd':
                assert degrees[0] < 0.01                                                    # never conflicting by design: the credit runs towards 0 with the load
            else:
                assert degrees[0] == 0.0, (key, scale)                                      # the worst end is conflicting (weight 0), continuous with the curve


def test_a_judge_is_not_reached_when_the_value_is_not_stated():
    record = synthetic_record()
    for name in ('elution_volume_shift', 'complex_elution_volume', 'stoichiometry_ratio', 'loaded_concentration', 'polydispersity', 'replicate_count', 'complex_mass_theoretical'):
        missing(record, name)
    record['facts']['buffer_rules_out_resin_interaction'] = fact('unknown')
    missing(record, 'salt_concentration')
    graded = grade_sec(record)
    assert not [name for name in CRITERIA if (name, graded['reasons'][name]) in JUDGES]       # nothing recorded for the sheet: unknown or the fact decides, never a degree of 0
    assert {name: _criterion(graded, name)['status'] for name in ('elution_shift', 'stoichiometry', 'resin_interaction', 'replicates')} == dict.fromkeys(('elution_shift', 'stoichiometry', 'resin_interaction', 'replicates'), 'unknown')


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
    assert base['binding_controls']['status'] == base['sampling_basis']['status'] == 'supported' and base['sampling_basis']['degree'] == 1.0      # three replicates: full credit
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
    missing(record, 'component_mass_measured_smaller')                                     # the researched 50 percent zero end
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
