"""The real published SEC-MALS paragraph on the MCU-NTD and the MCUb-NTD (The MCU and MCUb amino-terminal domains tightly interact: mechanisms for low conductance assembly of the
mitochondrial calcium uniporter complex, iScience 2024, doi 10.1016/j.isci.2024.109699, PMC11068563, PMID 38706857, CC BY 4.0): what the grader and the converter make of a record that
holds only what the paragraph states about the experiment (the mixture eluted in a single peak at an earlier elution volume than either protein alone; SDS-PAGE of the earlier fractions
of the mixture showed two bands; a heterodimer with a MALS molar mass of 21.7 +/- 0.4 kDa; the MCU-NTD alone, the larger by its stated theoretical mass, 13.6 kDa; stable heterodimers that
co-elute; SEC with in-line multi-angle light scattering). It states no elution volume, no theoretical mass of the complex, no injected molar concentration, column, buffer, temperature or
replicate, and no KD, so it is a qualitative result: four criteria are supported by stated facts, the stoichiometry criterion does not apply (no KD), and the others are unknown."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_record import point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_converter import _criterion, convert_sec
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_grader import grade_sec
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.sec_cases import real_record


def test_four_facts_are_supported_the_stoichiometry_does_not_apply_and_everything_else_is_unknown():
    graded = grade_sec(real_record())
    statuses = {name: item['status'] for name, item in graded['criteria'].items()}
    assert [name for name, status in statuses.items() if status == 'supported'] == ['complex_peak_observed', 'components_alone', 'complex_composition', 'complex_stable_on_column']
    assert graded['criteria']['complex_peak_observed']['support_refs'] == ['span_peak'] and graded['criteria']['components_alone']['support_refs'] == ['span_alone']
    assert graded['criteria']['complex_composition']['support_refs'] == ['span_sds'] and graded['criteria']['complex_stable_on_column']['support_refs'] == ['span_stable']
    assert [name for name, status in statuses.items() if status == 'conflicting'] == []
    assert [name for name, status in statuses.items() if status == 'not_applicable'] == ['stoichiometry']          # the paragraph reports no KD
    assert graded['reasons']['stoichiometry'] == 'no_apparent_kd_reported' and graded['reasons']['complex_stable_on_column'] == 'facts_answered_yes'
    assert graded['reasons']['elution_shift'] == 'elution_shift_not_given' and graded['reasons']['mals_mass'] == 'fact_unknown' and graded['reasons']['resin_interaction'] == 'fact_unknown'
    assert graded['reasons']['column_calibration'] == 'fact_unknown' and graded['reasons']['monodispersity'] == 'fact_unknown' and graded['reasons']['single_component_control'] == 'fact_unknown'
    assert graded['reasons']['titration_depletion'] == 'fact_unknown' and graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown'
    native = graded['native']
    assert native['interaction'] == 'detected' and native['kd_nM'] is None and native['shift_ml'] is None and native['detection'] == 'light_scattering'


def test_the_measured_mass_alone_is_not_compared_with_anything_the_paragraph_does_not_state():
    graded = grade_sec(real_record())                      # 21.7 kDa is stated, the mass the complex should have is not: the mass criterion is unknown, not a conflict
    assert graded['criteria']['mals_mass']['status'] == 'unknown' and graded['native']['mass_deviation_percent'] is None
    assert graded['native']['quantities']['complex_mass_measured']['value'] == 21.7 and graded['native']['quantities']['component_mass_measured_larger']['value'] == 13.6


def test_a_theoretical_mass_that_the_caller_adds_is_recorded_as_a_deviation_of_minus_16_percent_and_the_sheet_judges_it():
    """The paragraph gives the theoretical monomer masses of its two proteins (12.0098 and 13.8637 kDa) in sentences that the extraction does not add up. If a reader added them (25.8735 kDa), the
    measured 21.7 kDa is 16.1 percent below it. The grader only records that deviation (-16.13 percent); the sheet side (the converter) judges it: above the 10 percent agreement and below
    the 50 percent disagreement, so unknown. The shortfall is real: a heterodimer measured 16 percent lighter than the sum of its parts, on a column that dilutes the sample about twenty-fold
    (the paragraph says so), is what a complex that partly dissociates in the peak gives, and the paper itself calls the proteins mainly monomers 'under dilute conditions'."""
    record = real_record()
    record['spans']['span_theory'] = {'locator': 'derived by the test: 12.0098 + 13.8637', 'quote': 'a theoretical monomer mass of 12.0098\xa0kDa'}
    record['quantities']['complex_mass_theoretical'] = point(12.0098 + 13.8637, 'kDa', 'sum_of_monomers', ['span_theory'])
    graded = grade_sec(record)
    assert graded['reasons']['mals_mass'] == 'mass_deviation_recorded_for_the_sheet'
    assert graded['native']['mass_deviation_percent'] == pytest.approx(-16.13, abs=0.01)
    assert graded['native']['mass_measured'] == 21.7 and graded['native']['mass_theoretical'] == pytest.approx(25.8735)
    assert graded['native']['mass_support_refs'] == ['span_mass', 'span_theory']
    verdict = _criterion(graded, 'mals_mass')
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(0.847, abs=1e-3)                          # between 10 and 50 percent: supported with a degree
    assert convert_sec(graded)['extraction']['interpretations']['binding_parameter_definition']['status'] == 'unknown'      # the paragraph states no elution shift, so the sheet criterion stays unknown and carries no degree


def test_the_converter_reports_a_qualitative_detected_result_with_no_effect_and_unknown_interpretations():
    converted = convert_sec(grade_sec(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None
    assert converted['extraction']['quantity_kind'] == 'relative_binding_response' and converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_peak'], 'elution_shift_ml': None}
    interpretations = converted['extraction']['interpretations']
    assert {name: item['status'] for name, item in interpretations.items()} == dict.fromkeys(('binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis'), 'unknown')
    assert converted['dependence']['dataset_ref'] == 'dataset_pmc11068563_sec_mals' and converted['dependence']['analyte_preparation_ref'] is None
