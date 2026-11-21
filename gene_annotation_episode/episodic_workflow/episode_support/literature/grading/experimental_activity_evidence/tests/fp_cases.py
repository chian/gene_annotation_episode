"""FP experiment records for the FP grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: direct-titration KD 20 nM (standard error 2 nM) and a
competition Ki 40 nM (standard error 4 nM; ratio 2.0); tracer 5 nM (0.25 x KD); polarization from 50 mP (free tracer) to
250 mP (bound), a window of 200 mP; ten titrant concentrations from 2 nM (0.1 x KD) to 2000 nM (100 x KD); a 10 percent
change of the total intensity; 20 uL, 30 min, 25 C; three independent titrations.
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an 'unknown' fact.
real_record: the published FP measurement of a FAM-labelled LANA1-22 peptide binding to nucleosomes (PMC10606924), only
what the Results paragraph states.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_fp_record import CHOICES, EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

UNITS = {'kd': 'nM', 'ki': 'nM', 'kd_spread': 'nM', 'ki_spread': 'nM', 'tracer_concentration': 'nM', 'signal_minimum': 'mP', 'signal_maximum': 'mP', 'total_intensity_change': 'percent', 'assay_volume': 'uL', 'incubation_time': 'min', 'temperature': 'C', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'titrant_preparation_ref': None, 'tracer_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series', 'support': None}, 'assay_format': None, 'spread_kind': None, 'fit_model': None, 'plate_type': None, 'choice_support': dict.fromkeys(CHOICES), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_fp', kd=20.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_fp_1', titrant_prep='prep_titrant_a', tracer_prep='prep_tracer_a', dataset='dataset_fp_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'titrant_preparation_ref': titrant_prep, 'tracer_preparation_ref': tracer_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'ki': kd * 2, 'kd_spread': spread, 'ki_spread': spread * 2, 'tracer_concentration': kd / 4, 'signal_minimum': 50.0, 'signal_maximum': 250.0, 'total_intensity_change': 10.0, 'assay_volume': 20.0, 'incubation_time': 30.0, 'temperature': 25.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd / 10, kd / 5, kd / 2, kd, kd * 2, kd * 5, kd * 10, kd * 20, kd * 50, kd * 100], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['assay_format'] = 'direct_titration'
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = '1:1'
    record['plate_type'] = 'black_non_binding'
    record['choice_support'] = dict.fromkeys(CHOICES, 'direct')
    answers = {'tracer_at_or_below_kd': 'yes', 'equilibrium_reached': 'yes', 'tight_binding_considered': 'yes', 'intensity_change_checked': 'yes', 'free_probe_baseline_measured': 'yes', 'nonspecific_binding_checked': 'yes', 'unlabelled_competitor_displaces': 'yes', 'surface_adsorption_prevented': 'yes', 'independent_titrations': 'yes', 'single_estimate_method': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    return record


def real_record():
    """The published FP measurement of FAM-labelled LANA1-22 peptide binding to nucleosomes (International Journal of
    Molecular Sciences 2023, doi 10.3390/ijms242015194, PMC10606924, Results paragraph on the fluorescence polarization
    assay): tracer 100 nM, titrated with nucleosomes, Kd 0.4 +- 0.09 uM. Only what the paragraph states about that
    experiment is filled (the kind of the +- is not stated)."""
    record = blank_record('exp_lana_nucleosome_fp', 'source_pmc10606924', 'hypothesis_lana_peptide_binds_nucleosomes')
    record['spans'] = {'span_kd': {'locator': 'Results, FP paragraph', 'quote': 'Kd was 0.4 ± 0.09 µM'}, 'span_kd_spread': {'locator': 'Results, FP paragraph', 'quote': '0.09 µM'}, 'span_tracer': {'locator': 'Results, FP paragraph', 'quote': 'concentration of 100 nM'}}
    record['quantities']['kd'] = point(0.4, 'uM', 'kd', ['span_kd'])
    record['quantities']['kd_spread'] = point(0.09, 'uM', 'kd_spread', ['span_kd_spread'])
    record['quantities']['tracer_concentration'] = point(100, 'nM', 'tracer_concentration', ['span_tracer'])
    record['assay_format'] = 'direct_titration'
    record['choice_support']['assay_format'] = 'direct'
    record['preparations']['dataset_ref'] = 'dataset_pmc10606924_fp'
    return record
