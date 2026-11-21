"""Pull-down / co-IP experiment records for the pull-down grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every criterion's supported
path. Its numbers: a GST pull-down of a purified bait from a cell lysate at endogenous levels, detected by western blot: the prey
signal of the specific capture 12 times that of the GST-alone control, 4 percent of the input recovered, an input lane of 5 percent, a
wash with 300 mM sodium chloride and 0.1 percent detergent four times, a 120 min incubation at 4 C, three independent experiments;
every control done and passed (prey absent from the GST-alone control, no binding to the beads without the bait, reciprocal done,
competition with the untagged protein abolishing the capture, interaction surviving benzonase, antibody validated with a knockdown,
bands quantified and normalized) and the interaction shown with purified proteins too.
sparse_record: only the statement that the prey was detected in the eluate; everything else is an unavailable operand or an 'unknown' fact.
real_record: see below (the published case).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pulldown_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, UNITS as UNIT_VOCABULARIES, VERSION, fact, point, unavailable

CHOICE_NAMES = ('detection_method', 'capture_format', 'protein_source', 'nuclease_treatment', 'crosslinker')
UNITS = {name: units[0] for name, units in UNIT_VOCABULARIES.items()}
UNITS['incubation_time'] = 'min'


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'bait_preparation_ref': None, 'prey_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'detection_method': None, 'capture_format': None, 'protein_source': None, 'nuclease_treatment': None, 'crosslinker': None, 'choice_support': dict.fromkeys(CHOICE_NAMES), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_pulldown'):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_interaction')
    record['spans'] = {'span_detected': {'locator': 'synthetic', 'quote': 'synthetic fixture: the prey was detected in the eluate'}}
    record['facts']['prey_detected_in_eluate'] = fact('yes', ['span_detected'])
    return record


def real_record():
    """The published Results paragraph on the co-immunoprecipitation of RECQ1 with Ku70/80 (Parvathaneni et al., PLoS ONE 2013, doi 10.1371/journal.pone.0062481,
    PMC3641083, CC0), only what it states about the experiment: a reciprocal immunoprecipitation with specific antibodies from HeLa cell nuclear extracts, western
    blots showing that the RECQ1 antibody co-precipitated Ku70 and Ku80 (the prey) and the Ku70/80 immunoprecipitation co-precipitated RECQ1, normal IgG pulling
    down none of them, and the interaction surviving benzonase treatment of the extract. It states no wash, incubation, input, replicate count, endogenous level,
    competition or specificity control. Preparations are unknown (the bait is RECQ1, the prey Ku70/80)."""
    record = blank_record('exp_recq1_ku_coip', 'source_pmc3641083', 'hypothesis_recq1_binds_ku70_80')
    locator = 'Results, RECQ1 exists in complex with Ku70/80 heterodimer'
    record['spans'] = {'span_detected': {'locator': locator, 'quote': 'RECQ1 antibody specifically co-precipitated Ku70 and Ku80'},
                       'span_reciprocal': {'locator': locator, 'quote': 'immunoprecipitation of Ku70/80 resulted in co-precipitation of RECQ1'},
                       'span_control_done': {'locator': locator, 'quote': 'Similar immunoprecipitation using normal IgG'},
                       'span_absent': {'locator': locator, 'quote': 'normal IgG failed to pull down RECQ1, Ku70 or Ku80'},
                       'span_nuclease': {'locator': locator, 'quote': 'the use of benzonase-treated extract in immunoprecipitation reaction did not abolish co-precipitation of Ku70/80 and RECQ1'},
                       'span_western': {'locator': locator, 'quote': 'Western blot analyses showed'},
                       'span_antibody': {'locator': locator, 'quote': 'using specific antibodies from HeLa cell nuclear extracts'},
                       'span_extract': {'locator': locator, 'quote': 'HeLa cell nuclear extracts'}}
    record['detection_method'], record['capture_format'], record['protein_source'], record['nuclease_treatment'] = 'western_blot', 'antibody', 'cell_lysate', 'benzonase'
    record['choice_support'].update(detection_method='direct', capture_format='direct', protein_source='direct', nuclease_treatment='direct')
    for name, span in (('prey_detected_in_eluate', 'span_detected'), ('reciprocal_done', 'span_reciprocal'), ('negative_control_done', 'span_control_done'), ('prey_absent_in_negative_control', 'span_absent'), ('interaction_survives_nuclease', 'span_nuclease')):
        record['facts'][name] = fact('yes', [span])
    record['preparations']['dataset_ref'] = 'dataset_pmc3641083_coip'
    return record


def synthetic_record(experiment_ref='exp_synthetic_pulldown_1', bait_prep='prep_bait_a', prey_prep='prep_prey_a', dataset='dataset_pulldown_1', assertion='hypothesis_synthetic_interaction'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'bait_preparation_ref': bait_prep, 'prey_preparation_ref': prey_prep, 'dataset_ref': dataset}
    values = {'fold_enrichment': 12.0, 'percent_input_recovered': 4.0, 'input_fraction': 5.0, 'nacl_wash': 300.0, 'detergent_wash': 0.1, 'wash_count': 4, 'incubation_time': 120.0, 'incubation_temperature': 4.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['detection_method'] = 'western_blot'
    record['capture_format'] = 'gst'
    record['protein_source'] = 'cell_lysate'
    record['nuclease_treatment'] = 'benzonase'
    record['crosslinker'] = 'none'
    record['choice_support'] = dict.fromkeys(CHOICE_NAMES, 'direct')
    record['facts'] = {name: fact('yes', refs) for name in FACTS}
    return record
