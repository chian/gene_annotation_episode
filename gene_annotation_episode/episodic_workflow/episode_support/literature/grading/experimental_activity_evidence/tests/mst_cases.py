"""MST experiment records for the MST grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: direct-titration KD 20 nM (standard error 2 nM) and a
competition Ki 40 nM (standard error 4 nM; ratio 2.0), EC50 30 nM; a detected partner held at 5 nM (0.25 x KD); a
change of Fnorm of 12 per mille with a signal-to-noise of 18; excitation LED power 40 percent and infrared laser power 60
percent; F-hot read 1.5 s after the laser is switched on (thermophoresis); twelve titrant concentrations from 1 nM
(0.05 x KD) to 2048 nM (102.4 x KD); 15 min, 25 C; three independent titrations.
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an 'unknown' fact.
real_record: the published MST measurement of NHS-RED labelled BmpA binding thymidine (PMC13325309), only what its Results
and Methods paragraphs state.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_mst_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

CHOICE_NAMES = ('assay_format', 'spread_kind', 'fit_model', 'readout_signal', 'capillary_type', 'label_type')

UNITS = {'kd': 'nM', 'ki': 'nM', 'ec50': 'nM', 'kd_spread': 'nM', 'ki_spread': 'nM', 'labelled_concentration': 'nM', 'fnorm_amplitude': 'permille', 'fnorm_noise': 'permille', 'signal_to_noise': 'ratio', 'led_power': 'percent', 'ir_laser_power': 'percent', 'fhot_time': 's', 'titration_point_count': 'count', 'incubation_time': 'min', 'temperature': 'C', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'titrant_preparation_ref': None, 'fixed_partner_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series', 'support': None}, 'assay_format': None, 'spread_kind': None, 'fit_model': None, 'readout_signal': None, 'capillary_type': None, 'label_type': None, 'choice_support': dict.fromkeys(CHOICE_NAMES), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_mst', kd=20.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_mst_1', titrant_prep='prep_titrant_a', fixed_prep='prep_fixed_a', dataset='dataset_mst_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'titrant_preparation_ref': titrant_prep, 'fixed_partner_preparation_ref': fixed_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'ki': kd * 2, 'ec50': kd * 1.5, 'kd_spread': spread, 'ki_spread': spread * 2, 'labelled_concentration': kd / 4, 'fnorm_amplitude': 12.0, 'signal_to_noise': 18.0, 'led_power': 40.0, 'ir_laser_power': 60.0, 'fhot_time': 1.5, 'titration_point_count': 12, 'incubation_time': 15.0, 'temperature': 25.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd / 20 * 2 ** step for step in range(12)], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['assay_format'] = 'direct_titration'
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = '1:1'
    record['readout_signal'] = 'thermophoresis'
    record['capillary_type'] = 'hydrophilic'
    record['label_type'] = 'covalent_nhs_dye'
    answers = {'initial_fluorescence_checked': 'yes', 'initial_fluorescence_consistent': 'yes', 'fluorescence_intensity_in_range': 'yes', 'aggregation_or_adsorption_checked': 'yes', 'detergent_or_carrier_in_buffer': 'yes', 'labelled_partner_at_or_below_kd': 'yes', 'tight_binding_considered': 'yes', 'equilibrium_reached': 'yes', 'labelling_does_not_alter_binding': 'yes', 'nonspecific_binding_checked': 'yes', 'independent_titrations': 'yes', 'single_estimate_method': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    record['choice_support'] = dict.fromkeys(CHOICE_NAMES, 'direct')
    return record


def real_record():
    """The published MST saturation-type measurement of NHS-RED labelled BmpA with thymidine (Borrelia burgdorferi substrate-binding
    protein; Journal of Biological Chemistry 2026, doi 10.1016/j.jbc.2026.113206, PMC13325309), from its Results and its Methods
    paragraph: KD 5.32 x 10^-7 M (= 532 nM) for thymidine (the first of the three KDs the Results paragraph gives 'respectively' for
    thymidine, cytidine and adenosine), the labelled BmpA at a final concentration of 10 nM, a 10-min incubation, 100% excitation
    power, a 1:1 binding model, triplicate experiments, NHS-RED dye labelling and 0.05% Tween-20 in the buffer. Only what the
    paragraphs state is filled: the ligand series is given as a range (100 uM to 3.05 nM), not a list; the MST power is 'medium' (not a
    number); the capillaries are named 'standard MST premium'; the room temperature has no value; no spread, no signal size, no
    F-hot time and no control is stated. Preparations are unknown."""
    record = blank_record('exp_bmpa_thymidine_mst', 'source_pmc13325309', 'hypothesis_bmpa_binds_thymidine')
    locator = {'kd': 'Results, MST paragraph', 'other': 'Methods, MST paragraph'}
    record['spans'] = {'span_kd': {'locator': locator['kd'], 'quote': 'dissociation constants (Kd) of 5.32 × 10−7 M'},
                       'span_labelled': {'locator': locator['other'], 'quote': 'The labeled BmpA was diluted to a final concentration of 10 nM'},
                       'span_incubation': {'locator': locator['other'], 'quote': 'a 10-min incubation'},
                       'span_led': {'locator': locator['other'], 'quote': '100% excitation power'},
                       'span_triplicate': {'locator': locator['other'], 'quote': 'All experiments were performed in triplicate'},
                       'span_fit': {'locator': locator['other'], 'quote': 'using a 1:1 binding model'},
                       'span_label': {'locator': locator['other'], 'quote': 'fluorescently labeled with NHS-RED dye'},
                       'span_detergent': {'locator': locator['other'], 'quote': 'PBST buffer (phosphate-buffered saline, 0.05% Tween-20, pH 7.4)'}}
    record['quantities']['kd'] = point(532, 'nM', 'kd', ['span_kd'])
    record['quantities']['labelled_concentration'] = point(10, 'nM', 'labelled_concentration', ['span_labelled'])
    record['quantities']['incubation_time'] = point(10, 'min', 'incubation_time', ['span_incubation'])
    record['quantities']['led_power'] = point(100, 'percent', 'led_power', ['span_led'])
    record['quantities']['replicate_count'] = point(3, 'count', 'replicate_count', ['span_triplicate'])
    record['fit_model'] = '1:1'
    record['label_type'] = 'covalent_nhs_dye'
    record['facts']['detergent_or_carrier_in_buffer'] = fact('yes', ['span_detergent'])
    record['preparations']['dataset_ref'] = 'dataset_pmc13325309_mst'
    record['choice_support'] = {name: 'direct' if record[name] is not None else None for name in CHOICE_NAMES}
    return record
