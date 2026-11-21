"""Radioligand binding experiment records for the radioligand grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: a KD of 2 nM (standard error 0.2 nM) of a tritiated radioligand, a Ki of
5 nM (standard error 0.3 nM) from an IC50 of 7.5 nM with 1 nM of the radioligand (Cheng-Prusoff: 7.5 / (1 + 1 / 2) = 5); ten
radioligand concentrations from 0.1 nM (0.05 x KD) to 51.2 nM (25.6 x KD); 6 percent of the radioligand bound; non-specific binding
25 percent of the total binding, defined with a 500-fold excess of the unlabelled ligand (1000 nM, also 500 x the KD); a Hill slope
of 1.0; 60 min incubation at 25 C; three independent experiments of triplicate tubes; a non-linear fit of a saturation experiment.
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an 'unknown' fact.
real_record: see below (the published case).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_radioligand_record import CHOICE_FIELDS, EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

UNITS = {'kd': 'nM', 'bmax': 'fmol/mg', 'ki': 'nM', 'ic50': 'nM', 'hill_slope': 'ratio', 'kd_spread': 'nM', 'ki_spread': 'nM', 'specific_activity': 'Ci/mmol', 'radioligand_concentration': 'nM', 'radioligand_range_lowest': 'nM', 'radioligand_range_highest': 'nM', 'receptor_amount': 'ug', 'percent_bound': 'percent', 'nonspecific_fraction': 'percent', 'nonspecific_ligand_concentration': 'nM', 'nonspecific_excess': 'ratio', 'incubation_time': 'min', 'temperature': 'C', 'titration_point_count': 'count', 'technical_replicate_count': 'count', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'radioligand_preparation_ref': None, 'receptor_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series', 'support': None}, 'assay_format': None, 'radioligand_isotope': None, 'separation_method': None, 'preparation_type': None, 'spread_kind': None, 'fit_model': None, 'choice_support': dict.fromkeys(CHOICE_FIELDS), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_radioligand', kd=2.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def real_record():
    """The published analysis paragraph of the radioligand binding experiments of the apelin receptor (Nature Communications 15, 10714,
    2024, doi 10.1038/s41467-024-55381-w, PMC11680790), only what its Methods paragraph on the analysis of the saturation and competition
    binding data states: the known specific activity of the radiolabel (2200 Ci/mmol), the
    radiolabel concentration of the competition fit (0.1 nM) and a non-linear fit of the saturation data. The known KD of the radiolabel (0.076 nM) is
    cited, not measured in the experiment, so it is not held. It reports no measured KD or Bmax, IC50 or Ki value, no isotope, separation method, preparation type, incubation, temperature, non-specific binding definition,
    percent bound or replicate count. Preparations are unknown."""
    record = blank_record('exp_apelin_receptor_radioligand', 'source_pmc11680790', 'hypothesis_apelin_receptor_binds_ligand')
    locator = 'Methods, radioligand binding assays, analysis of the binding data'
    record['spans'] = {'span_specific_activity': {'locator': locator, 'quote': 'known specific activity of the radiolabel (2200 Ci/mmol)'},
                       'span_radioligand_concentration': {'locator': locator, 'quote': 'constraints for the radiolabel concentration (0.1 nM)'},
                       'span_nonlinear': {'locator': locator, 'quote': 'Saturation data were presented using the nonlinear one site-specific binding with Hill slope model'}}
    record['quantities']['specific_activity'] = point(2200.0, 'Ci/mmol', 'specific_activity', ['span_specific_activity'])
    record['quantities']['radioligand_concentration'] = point(0.1, 'nM', 'radioligand_concentration', ['span_radioligand_concentration'], support='implied')      # given as a constraint of the fit
    record['facts']['nonlinear_fit_used'] = fact('yes', ['span_nonlinear'])
    record['preparations']['dataset_ref'] = 'dataset_pmc11680790_radioligand'
    return record


def synthetic_record(experiment_ref='exp_synthetic_radioligand_1', radioligand_prep='prep_radioligand_a', receptor_prep='prep_receptor_a', dataset='dataset_radioligand_1', kd=2.0, spread=0.2, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'radioligand_preparation_ref': radioligand_prep, 'receptor_preparation_ref': receptor_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'bmax': 1200.0, 'ki': kd * 2.5, 'ic50': kd * 3.75, 'hill_slope': 1.0, 'kd_spread': spread, 'ki_spread': spread * 1.5, 'specific_activity': 85.0, 'radioligand_concentration': kd / 2, 'radioligand_range_lowest': kd * 0.05, 'radioligand_range_highest': kd * 25.6, 'receptor_amount': 20.0, 'percent_bound': 6.0, 'nonspecific_fraction': 25.0, 'nonspecific_ligand_concentration': kd * 500, 'nonspecific_excess': 500.0, 'incubation_time': 60.0, 'temperature': 25.0, 'titration_point_count': 10, 'technical_replicate_count': 3, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd * 0.05 * 2 ** step for step in range(10)], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['assay_format'] = 'saturation'
    record['radioligand_isotope'] = 'tritium'
    record['separation_method'] = 'filtration'
    record['preparation_type'] = 'membrane'
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = 'one_site'
    record['choice_support'] = dict.fromkeys(CHOICE_FIELDS, 'direct')      # a hand-built record: every stated choice is direct
    answers ={'ligand_depletion_checked': 'yes', 'nonspecific_binding_determined': 'yes', 'equilibrium_reached': 'yes', 'radioligand_purity_checked': 'yes', 'filter_binding_checked': 'yes', 'wash_dissociation_considered': 'yes', 'nonlinear_fit_used': 'yes', 'cheng_prusoff_applied_with_own_kd': 'yes', 'independent_experiments': 'yes', 'single_estimate_method': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    return record
