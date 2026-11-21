"""SEC (size-exclusion chromatography, with or without multi-angle light scattering, SEC-MALS) complex experiment records for the SEC grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC QUANTITATIVE record (not a publication) used to exercise every criterion's supported path. Its numbers: a
mixture of two proteins (theoretical masses 36 and 18 kDa) injected at 5000 nM (25 times the KD) in 500 uL after 30 min of incubation on a Superdex column (24 mL) at 0.5 mL/min
at 4 C in a running buffer of 150 mM salt; the complex peak elutes at 11.2 mL, the larger component alone at 12.5 mL and the smaller at 14.1 mL (a shift of 1.3 mL); the MALS
molar mass of the complex peak is 52 kDa against 54 kDa expected (the components alone 36.8 and 17.6 kDa), a 1:1 complex, a polydispersity of 1.02; an apparent KD from peak
areas of 200 nM (standard error 20 nM), three independent experiments; every control done and passed (each component alone, SDS-PAGE of the complex peak, the free peak
shrinking with the titration, the MALS mass matching, calibrated column, buffer ruling out the resin, stable on the column, no aggregation, a non-binding mutant, one method).
qualitative_record: the same experiment without a titration: a complex peak with the controls and no apparent KD (the KD, its spread, the spread kind and the injected
concentration are unavailable or None; the stability fact is unknown).
sparse_record: only the statement that a complex peak was seen; everything else is an unavailable operand or an 'unknown' fact.
weak_complex_record: the synthetic record with an injected concentration of 1000 nM (5 times the KD) and a 2:1 stoichiometry.
real_record: see below (the published case).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, UNITS as UNIT_VOCABULARIES, VERSION, fact, point, unavailable

UNITS = {name: units[0] for name, units in UNIT_VOCABULARIES.items()}
UNITS.update({'kd': 'nM', 'kd_spread': 'nM', 'incubation_time': 'min'})
CHOICES = ('column_type', 'detection', 'spread_kind')


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'component_a_preparation_ref': None, 'component_b_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, **dict.fromkeys(CHOICES), 'choice_support': dict.fromkeys(CHOICES), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_sec'):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_peak': {'locator': 'synthetic', 'quote': 'synthetic fixture: a complex peak was seen'}}
    record['facts']['complex_peak_detected'] = fact('yes', ['span_peak'])
    return record


# The published Results paragraph (iScience 2024, PMC11068563), the text the grader tests quote from.
REAL_SOURCE = 'PMC11068563'
REAL_LOCATOR = 'Results, SEC-MALS of the MCUb-NTD, the MCU-NTD and their mixture'
REAL_QUOTES = {
    'span_peak': 'the mixed sample eluted in a single peak and at an earlier elution volume compared to either of the proteins in isolation',
    'span_alone': 'compared to either of the proteins in isolation',
    'span_sds': 'but two bands in the earlier elution fractions for the mixed samples, confirming co-elution',
    'span_mass': 'the domains formed a heterodimer with a MALS-determined molecular weight of 21.7\xa0± 0.4\xa0kDa',
    'span_larger': 'a measured molecular weight of 13.6\xa0± 0.2\xa0kDa',
    'span_stoichiometry': 'the domains formed a heterodimer',
    'span_detection': 'size exclusion chromatography with in-line multi-angle light scattering (SEC-MALS)',
    'span_stable': 'forming stable heterodimers that co-elute in gel filtration experiments',
}


def real_record():
    """The published Results paragraph on the SEC-MALS of the MCU-NTD and the MCUb-NTD (The MCU and MCUb amino-terminal domains tightly interact: mechanisms for low conductance assembly
    of the mitochondrial calcium uniporter complex, iScience 2024, doi 10.1016/j.isci.2024.109699, PMC11068563, CC BY 4.0), only what it states about the experiment: the mixture eluted as a single
    peak at an earlier elution volume than either protein alone, SDS-PAGE of the earlier fractions of the mixture showed two bands (co-elution), the heterodimer has a MALS molar mass of 21.7 +/- 0.4 kDa,
    the MCU-NTD alone (the larger by its stated theoretical mass) 13.6 kDa, the complex is a heterodimer, it is called stable and co-eluting, and the method is SEC with in-line multi-angle light
    scattering. It states no elution volume, no theoretical mass of the complex, no injected molar concentration (the injection concentrations are in mg/mL), no column, buffer, temperature or
    replicate, and no KD. Preparations are unknown (the two proteins are the MCU-NTD and the MCUb-NTD)."""
    record = blank_record('exp_mcu_mcub_ntd_sec_mals', 'source_pmc11068563', 'hypothesis_mcu_ntd_binds_mcub_ntd')
    record['spans'] = {span: {'locator': REAL_LOCATOR, 'quote': quote} for span, quote in REAL_QUOTES.items()}
    for name, (value, unit, span) in {'complex_mass_measured': (21.7, 'kDa', 'span_mass'), 'component_mass_measured_larger': (13.6, 'kDa', 'span_larger'), 'stoichiometry_ratio': (1, 'ratio', 'span_stoichiometry')}.items():
        record['quantities'][name] = point(value, unit, name, [span])
    for name, span in (('complex_peak_detected', 'span_peak'), ('components_run_alone', 'span_alone'), ('complex_peak_analysed_by_sds_page', 'span_sds'), ('complex_stable_on_column', 'span_stable')):
        record['facts'][name] = fact('yes', [span])
    record['detection'] = 'light_scattering'
    record['choice_support']['detection'] = 'direct'
    record['preparations']['dataset_ref'] = 'dataset_pmc11068563_sec_mals'
    return record


def synthetic_record(experiment_ref='exp_synthetic_sec_1', component_a='prep_component_a', component_b='prep_component_b', dataset='dataset_sec_1', kd=200.0, spread=20.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'component_a_preparation_ref': component_a, 'component_b_preparation_ref': component_b, 'dataset_ref': dataset}
    values = {'kd': kd, 'kd_spread': spread, 'complex_elution_volume': 11.2, 'component_elution_volume_earlier': 12.5, 'component_elution_volume_later': 14.1, 'elution_volume_shift': 1.3, 'complex_mass_measured': 52.0, 'complex_mass_theoretical': 54.0,
              'component_mass_measured_larger': 36.8, 'component_mass_measured_smaller': 17.6, 'stoichiometry_ratio': 1.0, 'polydispersity': 1.02, 'flow_rate': 0.5, 'run_temperature': 4.0, 'loaded_concentration': kd * 25.0, 'loaded_volume': 500.0, 'column_volume': 24.0,
              'salt_concentration': 150.0, 'incubation_time': 30.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record.update({'column_type': 'superdex', 'detection': 'light_scattering', 'spread_kind': 'standard_error'})
    record['choice_support'] = dict.fromkeys(CHOICES, 'direct')
    record['facts'] = {name: fact('yes', refs) for name in FACTS}
    return record


def qualitative_record(experiment_ref='exp_qualitative_sec_1', component_a='prep_component_aq', component_b='prep_component_bq', dataset='dataset_sec_q', assertion='hypothesis_synthetic_binding'):
    record = synthetic_record(experiment_ref, component_a, component_b, dataset, assertion=assertion)
    for name in ('kd', 'kd_spread', 'loaded_concentration'):
        record['quantities'][name] = unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text')
    record['spread_kind'] = record['choice_support']['spread_kind'] = None
    record['facts']['complex_stable_on_column'] = fact('unknown')
    return record


def weak_complex_record(experiment_ref='exp_weak_complex_sec'):
    record = synthetic_record(experiment_ref)
    refs = ['span_' + experiment_ref]
    record['quantities']['loaded_concentration'] = point(1000.0, 'nM', 'loaded_concentration:' + experiment_ref, refs, 'loaded_concentration')
    record['quantities']['stoichiometry_ratio'] = point(2.0, 'ratio', 'stoichiometry_ratio:' + experiment_ref, refs, 'stoichiometry_ratio')
    return record
