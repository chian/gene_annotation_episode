"""GCI experiment records for the GCI grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: KD 20 nM from kon 1.0e5 M^-1 s^-1 and koff 2.0e-3 s^-1
(koff / kon = 2.0e-8 M = 20 nM); steady-state KD 30 nM (ratio 1.5); immobilization level 500 pg/mm2, maximum response
40 pg/mm2; six concentrations from 2 nM (0.1 x KD) to 600 nM (30 x KD); a standard error of 2 nM; three replicates.
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an 'unknown' fact.
real_record: the published GCI measurement of CrcA binding to Crc (PMC10213629), only what the paragraph states.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_gci_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

UNITS = {'kd': 'nM', 'kd_steady_state': 'nM', 'kon': 'M^-1 s^-1', 'koff': 's^-1', 'response_max': 'pg/mm2', 'kd_spread': 'nM', 'immobilization_level': 'pg/mm2', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'analyte_preparation_ref': None, 'immobilized_preparation_ref': None, 'chip_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series'}, 'spread_kind': None, 'fit_model': None, 'chip_type': None, 'choice_support': {'spread_kind': None, 'fit_model': None, 'chip_type': None}, 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_gci', kd=20.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_gci_1', analyte_prep='prep_analyte_a', immobilized_prep='prep_ligand_a', chip='chip_lot_1', dataset='dataset_gci_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'analyte_preparation_ref': analyte_prep, 'immobilized_preparation_ref': immobilized_prep, 'chip_ref': chip, 'dataset_ref': dataset}
    values = {'kd': kd, 'kd_steady_state': kd * 1.5, 'kon': 1.0e5, 'koff': kd * 1e-9 * 1.0e5, 'response_max': 40.0, 'kd_spread': spread, 'immobilization_level': 500.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd / 10, kd * 0.3, kd, kd * 3, kd * 10, kd * 30], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = '1:1'
    record['chip_type'] = 'streptavidin'
    record['choice_support'] = {'spread_kind': 'direct', 'fit_model': 'direct', 'chip_type': 'direct'}
    answers = {'reference_channel_subtracted': 'yes', 'double_referenced': 'yes', 'bulk_solvent_corrected': 'yes', 'baseline_stable': 'yes', 'regeneration': 'yes', 'independent_channels_or_chips': 'yes', 'immobilized_partner_active': 'yes', 'analyte_bivalent_or_oligomeric': 'no', 'mass_transport_checked': 'yes', 'nonspecific_binding_checked': 'yes', 'single_estimate_method': 'no', 'repeated_pulse_kinetics_used': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    return record


def real_record():
    """The published GCI measurement of CrcA binding to Crc (Frontiers in Microbiology 2023, doi
    10.3389/fmicb.2023.1195558, PMC10213629, Results paragraph on the GCI assay): Crc immobilized at 15 pg/mm2, a 1:1
    kinetic fit with KD 10.99 uM, and a steady-state ('equilibration curve') KD of 11.99 uM. Only what the paragraph
    states about that experiment is filled."""
    record = blank_record('exp_crca_crc_gci', 'source_pmc10213629', 'hypothesis_crca_binds_crc_directly')
    record['spans'] = {'span_kd': {'locator': 'Results, GCI paragraph', 'quote': 'KD of 10.99 μM'}, 'span_kd_steady_state': {'locator': 'Results, GCI paragraph', 'quote': 'KD of 11.99 ± 0.00 μM'}, 'span_immobilization': {'locator': 'Results, GCI paragraph', 'quote': '15 pg/mm2'}, 'span_fit': {'locator': 'Results, GCI paragraph', 'quote': 'a 1:1 kinetic'}}
    record['quantities']['kd'] = point(10.99, 'uM', 'kd', ['span_kd'])
    record['quantities']['kd_steady_state'] = point(11.99, 'uM', 'kd_steady_state', ['span_kd_steady_state'])
    record['quantities']['immobilization_level'] = point(15, 'pg/mm2', 'immobilization_level', ['span_immobilization'])
    record['fit_model'] = '1:1'
    record['preparations']['dataset_ref'] = 'dataset_pmc10213629_gci'
    return record
