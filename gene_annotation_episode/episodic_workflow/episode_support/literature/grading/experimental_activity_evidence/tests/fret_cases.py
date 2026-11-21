"""FRET experiment records for the FRET grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: direct-titration KD 20 nM (standard error 2 nM) and a
competition Ki 40 nM (standard error 4 nM; ratio 2.0), EC50 30 nM, IC50 80 nM; a terbium-cryptate donor at 5 nM and an
acceptor at 30 nM held fixed (the limiting one is 5 nM = 0.25 x KD); an emission ratio from 0.4 (bottom) to 1.6 (plateau),
a fold of 4; ten titrant concentrations from 2 nM (0.1 x KD) to 2000 nM (100 x KD); a 100 us delay and a 400 us
integration window; 20 uL, 60 min, 25 C; three independent titrations.
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an 'unknown' fact.
real_record: the published TR-FRET saturation measurement of CoraFluor-1 labelled KLHL11 BTB-BACK binding to AF488-labelled
CUL3 N-terminal domain (PMC10564622), only what the Results paragraph states.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fret_record import CHOICES, EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

UNITS = {'kd': 'nM', 'ki': 'nM', 'ec50': 'nM', 'ic50': 'nM', 'kd_spread': 'nM', 'ki_spread': 'nM', 'donor_concentration': 'nM', 'acceptor_concentration': 'nM', 'ratio_minimum': 'ratio', 'ratio_maximum': 'ratio', 'delay_time': 'us', 'integration_time': 'us', 'assay_volume': 'uL', 'incubation_time': 'min', 'temperature': 'C', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'titrant_preparation_ref': None, 'fixed_partner_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series', 'support': None}, 'assay_format': None, 'spread_kind': None, 'fit_model': None, 'plate_type': None, 'donor_acceptor_pair': None, 'choice_support': dict.fromkeys(CHOICES), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_fret', kd=20.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_fret_1', titrant_prep='prep_titrant_a', fixed_prep='prep_fixed_a', dataset='dataset_fret_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'titrant_preparation_ref': titrant_prep, 'fixed_partner_preparation_ref': fixed_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'ki': kd * 2, 'ec50': kd * 1.5, 'ic50': kd * 4, 'kd_spread': spread, 'ki_spread': spread * 2, 'donor_concentration': kd / 4, 'acceptor_concentration': kd * 1.5, 'ratio_minimum': 0.4, 'ratio_maximum': 1.6, 'delay_time': 100.0, 'integration_time': 400.0, 'assay_volume': 20.0, 'incubation_time': 60.0, 'temperature': 25.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd / 10, kd / 5, kd / 2, kd, kd * 2, kd * 5, kd * 10, kd * 20, kd * 50, kd * 100], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['assay_format'] = 'direct_titration'
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = '1:1'
    record['plate_type'] = 'white'
    record['donor_acceptor_pair'] = 'lanthanide_with_organic_acceptor'
    answers = {'time_resolved_read': 'yes', 'ratiometric_readout_used': 'yes', 'donor_only_control_measured': 'yes', 'acceptor_only_control_measured': 'yes', 'crosstalk_corrected': 'yes', 'labelled_partner_at_or_below_kd': 'yes', 'tight_binding_considered': 'yes', 'equilibrium_reached': 'yes', 'indirect_labelling_used': 'no', 'labelling_does_not_alter_binding': 'yes', 'compound_interference_checked': 'yes', 'nonspecific_binding_checked': 'yes', 'unlabelled_competitor_displaces': 'yes', 'independent_titrations': 'yes', 'single_estimate_method': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    record['choice_support'] = dict.fromkeys(CHOICES, 'direct')
    return record


def real_record():
    """The published TR-FRET saturation measurement of CoraFluor-1 (terbium) labelled KLHL11 BTB-BACK and AF488-labelled CUL3
    N-terminal domain (Free Radical Biology & Medicine 2023, doi 10.1016/j.freeradbiomed.2023.04.021, PMC10564622, Results
    paragraph on the validation of the TR-FRET assay): KD 20 nM (95% CI 19-22 nM) from a saturation binding experiment, direct
    chemical labelling (not through tag antibodies or streptavidin) shown not to alter the affinity. Only what the paragraph
    states about that experiment is filled: the interval is given by its limits, so no spread value is stated, only its kind."""
    record = blank_record('exp_klhl11_cul3_tr_fret', 'source_pmc10564622', 'hypothesis_klhl11_binds_cul3_ntd')
    record['spans'] = {'span_kd': {'locator': 'Results, TR-FRET validation paragraph', 'quote': 'KD value of 20\xa0nM'}, 'span_kind': {'locator': 'Results, TR-FRET validation paragraph', 'quote': '95% CI 19–22\xa0nM'}, 'span_assay': {'locator': 'Results, TR-FRET validation paragraph', 'quote': 'saturation binding experiment'}, 'span_time_resolved': {'locator': 'Results, TR-FRET validation paragraph', 'quote': 'TR-FRET donor and acceptor functionalization'}, 'span_direct': {'locator': 'Results, TR-FRET validation paragraph', 'quote': 'We selected direct chemical labeling over the use of labeled anti-epitope tag antibodies or streptavidin'}, 'span_tolerated': {'locator': 'Results, TR-FRET validation paragraph', 'quote': 'dye functionalization was well tolerated and did not alter the binding affinity'}}
    record['quantities']['kd'] = point(20, 'nM', 'kd', ['span_kd'])
    record['spread_kind'] = 'confidence_interval'
    record['assay_format'] = 'direct_titration'
    record['facts']['time_resolved_read'] = fact('yes', ['span_time_resolved'])
    record['facts']['indirect_labelling_used'] = fact('no', ['span_direct'])
    record['facts']['labelling_does_not_alter_binding'] = fact('yes', ['span_tolerated'])
    record['preparations']['dataset_ref'] = 'dataset_pmc10564622_tr_fret'
    record['choice_support'] = {name: 'direct' if record[name] is not None else None for name in CHOICES}
    return record
