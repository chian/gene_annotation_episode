"""SPA (scintillation proximity assay) binding experiment records for the SPA grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: a KD of 2 nM (standard error 0.2 nM) of a tritiated radioligand, a Ki of
5 nM (standard error 0.3 nM) from an IC50 of 7.5 nM with 1 nM of the radioligand (Cheng-Prusoff: 7.5 / (1 + 1 / 2) = 5); ten
radioligand concentrations from 0.1 nM (0.05 x KD) to 51.2 nM (25.6 x KD); 6 percent of the radioligand bound; non-specific binding
25 percent of the total binding, defined with a 500-fold excess of the unlabelled ligand (1000 nM, also 500 x the KD); the control
without the captured target 8 percent of the total signal; a Hill slope of 1.0; 120 min incubation at 25 C; three independent
experiments of triplicate wells; a non-linear fit of a saturation experiment on YSi beads that capture a His-tagged protein.
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an 'unknown' fact.
real_record: see below (the published case).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spa_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

CHOICE_NAMES = ('assay_format', 'radioligand_isotope', 'bead_type', 'capture_method', 'preparation_type', 'counter', 'spread_kind', 'fit_model')
UNITS = {'kd': 'nM', 'bmax': 'fmol/mg', 'ki': 'nM', 'ic50': 'nM', 'hill_slope': 'ratio', 'kd_spread': 'nM', 'ki_spread': 'nM', 'specific_activity': 'Ci/mmol', 'radioligand_concentration': 'nM', 'radioligand_range_lowest': 'nM', 'radioligand_range_highest': 'nM', 'bead_amount': 'mg', 'bead_concentration': 'mg/mL', 'receptor_amount': 'ug', 'percent_bound': 'percent', 'nonspecific_fraction': 'percent', 'nonspecific_ligand_concentration': 'nM', 'nonspecific_excess': 'ratio', 'bead_only_fraction': 'percent', 'counting_efficiency': 'percent', 'incubation_time': 'min', 'settling_time': 'min', 'temperature': 'C', 'titration_point_count': 'count', 'technical_replicate_count': 'count', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'radioligand_preparation_ref': None, 'receptor_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': unavailable('nM', 'concentration_series', 'not_given_in_the_inspected_source_text'), 'assay_format': None, 'radioligand_isotope': None, 'bead_type': None, 'capture_method': None, 'preparation_type': None, 'counter': None, 'spread_kind': None, 'fit_model': None, 'choice_support': dict.fromkeys(CHOICE_NAMES), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_spa', kd=2.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def real_record():
    """The published Methods paragraph on the SPA experiments of purified LeuT variants (eLife 2024, doi 10.7554/eLife.87985, PMC10945697), only
    what it states about the experiments: [3H]leucine (tritium) of 25 Ci/mmol, YSi-Cu His-tag SPA beads (yttrium silicate beads that capture
    a His-tagged protein through a metal chelate) at 1.25 mg/ml, purified protein, a MicroBeta2 counter, 100 uM unlabelled leucine to correct
    for unspecific binding, ligand depletion avoided by a 20-fold molar excess of radioligand, about 16 hours at 4 C. It reports no measured
    KD or Bmax, IC50 or Ki value, no Hill slope, fit model, bead-only control, settling time, equilibrium time course or replicate count.
    Preparations are unknown."""
    record = blank_record('exp_leut_spa', 'source_pmc10945697', 'hypothesis_leut_binds_ligand')
    locator = 'Methods, pharmacological studies of purified LeuT variants by SPA'
    record['spans'] = {'span_isotope': {'locator': locator, 'quote': 'saturation binding of [3H]leucine'},
                       'span_specific_activity': {'locator': locator, 'quote': 'saturation binding of [3H]leucine (25 Ci/mmol)'},
                       'span_beads': {'locator': locator, 'quote': 'Yttrium Silicate Copper (YSi-Cu) His-tag SPA beads'},
                       'span_purified': {'locator': locator, 'quote': 'Pharmacological studies were conducted on purified LeuT variants'},
                       'span_counter': {'locator': locator, 'quote': 'on a 2450 MicroBeta2 microplate counter'},
                       'span_bead_concentration': {'locator': locator, 'quote': '1.25 mg/ml YSi-Cu His-tag SPA beads'},
                       'span_nonspecific_ligand': {'locator': locator, 'quote': 'addition of 100 µM unlabeled leucine'},
                       'span_incubation': {'locator': locator, 'quote': 'incubated for ~16 hr'},
                       'span_temperature': {'locator': locator, 'quote': 'at 4°C with gentle agitation'},
                       'span_depletion': {'locator': locator, 'quote': 'ligand depletion was avoided by maintaining ≥20-fold molar excess of [3H]leucine relative to LeuT'},
                       'span_nonspecific': {'locator': locator, 'quote': 'with unspecific binding corrected for by the addition of 100 µM unlabeled leucine'}}
    quantities = {'specific_activity': (25.0, 'Ci/mmol', 'span_specific_activity'), 'bead_concentration': (1.25, 'mg/mL', 'span_bead_concentration'),
                  'nonspecific_ligand_concentration': (100.0, 'uM', 'span_nonspecific_ligand'), 'incubation_time': (16.0, 'h', 'span_incubation'), 'temperature': (4.0, 'C', 'span_temperature')}
    for name, (value, unit, span) in quantities.items():
        record['quantities'][name] = point(value, unit, name, [span])
    record['radioligand_isotope'], record['bead_type'], record['capture_method'] = 'tritium', 'ysi', 'metal_chelate'
    record['preparation_type'], record['counter'] = 'purified_protein', 'microbeta'
    record['choice_support'].update(radioligand_isotope='direct', bead_type='direct', capture_method='direct', preparation_type='direct', counter='direct')
    record['facts']['ligand_depletion_checked'] = fact('yes', ['span_depletion'])
    record['facts']['nonspecific_binding_determined'] = fact('yes', ['span_nonspecific'])
    record['preparations']['dataset_ref'] = 'dataset_pmc10945697_spa'
    return record


def synthetic_record(experiment_ref='exp_synthetic_spa_1', radioligand_prep='prep_radioligand_a', receptor_prep='prep_receptor_a', dataset='dataset_spa_1', kd=2.0, spread=0.2, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'radioligand_preparation_ref': radioligand_prep, 'receptor_preparation_ref': receptor_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'bmax': 1200.0, 'ki': kd * 2.5, 'ic50': kd * 3.75, 'hill_slope': 1.0, 'kd_spread': spread, 'ki_spread': spread * 1.5, 'specific_activity': 85.0, 'radioligand_concentration': kd / 2, 'radioligand_range_lowest': kd * 0.05, 'radioligand_range_highest': kd * 25.6, 'bead_amount': 2.0, 'bead_concentration': 20.0, 'receptor_amount': 0.5, 'percent_bound': 6.0, 'nonspecific_fraction': 25.0, 'nonspecific_ligand_concentration': kd * 500, 'nonspecific_excess': 500.0, 'bead_only_fraction': 8.0, 'counting_efficiency': 32.0, 'incubation_time': 120.0, 'settling_time': 30.0, 'temperature': 25.0, 'titration_point_count': 10, 'technical_replicate_count': 3, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd * 0.05 * 2 ** step for step in range(10)], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['assay_format'] = 'saturation'
    record['radioligand_isotope'] = 'tritium'
    record['bead_type'] = 'ysi'
    record['capture_method'] = 'metal_chelate'
    record['preparation_type'] = 'purified_protein'
    record['counter'] = 'microbeta'
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = 'one_site'
    record['choice_support'] = dict.fromkeys(CHOICE_NAMES, 'direct')
    answers = {'homogeneous_no_wash_format': 'yes', 'nonspecific_binding_determined': 'yes', 'nonproximity_signal_checked': 'yes', 'bead_only_control_done': 'yes', 'equilibrium_reached': 'yes', 'ligand_depletion_checked': 'yes', 'quench_interference_checked': 'yes', 'bead_settling_controlled': 'yes', 'radioligand_purity_checked': 'yes', 'nonlinear_fit_used': 'yes', 'cheng_prusoff_applied_with_own_kd': 'yes', 'independent_experiments': 'yes', 'single_estimate_method': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    return record
