"""BLI experiment records for the BLI grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: KD 20 nM from kon 1.0e5 M^-1 s^-1 and koff 2.0e-3 s^-1
(koff / kon = 2.0e-8 M = 20 nM); steady-state KD 30 nM (ratio 1.5); a 600 s dissociation window, so the decayed
fraction is 1 - exp(-2.0e-3 x 600) = 1 - exp(-1.2) = 0.6988; loading 1.0 nm, maximum response 0.8 nm, R-squared 0.99;
six concentrations from 2 nM (0.1 x KD) to 600 nM (30 x KD).
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an
'unknown' fact.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_bli_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

UNITS = {'kd': 'nM', 'kd_steady_state': 'nM', 'kon': 'M^-1 s^-1', 'koff': 's^-1', 'response_max': 'nm', 'kd_spread': 'nM', 'fit_r_squared': 'dimensionless', 'loading_level': 'nm', 'dissociation_time': 's', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'analyte_preparation_ref': None, 'immobilized_preparation_ref': None, 'sensor_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series'}, 'spread_kind': None, 'fit_model': None, 'biosensor_type': None, 'choice_support': {'spread_kind': None, 'fit_model': None, 'biosensor_type': None}, 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_bli', kd=20.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_bli_1', analyte_prep='prep_analyte_a', immobilized_prep='prep_ligand_a', sensor='sensor_lot_1', dataset='dataset_bli_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'analyte_preparation_ref': analyte_prep, 'immobilized_preparation_ref': immobilized_prep, 'sensor_ref': sensor, 'dataset_ref': dataset}
    values = {'kd': kd, 'kd_steady_state': kd * 1.5, 'kon': 1.0e5, 'koff': kd * 1e-9 * 1.0e5, 'response_max': 0.8, 'kd_spread': spread, 'fit_r_squared': 0.99, 'loading_level': 1.0, 'dissociation_time': 600.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd / 10, kd * 0.3, kd, kd * 3, kd * 10, kd * 30], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = '1:1'
    record['biosensor_type'] = 'streptavidin'
    record['choice_support'] = {'spread_kind': 'direct', 'fit_model': 'direct', 'biosensor_type': 'direct'}
    answers = {'reference_sensor_subtracted': 'yes', 'buffer_reference_subtracted': 'yes', 'baseline_stable': 'yes', 'loading_step_documented': 'yes', 'regeneration': 'yes', 'independent_sensors': 'yes', 'immobilized_partner_active': 'yes', 'analyte_bivalent_or_oligomeric': 'no', 'avidity_rebinding_considered': 'yes', 'mass_transport_considered': 'yes', 'nonspecific_binding_checked': 'yes', 'single_estimate_method': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    return record


def real_record():
    """The published BLI measurement of pantinin-1 binding to the Chikungunya virus nsP2 protease (PLOS ONE, doi
    10.1371/journal.pone.0346930, PMC13065029, Methods paragraph on the BLI assay): KD 9.29 uM from a Scatchard
    plot of the responses (no spread), a 600 s dissociation phase, all measurements in triplicate, and a control
    without the protease that showed no binding. Only what the paragraph states is filled."""
    record = blank_record('exp_chikv_nsp2pro_pantinin1_bli', 'source_pmc13065029', 'hypothesis_pantinin1_binds_chikv_nsp2pro_directly')
    record['spans'] = {'span_kd': {'locator': 'Methods, BLI assay paragraph', 'quote': 'KD) of 9.29 μM'}, 'span_dissociation': {'locator': 'Methods, BLI assay paragraph', 'quote': 'dissociation phase of 600 s'}, 'span_triplicate': {'locator': 'Methods, BLI assay paragraph', 'quote': 'All measurements were conducted in triplicate'}, 'span_control': {'locator': 'Methods, BLI assay paragraph', 'quote': 'a control experiment was performed in the absence of the protease'}}
    record['quantities']['kd'] = point(9.29, 'uM', 'kd', ['span_kd'])
    record['quantities']['dissociation_time'] = point(600, 's', 'dissociation_time', ['span_dissociation'])
    record['quantities']['replicate_count'] = point(3, 'count', 'replicate_count', ['span_triplicate'])
    record['facts']['nonspecific_binding_checked'] = fact('yes', ['span_control'])
    record['preparations']['dataset_ref'] = 'dataset_pmc13065029_bli'
    return record
