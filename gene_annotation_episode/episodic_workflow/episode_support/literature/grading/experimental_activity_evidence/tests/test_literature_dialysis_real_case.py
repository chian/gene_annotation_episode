"""The real published equilibrium dialysis text (Perfluoroalkyl Acid Binding with Peroxisome Proliferator-Activated Receptors alpha, gamma and delta, and Fatty Acid Binding Proteins by Equilibrium Dialysis with a
Comparison of Methods, Toxics 2021, 9(3), 45, doi 10.3390/toxics9030045, PMC7996760, PMID 33652875, CC BY 4.0): what the grader, the converter and the merger make of two records that hold only what the text states.

1. The Methods paragraphs: a Slide-a-Lyzer mini dialysis cup (10 kDa cutoff) in a tube with 1.2 mL of phosphate buffered saline (pH 7.4), 100 uL in the cup, a membrane impermeable to the proteins, 36 h to reach equilibrium, in
   duplicate. No KD and no result: a qualitative record with no statement of binding. Two criteria are supported (the time of 36 h is at least the minimum; the protein is retained), none is conflicting.
2. The Results paragraph on PFHxA and PPAR-alpha: binding observed by EqD, KD 0.097 uM (97 nM). A quantitative record with no spread, so the effect is the KD and the variance is unavailable."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_binding_merger import merge_binding
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_converter import _criterion, convert_dialysis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_grader import grade_dialysis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.dialysis_cases import real_kd_record, real_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.test_literature_binding_merger_spa import spr


def test_the_methods_paragraphs_support_the_equilibration_time_and_the_retained_protein_and_everything_else_is_unknown():
    graded = grade_dialysis(real_record())
    statuses = {name: _criterion(graded, name)['status'] for name in graded['criteria']}      # the sheet judges the recorded time of 36 h
    assert [name for name, status in statuses.items() if status == 'supported'] == ['equilibrium', 'protein_retained']
    assert _criterion(graded, 'equilibrium')['support_refs'] == ['span_time'] and graded['criteria']['protein_retained']['support_refs'] == ['span_retained']
    assert [name for name, status in statuses.items() if status == 'conflicting'] == []
    assert [name for name, status in statuses.items() if status == 'not_applicable'] == ['protein_level', 'free_fraction_measurable', 'concentration_series', 'fit_model']      # the paragraphs report no KD and no fraction
    assert graded['reasons']['equilibrium'] == 'equilibration_time_recorded_for_the_sheet' and graded['reasons']['binding_observed'] == 'fact_unknown' and graded['reasons']['volume_shift'] == 'fact_unknown'
    assert graded['reasons']['ligand_depletion'] == 'bound_or_protein_concentration_not_given' and graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown'
    native = graded['native']
    assert native['interaction'] is None and native['kd_nM'] is None and native['equilibration_h'] == 36.0 and native['separation_method'] == 'equilibrium_dialysis' and native['device_type'] == 'dialysis_cup'


def test_the_36_hours_are_a_time_not_a_time_course_so_the_equilibrium_fact_stays_unknown():
    record = real_record()
    assert record['facts']['equilibrium_time_course_shown']['answer'] == 'unknown'        # 'to reach equilibrium' is what the time was meant to do
    assert _criterion(grade_dialysis(record), 'equilibrium')['support_refs'] == ['span_time']


def test_the_converter_reports_a_qualitative_result_with_no_statement_of_binding_for_the_methods_paragraphs():
    converted = convert_dialysis(grade_dialysis(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and converted['extraction']['quantity_kind'] == 'relative_binding_response'
    assert converted['qualitative_effect'] == {'statement': 'interaction_not_stated', 'support_refs': [], 'percent_bound': None}
    interpretations = {name: item['status'] for name, item in converted['extraction']['interpretations'].items()}
    assert interpretations == dict.fromkeys(('binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis'), 'unknown')      # each sheet criterion has an unknown member
    assert converted['dependence']['dataset_ref'] == 'dataset_pmc7996760_eqd_methods' and converted['dependence']['analyte_preparation_ref'] is None


def test_the_results_paragraph_is_quantitative_with_the_kd_as_the_effect_and_no_variance():
    graded = grade_dialysis(real_kd_record())
    assert graded['native']['kd_nM'] == pytest.approx(97.0) and graded['native']['interaction'] == 'detected'
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'supported'] == ['binding_observed']
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'conflicting'] == []
    assert graded['reasons']['concentration_series'] == 'kd_or_series_missing' and graded['reasons']['fit_model'] == 'fit_model_not_stated' and graded['reasons']['protein_level'] == 'fact_unknown'
    converted = convert_dialysis(graded)
    assert converted['extraction']['quantity_kind'] == 'binding_parameter' and converted['extraction']['quantities']['effect']['value'] == pytest.approx(97.0)
    assert converted['null_components']['effect_variance'] == 'kd_spread_not_given' and 'qualitative_effect' not in converted
    assert converted['sheet']['cells']['measured_effect']['value'] == pytest.approx(97.0) and converted['sheet']['cells']['effect_variance']['value'] is None


def test_the_real_records_in_a_row_with_an_spr_pool_only_the_numbers_and_the_variance_stays_unavailable_for_the_real_kd():
    methods = convert_dialysis(grade_dialysis(real_record()))
    result = convert_dialysis(grade_dialysis(real_kd_record()))
    row = merge_binding([methods, spr(kd=30.0, spread=3.0)])
    assert row['cells']['measured_effect']['value'] == pytest.approx(30.0) and row['cells']['effect_variance']['value'] == pytest.approx(9.0)
    assert row['qualitative']['experiment_refs'] == ['exp_pfas_protein_eqd_methods'] and row['qualitative']['statements'] == {'exp_pfas_protein_eqd_methods': 'interaction_not_stated'}
    both = merge_binding([result, spr(kd=30.0, spread=3.0)])
    assert both['cells']['measured_effect']['status'] == 'conditional' and both['cells']['effect_variance']['value'] is None            # the real KD has no spread, so no weights
    assert both['cells']['measured_effect']['value'] == pytest.approx((97.0 + 30.0) / 2) and both['counts'] == {'experiments': 2, 'independent_groups': 1}      # the real record's preparations are unknown, so it is dependent on the SPR
