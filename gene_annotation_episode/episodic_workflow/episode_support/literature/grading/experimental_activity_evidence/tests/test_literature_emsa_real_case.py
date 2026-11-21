"""The real published EMSA paragraph on SarA and the srn_9340 promoter (Insights into the regulation of small RNA expression: SarA represses the expression of two sRNAs in
Staphylococcus aureus, Nucleic Acids Research 2016, doi 10.1093/nar/gkw777, PMC5137438, PMID 27596601, CC BY-NC 4.0): what the grader and the converter make of a record that holds only what
the paragraph states about the experiment (purified SarA, a distinct complex with an apparent Kd of 11 +/- 0.2 nM, competition by a 10-fold excess of the unlabelled probe, no displacement by a
100-fold excess of an unlabelled non-specific fragment). It states no probe concentration, protein concentrations, buffer, incubation, gel, run, fit model, spread kind or replicate count, and its
second shifted band is not a number or a model, so nothing in it can cross a threshold: four criteria are supported by stated facts, the 10-fold excess is not tested against a threshold because the
competition is stated to have worked, and the others are unknown. A conflict would be a real one only if a stated fact or number failed a criterion; none does here (a stated 'no' or a number
under a minimum would be needed)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_converter import convert_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_grader import grade_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.emsa_cases import real_record


def test_four_facts_are_supported_and_everything_else_is_unknown():
    graded = grade_emsa(real_record())
    statuses = {name: item['status'] for name, item in graded['criteria'].items()}
    assert [name for name, status in statuses.items() if status == 'supported'] == ['shift_observed', 'specific_competition', 'nonspecific_competition', 'protein_identity']
    assert graded['criteria']['shift_observed']['support_refs'] == ['span_shift'] and graded['criteria']['specific_competition']['support_refs'] == ['span_specific']
    assert graded['criteria']['nonspecific_competition']['support_refs'] == ['span_nonspecific'] and graded['criteria']['protein_identity']['support_refs'] == ['span_purified']
    assert [name for name, status in statuses.items() if status == 'conflicting'] == []
    assert [name for name, status in statuses.items() if status == 'not_applicable'] == []            # the paragraph reports an apparent KD, so the KD criteria apply (and are unknown)
    assert graded['reasons']['probe_concentration'] == 'fact_unknown' and graded['reasons']['protein_range'] == 'fact_unknown' and graded['reasons']['titration_points'] == 'titration_point_count_not_given'
    assert graded['reasons']['saturation'] == 'fraction_shifted_not_given' and graded['reasons']['fit_model'] == 'fit_model_not_stated' and graded['reasons']['single_complex'] == 'shifted_species_count_not_given'
    assert graded['reasons']['mutant_probe'] == 'fact_unknown' and graded['reasons']['probe_alone_lane'] == 'fact_unknown' and graded['reasons']['equilibrium'] == 'fact_unknown'
    assert graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown'
    native = graded['native']
    assert native['interaction'] == 'detected' and native['kd_nM'] == 11.0 and native['probe_nM'] is None


def test_the_ten_fold_competitor_that_worked_is_not_a_conflict():
    graded = grade_emsa(real_record())            # a 10-fold excess is below the usual 50-fold, but the paragraph says it competed: supported, with the excess kept in the record
    assert graded['reasons']['specific_competition'] == 'facts_answered_yes' and graded['native']['quantities']['specific_competitor_excess']['value'] == 10.0


def test_the_converter_gives_the_kd_as_the_effect_and_no_variance_because_the_spread_kind_is_not_stated():
    converted = convert_emsa(grade_emsa(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == 11.0 and cells['effect_variance']['value'] is None
    assert converted['extraction']['quantities']['effect']['source_refs'] == ['span_kd'] and converted['null_components']['effect_variance'] == 'spread_kind_not_stated'
    assert 'qualitative_effect' not in converted and converted['extraction']['quantity_kind'] == 'binding_parameter'
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['binding_parameter_definition']['status'] == 'unknown' and interpretations['sampling_basis']['status'] == 'unknown'
    assert converted['dependence']['dataset_ref'] == 'dataset_pmc5137438_emsa' and converted['dependence']['analyte_preparation_ref'] is None
