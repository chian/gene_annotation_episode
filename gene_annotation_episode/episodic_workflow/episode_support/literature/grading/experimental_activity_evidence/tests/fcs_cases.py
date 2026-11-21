"""FCS binding titration records for the FCS grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: KD 20 nM (standard error 2 nM); the labelled partner held at 2 nM
(0.1 x KD), 0.8 molecules in the confocal volume; free diffusion time 60 us and bound 108 us (ratio 1.8), free diffusion
coefficient 280 um2/s and bound 156 um2/s (ratio about 1.79), a complex of 6 times the mass (cube root 1.817); the fraction bound
reaches 92 percent; twelve titrant concentrations from 1 nM (0.05 x KD) to 2048 nM (102.4 x KD); 20 min incubation; each
measurement 30 s repeated 5 times (150 s); 25 C; three independent titrations; a two-component fit with the free time fixed.
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an 'unknown' fact.
real_record: the published measurement of the CLN3 aptamer binding the c-Met protein by FCS (PMC10782416), only what its
Results and Methods paragraphs state.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fcs_record import CHOICE_FIELDS, EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

UNITS = {'kd': 'nM', 'kd_spread': 'nM', 'labelled_concentration': 'nM', 'free_diffusion_time': 'us', 'free_diffusion_time_spread': 'us', 'bound_diffusion_time': 'us', 'free_diffusion_coefficient': 'um2/s', 'bound_diffusion_coefficient': 'um2/s', 'fraction_bound_maximum': 'percent', 'particle_number': 'molecules', 'detection_volume': 'fL', 'structure_parameter': 'ratio', 'mass_ratio': 'ratio', 'brightness': 'kHz', 'laser_power': 'uW', 'measurement_time': 's', 'measurement_repeat_count': 'count', 'titration_point_count': 'count', 'incubation_time': 'min', 'temperature': 'C', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'titrant_preparation_ref': None, 'fixed_partner_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series', 'support': None}, 'spread_kind': None, 'fit_model': None, 'diffusion_model': None, 'readout_signal': None, 'choice_support': dict.fromkeys(CHOICE_FIELDS), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_fcs', kd=20.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_fcs_1', titrant_prep='prep_titrant_a', fixed_prep='prep_labelled_a', dataset='dataset_fcs_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'titrant_preparation_ref': titrant_prep, 'fixed_partner_preparation_ref': fixed_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'kd_spread': spread, 'labelled_concentration': kd / 10, 'free_diffusion_time': 60.0, 'free_diffusion_time_spread': 4.0, 'bound_diffusion_time': 108.0, 'free_diffusion_coefficient': 280.0, 'bound_diffusion_coefficient': 156.0, 'fraction_bound_maximum': 92.0, 'particle_number': 0.8, 'detection_volume': 0.66, 'structure_parameter': 5.2, 'mass_ratio': 6.0, 'brightness': 12.0, 'laser_power': 5.0, 'measurement_time': 30.0, 'measurement_repeat_count': 5, 'titration_point_count': 12, 'incubation_time': 20.0, 'temperature': 25.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd / 20 * 2 ** step for step in range(12)], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = '1:1'
    record['diffusion_model'] = 'two_component'
    record['readout_signal'] = 'diffusion_time'
    record['choice_support'] = dict.fromkeys(CHOICE_FIELDS, 'direct')      # a hand-built record: every stated choice is direct
    answers ={'confocal_volume_calibrated': 'yes', 'triplet_state_modelled': 'yes', 'free_diffusion_time_fixed': 'yes', 'brightness_change_accounted': 'yes', 'crosstalk_corrected': 'yes', 'background_corrected': 'yes', 'aggregates_checked': 'yes', 'photobleaching_or_saturation_checked': 'yes', 'surface_adsorption_prevented': 'yes', 'labelling_does_not_alter_binding': 'yes', 'nonbinding_control_done': 'yes', 'labelled_partner_at_or_below_kd': 'yes', 'tight_binding_considered': 'yes', 'equilibrium_reached': 'yes', 'independent_titrations': 'yes', 'single_estimate_method': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    return record


def real_record():
    """The published FCS titration of the dye-conjugated CLN3 aptamer with the c-Met protein (Analytical Chemistry 2023, doi
    10.1021/acs.analchem.3c03341, PMC10782416), from its Results paragraphs 'Detection of Aptamer-Protein Interaction with FCS',
    'Measurement of Binding Affinity' and the following control paragraph, and from its Methods paragraph 'FCS Instrumentation and
    Acquisition': KD 5 +/- 1 nM (the kind of the uncertainty is not stated), 100 pM of the labelled aptamer, a free diffusion time of
    0.37 ms and a bound one of 1.2 ms (free and bound diffusion coefficients of about 90 and 30 um2/s), curves fitted with a single
    effective diffusing species (an apparent time against the free and the bound reference times), a laser power of about 3 uW, a
    measurement of 180 s with three repetitions, titrations independently replicated four times, and a mutated aptamer and an IgG
    as non-binding controls. Only what the paragraphs state is filled: the c-Met concentrations are a range (0 to 100 nM), not a
    list; 'a simple binding model' is not named; no maximum fraction bound, particle number, incubation, calibration with a
    reference dye, correction or aggregate check is stated. Preparations are unknown."""
    record = blank_record('exp_cln3_cmet_fcs', 'source_pmc10782416', 'hypothesis_cln3_binds_cmet')
    record['spans'] = {'span_kd': {'locator': 'Results, Measurement of Binding Affinity', 'quote': 'KD = 5 ± 1 nM'},
                       'span_labelled': {'locator': 'Results, Measurement of Binding Affinity', 'quote': '100 pM of fluorescent CLN3'},
                       'span_free_time': {'locator': 'Results, Detection of Aptamer-Protein Interaction with FCS', 'quote': 'τD = (0.37 ± 0.03) ms was found for the free aptamer'},
                       'span_bound_time': {'locator': 'Results, Detection of Aptamer-Protein Interaction with FCS', 'quote': 'τD = (1.2 ± 0.1) ms, was found for the aptamer exposed to an excess of c-Met'},
                       'span_free_d': {'locator': 'Results, Detection of Aptamer-Protein Interaction with FCS', 'quote': 'A D ∼90 μm2/s was calculated for free CLN3'},
                       'span_bound_d': {'locator': 'Results, Detection of Aptamer-Protein Interaction with FCS', 'quote': 'A D ∼30 μm2/s was found for CLN3 exposed to an excess of c-Met'},
                       'span_model': {'locator': 'Results, Measurement of Binding Affinity', 'quote': 'a model comprising a single effective diffusing species'},
                       'span_readout': {'locator': 'Results, Measurement of Binding Affinity', 'quote': 'comparing the apparent τD obtained by the fit'},
                       'span_power': {'locator': 'Methods, FCS Instrumentation and Acquisition', 'quote': 'The laser power on the sample was typically adjusted to ∼3 μW'},
                       'span_time': {'locator': 'Methods, FCS Instrumentation and Acquisition', 'quote': '180 s for other measurements'},
                       'span_repeats': {'locator': 'Methods, FCS Instrumentation and Acquisition', 'quote': 'with three repetitions'},
                       'span_replicates': {'locator': 'Methods, FCS Instrumentation and Acquisition', 'quote': 'were independently replicated four times'},
                       'span_control': {'locator': 'Results, control experiments', 'quote': 'did not lead to any appreciable change in the measured τD and the calculated fraction bound'},
                       'span_other_method': {'locator': 'Results, Measurement of Binding Affinity', 'quote': 'a value obtained by biolayer interferometry'}}
    quantities = {'kd': (5.0, 'nM', 'span_kd'), 'kd_spread': (1.0, 'nM', 'span_kd'), 'labelled_concentration': (100.0, 'pM', 'span_labelled'),
                  'free_diffusion_time': (0.37, 'ms', 'span_free_time'), 'free_diffusion_time_spread': (0.03, 'ms', 'span_free_time'), 'bound_diffusion_time': (1.2, 'ms', 'span_bound_time'),
                  'free_diffusion_coefficient': (90.0, 'um2/s', 'span_free_d'), 'bound_diffusion_coefficient': (30.0, 'um2/s', 'span_bound_d'),
                  'laser_power': (3.0, 'uW', 'span_power'), 'measurement_time': (180.0, 's', 'span_time'), 'measurement_repeat_count': (3, 'count', 'span_repeats'),
                  'replicate_count': (4, 'count', 'span_replicates')}
    for name, (value, unit, span) in quantities.items():
        record['quantities'][name] = point(value, unit, name, [span])
    record['diffusion_model'] = 'one_component'
    record['readout_signal'] = 'diffusion_time'
    record['choice_support'].update({'diffusion_model': 'direct', 'readout_signal': 'direct'})      # both quotes state the choice themselves
    record['facts']['independent_titrations'] = fact('yes', ['span_replicates'])
    record['facts']['nonbinding_control_done'] = fact('yes', ['span_control'])
    record['facts']['single_estimate_method'] = fact('no', ['span_other_method'])
    record['preparations']['dataset_ref'] = 'dataset_pmc10782416_fcs'
    return record
