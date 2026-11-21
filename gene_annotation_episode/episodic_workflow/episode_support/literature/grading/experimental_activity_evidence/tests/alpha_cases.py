"""AlphaScreen binding experiment records for the AlphaScreen grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: apparent KD 20 nM (standard error 2 nM), a competition Ki of
30 nM (ratio 1.5), an EC50 of 28 nM and an IC50 of 45 nM kept as separate values; twelve concentrations from 1 nM
(0.05 x KD) to 2048 nM (102.4 x KD); a top signal of 450000 cps over a background of 900 cps (ratio 500, also reported as 500)
and a Z' factor of 0.8; partners incubated 60 min; three independent experiments of triplicate wells; a four-parameter logistic
fit of a saturation titration with a fixed partner.
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an 'unknown' fact.
real_record: the published cross-titration of PMC4872087 (the paragraph 'matrix cross-titration', hook effect).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_alpha_record import CHOICE_FIELDS, EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

UNITS = {'kd': 'nM', 'ki': 'nM', 'ec50': 'nM', 'ic50': 'nM', 'kd_spread': 'nM', 'ki_spread': 'nM', 'signal_maximum': 'cps', 'signal_background': 'cps', 'signal_to_background': 'ratio', 'z_prime': 'ratio', 'bead_concentration': 'ug/mL', 'labelled_partner_concentration': 'nM', 'tagged_partner_concentration': 'nM', 'plate_well_count': 'count', 'titration_point_count': 'count', 'technical_replicate_count': 'count', 'incubation_time': 'min', 'bead_incubation_time': 'min', 'temperature': 'C', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'titrant_preparation_ref': None, 'fixed_partner_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series', 'support': None}, 'assay_format': None, 'titration_design': None, 'donor_bead': None, 'acceptor_bead': None, 'spread_kind': None, 'fit_model': None, 'choice_support': dict.fromkeys(CHOICE_FIELDS), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_alpha', kd=20.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_alpha_1', titrant_prep='prep_titrant_a', fixed_prep='prep_fixed_a', dataset='dataset_alpha_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'titrant_preparation_ref': titrant_prep, 'fixed_partner_preparation_ref': fixed_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'ki': kd * 1.5, 'ec50': kd * 1.4, 'ic50': kd * 2.25, 'kd_spread': spread, 'ki_spread': spread * 1.5, 'signal_maximum': 450000.0, 'signal_background': 900.0, 'signal_to_background': 500.0, 'z_prime': 0.8, 'bead_concentration': 20.0, 'labelled_partner_concentration': 5.0, 'tagged_partner_concentration': 10.0, 'plate_well_count': 384, 'titration_point_count': 12, 'technical_replicate_count': 3, 'incubation_time': 60.0, 'bead_incubation_time': 45.0, 'temperature': 25.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd / 20 * 2 ** step for step in range(12)], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['assay_format'] = 'saturation_titration'
    record['titration_design'] = 'fixed_partner_titration'
    record['donor_bead'] = 'streptavidin'
    record['acceptor_bead'] = 'nickel_chelate'
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = 'four_parameter_logistic'
    record['choice_support'] = dict.fromkeys(CHOICE_FIELDS, 'direct')      # a hand-built record: every stated choice is direct
    answers ={'counter_screen_done': 'yes', 'hook_effect_handled': 'yes', 'partner_concentration_below_kd': 'yes', 'signal_in_linear_range': 'yes', 'equilibrium_reached': 'yes', 'nonspecific_binding_checked': 'yes', 'capture_does_not_alter_binding': 'yes', 'light_protected': 'yes', 'avidity_excluded': 'yes', 'independent_experiments': 'yes', 'single_estimate_method': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    return record


def real_record():
    """The published matrix cross-titration of His-Spindlin1 and biotin-H3(1-23)K4me3 with streptavidin donor and Ni-NTA acceptor beads
    (Nucleic Acids Research 2016, doi 10.1093/nar/gkw089, PMC4872087), only what its Results paragraph on the optimal assay
    concentrations states: both bead types at 17 ug/mL, the cross-titration of the two partners, the hook effect that was observed and
    the concentrations (15 nM and 30 nM) chosen as a compromise between the assay window and a reliable prevention of the hook effect.
    It reports no KD, EC50, IC50 or Ki value, no signal, background or Z' value, no incubation time, temperature, plate format,
    replicate count or series list. Preparations are unknown."""
    record = blank_record('exp_spindlin1_alphalisa', 'source_pmc4872087', 'hypothesis_spindlin1_binds_h3k4me3')
    locator = 'Results, setup of the AlphaLISA based ligand screening assay'
    record['spans'] = {'span_beads': {'locator': locator, 'quote': '17 μg/ml for both, acceptor- and donor beads'},
                       'span_bead_kinds': {'locator': locator, 'quote': 'Ni-NTA acceptor beads and streptavidin donor beads'},
                       'span_design': {'locator': locator, 'quote': 'we conducted a matrix cross-titration of His-Spindlin1 and biotin-H3(1–23)K4me3'},
                       'span_hook': {'locator': locator, 'quote': 'a reliable prevention of the hook-effect'}}
    record['quantities']['bead_concentration'] = point(17.0, 'ug/mL', 'bead_concentration', ['span_beads'])
    record['donor_bead'] = 'streptavidin'
    record['acceptor_bead'] = 'nickel_chelate'
    record['titration_design'] = 'cross_titration'
    record['choice_support'].update({'donor_bead': 'direct', 'acceptor_bead': 'direct', 'titration_design': 'direct'})      # the stated choices
    record['facts']['hook_effect_handled'] = fact('yes', ['span_hook'])
    record['preparations']['dataset_ref'] = 'dataset_pmc4872087_alphalisa'
    return record
