"""SPR experiment records for the SPR grader, converter and merger tests.

popz_record: the published PopZ-ParB SPR measurement (Bowman et al., Cell 2008,
PMC2745220, Fig 3D and SPR methods), built from the owner's case record
research/experimental_scoring_review_2026-10-23/template_a105_binding_002/
paper_01_popz_2745220_001.md. Only what the source gave is filled; everything
else is an unavailable operand or an 'unknown' fact.
synthetic_record: a fully specified, explicitly SYNTHETIC record (not a
publication) used to exercise every criterion's supported path.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spr_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

UNITS = {'kd': 'nM', 'kd_steady_state': 'nM', 'kon': 'M^-1 s^-1', 'koff': 's^-1', 'rmax': 'RU', 'kd_spread': 'nM', 'chi_squared': 'RU^2', 'baseline_noise': 'RU', 'immobilization_level': 'RU', 'analyte_mass': 'kDa', 'ligand_mass': 'kDa', 'stoichiometry': 'dimensionless', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'analyte_preparation_ref': None, 'immobilized_preparation_ref': None, 'surface_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series'}, 'spread_kind': None, 'fit_model': None, 'choice_support': {'spread_kind': None, 'fit_model': None}, 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def popz_record():
    record = blank_record('exp_popz_parb_spr_affinity', 'source_pmc2745220', 'hypothesis_popz_binds_parb_directly')
    record['spans'] = {'span_kd': {'locator': 'Results, SPR paragraph', 'quote': 'we determined the equilibrium dissociation constant for the interaction between ParB and PopZ to be 20 nanomolar'}, 'span_surface': {'locator': 'Methods, Surface Plasmon Resonance', 'quote': 'ParB was covalently immobilized on the surface of a CM5 biosensor chip (Biacore) using amine coupling chemistry'}}
    record['quantities']['kd'] = point(20.0, 'nM', 'kd', ['span_kd'])
    record['preparations'] = {'analyte_preparation_ref': None, 'immobilized_preparation_ref': None, 'surface_ref': None, 'dataset_ref': 'dataset_pmc2745220_fig3d'}
    return record


def synthetic_record(experiment_ref='exp_synthetic_spr_1', analyte_prep='prep_analyte_a', immobilized_prep='prep_ligand_a', surface='surface_1', dataset='dataset_1', kd=20.0, spread=2.0):
    record = blank_record(experiment_ref, 'source_synthetic', 'hypothesis_synthetic_binding')
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'analyte_preparation_ref': analyte_prep, 'immobilized_preparation_ref': immobilized_prep, 'surface_ref': surface, 'dataset_ref': dataset}
    values = {'kd': kd, 'kd_steady_state': kd * 1.5, 'kon': 1.0e5, 'koff': kd * 1e-9 * 1.0e5, 'rmax': 200.0, 'kd_spread': spread, 'chi_squared': 2.0, 'baseline_noise': 1.5, 'immobilization_level': 1000.0, 'analyte_mass': 20.0, 'ligand_mass': 50.0, 'stoichiometry': 1.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([2.0, 6.0, 20.0, 60.0, 200.0, 600.0], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = '1:1_langmuir'
    record['choice_support'] = {'spread_kind': 'direct', 'fit_model': 'direct'}
    answers = {'reference_surface': 'yes', 'double_referencing': 'yes', 'mass_transport': 'checked_not_limited', 'baseline_drift': 'yes', 'regeneration': 'yes', 'independent_surfaces': 'yes', 'immobilized_activity': 'yes', 'analyte_bivalent_or_oligomeric': 'no', 'residuals_reported': 'yes', 'single_estimate_method': 'no', 'kd_analysis': 'kinetic_fit'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    return record
