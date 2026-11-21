"""ITC experiment records for the ITC grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a
publication) used to exercise every criterion's supported path. Its numbers,
worked by hand: KD 20 nM, n 1.0 (expected 1.0), cell 10 uM so c = 1.0 x
10000 nM / 20 nM = 500; T 298.15 K; dH -50 kJ/mol; dS -20.3 J/mol/K, so
dG from parts = -50 - 298.15 x (-20.3)/1000 = -43.948 kJ/mol and dG from KD
= 8.314462618 x 298.15 x ln(20e-9)/1000 = 2.47896 x (-17.7275) = -43.948
kJ/mol (gap about 0).
sparse_record: only a KD and what a bare abstract gives; everything else is
an unavailable operand or an 'unknown' fact.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_itc_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

UNITS = {'kd': 'nM', 'kd_spread': 'nM', 'stoichiometry': 'dimensionless', 'expected_stoichiometry': 'dimensionless', 'enthalpy': 'kJ/mol', 'entropy': 'J/mol/K', 'temperature': 'K', 'cell_concentration': 'uM', 'syringe_concentration': 'uM', 'injection_count': 'count', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'syringe_preparation_ref': None, 'cell_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'spread_kind': None, 'fit_model': None, 'choice_support': {'spread_kind': None, 'fit_model': None}, 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_itc', kd=20.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_itc_1', syringe_prep='prep_syringe_a', cell_prep='prep_cell_a', dataset='dataset_itc_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'syringe_preparation_ref': syringe_prep, 'cell_preparation_ref': cell_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'kd_spread': spread, 'stoichiometry': 1.0, 'expected_stoichiometry': 1.0, 'enthalpy': -50.0, 'entropy': -20.3, 'temperature': 298.15, 'cell_concentration': 10.0, 'syringe_concentration': 100.0, 'injection_count': 20, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = 'one_set_of_sites'
    record['choice_support'] = {'spread_kind': 'direct', 'fit_model': 'direct'}
    answers = {'dilution_control_performed': 'yes', 'dilution_control_subtracted': 'yes', 'baseline_corrected': 'yes', 'concentrations_determined': 'yes', 'active_fraction_determined': 'yes', 'binding_sites_heterogeneous': 'no', 'residuals_reported': 'yes', 'n_fitted_freely': 'yes', 'buffer_matching': 'dialysed_together', 'temperature_controlled': 'yes', 'independent_titrations': 'yes'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    return record


def hsp90_hop_record():
    """The published Hsp90-Hop ITC measurement (Protein Science 2020, doi 10.1002/pro.3969, PMC7679967, Figure 1a-b
    legend): KD 0.578 +- 0.073 uM and fitted n 0.544 +- 0.052 (errors: SD of three independent experiments), a single
    binding site model, and the signs (not the values) of dH and -T dS. Only what the legend gave is filled."""
    record = blank_record('exp_hsp90_hop_itc', 'source_pmc7679967', 'hypothesis_hsp90_binds_hop_directly')
    record['spans'] = {'span_kd': {'locator': 'Figure 1 legend, part a', 'quote': 'KD = 0.578 ± 0.073 μM'}, 'span_n': {'locator': 'Figure 1 legend, part a', 'quote': 'n = 0.544 ± 0.052'}, 'span_replicates': {'locator': 'Figure 1 legend, part b', 'quote': 'three independent experiments'}}
    record['quantities']['kd'] = point(0.578, 'uM', 'kd', ['span_kd'])
    record['quantities']['kd_spread'] = point(0.073, 'uM', 'kd_spread', ['span_kd'])
    record['quantities']['stoichiometry'] = point(0.544, 'dimensionless', 'stoichiometry', ['span_n'])
    record['quantities']['replicate_count'] = point(3, 'count', 'replicate_count', ['span_replicates'])
    record['spread_kind'] = 'standard_deviation'
    record['fit_model'] = 'one_set_of_sites'
    record['choice_support'] = {'spread_kind': 'direct', 'fit_model': 'direct'}
    record['facts']['independent_titrations'] = fact('yes', ['span_replicates'])
    record['preparations']['dataset_ref'] = 'dataset_pmc7679967_fig1'
    return record
