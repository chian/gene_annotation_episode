"""The real published co-immunoprecipitation paragraph on RECQ1 and Ku70/80 (Parvathaneni et al., PLoS ONE 2013, doi 10.1371/journal.pone.0062481, PMC3641083, CC0):
what the grader and the converter make of a record that holds only what the paragraph states about the experiment (a reciprocal immunoprecipitation with specific
antibodies from HeLa cell nuclear extracts, western blots, the RECQ1 antibody co-precipitating Ku70 and Ku80, the Ku70/80 immunoprecipitation co-precipitating RECQ1,
normal IgG pulling down none of the three, and the interaction surviving benzonase treatment of the extract). It states no wash, incubation, input lane, replicate
count, endogenous level, competition or specificity control, so nothing in it can cross a threshold: four criteria are supported by stated facts and the others are
unknown. A conflict would be a real one only if a stated fact or number failed a criterion; none does here (a stated 'no' or a number at or below a zero-agreement
value, such as a fold enrichment no larger than the control, would be needed; a count under a researched minimum now gets partial credit, not a conflict)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_converter import convert_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_grader import grade_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.pulldown_cases import real_record


def test_four_facts_are_supported_and_everything_else_is_unknown():
    graded = grade_pulldown(real_record())
    statuses = {name: item['status'] for name, item in graded['criteria'].items()}
    assert [name for name, status in statuses.items() if status == 'supported'] == ['prey_in_eluate', 'negative_control', 'reciprocal', 'nuclease']
    assert graded['criteria']['prey_in_eluate']['support_refs'] == ['span_detected'] and graded['criteria']['negative_control']['support_refs'] == ['span_absent']
    assert graded['criteria']['reciprocal']['support_refs'] == ['span_reciprocal'] and graded['criteria']['nuclease']['support_refs'] == ['span_nuclease']
    assert [name for name, status in statuses.items() if status == 'conflicting'] == []
    assert [name for name, status in statuses.items() if status == 'not_applicable'] == []
    assert graded['reasons']['wash_stringency'] == 'wash_stringency_not_given' and graded['reasons']['wash_count'] == 'wash_count_not_given'
    assert graded['reasons']['incubation'] == 'incubation_time_not_given' and graded['reasons']['enrichment'] == 'enrichment_not_given'
    assert graded['reasons']['input_lane'] == 'fact_unknown' and graded['reasons']['bait_minus_control'] == 'fact_unknown' and graded['reasons']['expression_level'] == 'fact_unknown'
    assert graded['reasons']['direct_interaction'] == 'direct_interaction_not_shown' and graded['reasons']['replicates'] == 'replicate_count_or_independence_unknown'
    native = graded['native']
    assert native['interaction'] == 'detected' and native['detection_method'] == 'western_blot' and native['capture_format'] == 'antibody'
    assert native['protein_source'] == 'cell_lysate' and native['nuclease_treatment'] == 'benzonase'


def test_the_converter_gives_no_effect_and_a_qualitative_detection():
    converted = convert_pulldown(grade_pulldown(real_record()))
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None
    assert converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_detected'], 'fold_enrichment': None}
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'unknown'
    assert interpretations['binding_parameter_definition']['status'] == 'unknown' and interpretations['sampling_basis']['status'] == 'unknown'
