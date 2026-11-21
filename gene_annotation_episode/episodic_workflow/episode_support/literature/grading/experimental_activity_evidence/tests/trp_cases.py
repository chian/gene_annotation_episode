"""Intrinsic fluorescence quenching titration records for the Trp grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: KD 20 nM (standard error 2 nM), Stern-Volmer constant
2.0e4 M^-1 (kept apart from the KD), protein held at 5 nM (0.25 x KD); excitation 295 nm, emission read at 340 nm with
a 4 nm blue shift; the fluorescence is quenched by 40 percent at saturation; the ligand absorbs 0.02 AU at most; 3 percent
of the starting volume is added; twelve ligand concentrations from 1 nM (0.05 x KD) to 2048 nM (102.4 x KD); 5 min after
each addition, 25 C; three independent titrations.
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an 'unknown' fact.
real_record: the published measurement of the Bug69 protein of Bordetella pertussis binding quinolinate (PMC11452294), only
what its Methods and Results paragraphs state.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_trp_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

CHOICE_NAMES = ('spread_kind', 'fit_model', 'change_direction', 'emission_shift_direction')

UNITS = {'kd': 'nM', 'kd_spread': 'nM', 'ksv': 'M^-1', 'protein_concentration': 'nM', 'excitation_wavelength': 'nm', 'emission_wavelength': 'nm', 'emission_shift': 'nm', 'fluorescence_change': 'percent', 'ligand_absorbance': 'AU', 'added_volume_fraction': 'percent', 'titration_point_count': 'count', 'concentration_lowest': 'nM', 'concentration_highest': 'nM', 'incubation_time': 'min', 'temperature': 'C', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'titrant_preparation_ref': None, 'fixed_partner_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series', 'support': None}, 'spread_kind': None, 'fit_model': None, 'change_direction': None, 'emission_shift_direction': None, 'choice_support': dict.fromkeys(CHOICE_NAMES), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_trp', kd=20.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_trp_1', titrant_prep='prep_ligand_a', fixed_prep='prep_protein_a', dataset='dataset_trp_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'titrant_preparation_ref': titrant_prep, 'fixed_partner_preparation_ref': fixed_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'kd_spread': spread, 'ksv': 2.0e4, 'protein_concentration': kd / 4, 'excitation_wavelength': 295.0, 'emission_wavelength': 340.0, 'emission_shift': 4.0, 'fluorescence_change': 40.0, 'ligand_absorbance': 0.02, 'added_volume_fraction': 3.0, 'titration_point_count': 12, 'incubation_time': 5.0, 'temperature': 25.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd / 20 * 2 ** step for step in range(12)], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = '1:1'
    record['change_direction'] = 'quenching'
    record['emission_shift_direction'] = 'blue'
    answers = {'inner_filter_corrected': 'yes', 'ligand_absorbance_negligible': 'yes', 'dilution_corrected': 'yes', 'buffer_blank_subtracted': 'yes', 'ligand_only_control_measured': 'yes', 'nonbinding_control_done': 'yes', 'trp_analogue_control_done': 'yes', 'signal_localised_to_binding_site': 'yes', 'signal_saturates': 'yes', 'quenching_is_static': 'yes', 'photobleaching_checked': 'yes', 'protein_at_or_below_kd': 'yes', 'tight_binding_considered': 'yes', 'equilibrium_reached': 'yes', 'independent_titrations': 'yes', 'single_estimate_method': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    record['choice_support'] = dict.fromkeys(CHOICE_NAMES, 'direct')
    return record


def real_record():
    """The published tryptophan fluorescence titration of TRKB-ECD-His with the compound 7,8-DHF (International Journal of Molecular
    Sciences 2022, doi 10.3390/ijms232112734, PMC9654711), from its Results paragraph 2.7 and its Methods paragraph 4.14: KD 16.0 nM
    (standard-error-looking '16.0 +/- 3.4 nM', but the kind of the uncertainty is not stated), the TRKB-ECD-His protein at 50 nM,
    excitation at 295 nm and the fit of the normalized intensity at 330 nm. Only what the paragraphs state is filled: the compounds
    are used over a range (0-1000 nM), not a list, so only its top end (1000 nM) is filled and its lowest is not (0 is a blank); 'room temperature' has no value; the size of the change is not given; the fit is an
    equation of the fractional change, not a named model; no replicate count, incubation, correction, blank or control is stated.
    Preparations are unknown."""
    record = blank_record('exp_trkb_78dhf_trp', 'source_pmc9654711', 'hypothesis_trkb_binds_78dhf')
    record['spans'] = {'span_kd': {'locator': 'Results 2.7', 'quote': 'TRKB-ECD binding affinity (KD) of 7,8-DHF was 16.0 ± 3.4 nM'},
                       'span_spread': {'locator': 'Results 2.7', 'quote': '16.0 ± 3.4 nM'},
                       'span_protein': {'locator': 'Methods 4.14', 'quote': 'TRKB-ECD-His (50 nM in PBS)'},
                       'span_excitation': {'locator': 'Methods 4.14', 'quote': 'excitation wavelength set at 295 nm'},
                       'span_emission': {'locator': 'Methods 4.14', 'quote': 'fluorescence intensity at 330 nm'},
                       'span_highest': {'locator': 'Methods 4.14', 'quote': '0–1000 nM'}}
    record['quantities']['concentration_highest'] = point(1000, 'nM', 'concentration_highest', ['span_highest'])      # the range's top; its 0 is a blank, not a lowest concentration
    record['quantities']['kd'] = point(16.0, 'nM', 'kd', ['span_kd'])
    record['quantities']['kd_spread'] = point(3.4, 'nM', 'kd_spread', ['span_spread'])
    record['quantities']['protein_concentration'] = point(50, 'nM', 'protein_concentration', ['span_protein'])
    record['quantities']['excitation_wavelength'] = point(295, 'nm', 'excitation_wavelength', ['span_excitation'])
    record['quantities']['emission_wavelength'] = point(330, 'nm', 'emission_wavelength', ['span_emission'])
    record['preparations']['dataset_ref'] = 'dataset_pmc9654711_trp'
    record['choice_support'] = {name: 'direct' if record[name] is not None else None for name in CHOICE_NAMES}
    return record
