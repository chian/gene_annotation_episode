"""EMSA (electrophoretic mobility shift assay) experiment records for the EMSA grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC QUANTITATIVE record (not a publication) used to exercise every criterion's supported
path. Its numbers: a titration of a purified protein against a 28 bp double-stranded DNA probe labelled with 32P, at 0.5 nM (a 40th of the KD) in a
binding buffer of 100 mM salt, 5 mM magnesium and 10 percent glycerol with 50 ng of poly(dI-dC), incubated 30 min at 25 C and run on a 6 percent native
polyacrylamide gel at 10 V/cm for 90 min at 4 C; 11 protein concentrations from 1 nM to 640 nM, 92 percent of the probe shifted at the highest, a
one-site fit giving an apparent KD of 20 nM (standard error 2 nM), one shifted species, three independent experiments; every control done and passed
(probe alone, specific competitor 100 fold, non-specific competitor, mutant probe, BSA, supershift, purified protein, equilibrium by a time course,
stable complex, free probe quantified, probe below the KD, range spanning the KD, one method).
qualitative_record: the same experiment without a titration: a shift with the controls and no apparent KD (the KD, its spread, the fraction shifted, the
protein concentrations, the titration points and the fit model are unavailable or None; the probe-below-KD and range facts are unknown).
sparse_record: only the statement that a shifted band was seen; everything else is an unavailable operand or an 'unknown' fact.
multiple_species_record: the synthetic record with two shifted species and a one-site fit.
real_record: see below (the published case).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_emsa_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, UNITS as UNIT_VOCABULARIES, VERSION, fact, point, unavailable

UNITS = {name: units[0] for name, units in UNIT_VOCABULARIES.items()}
UNITS.update({'kd': 'nM', 'kd_spread': 'nM', 'protein_concentration_lowest': 'nM', 'protein_concentration_highest': 'nM', 'probe_concentration': 'nM', 'incubation_time': 'min', 'run_time': 'min', 'run_voltage': 'V/cm'})
CHOICES = ('probe_type', 'probe_label', 'gel_type', 'nonspecific_competitor_type', 'spread_kind', 'fit_model')


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'probe_preparation_ref': None, 'protein_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, **dict.fromkeys(CHOICES), 'choice_support': dict.fromkeys(CHOICES), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_emsa'):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_shift': {'locator': 'synthetic', 'quote': 'synthetic fixture: a shifted band was seen'}}
    record['facts']['shift_detected'] = fact('yes', ['span_shift'])
    return record


def real_record():
    """The published Results paragraph on the EMSA of purified SarA with the srn_9340 promoter fragment (Insights into the regulation of small RNA expression: SarA
    represses the expression of two sRNAs in Staphylococcus aureus, Nucleic Acids Research 2016, doi 10.1093/nar/gkw777, PMC5137438, CC BY-NC), only what it states about the
    experiment: a distinct SarA/srn_9340P225 complex with an apparent Kd of 11 +/- 0.2 nM, a second shifted band (not described as a replicate or a model), a 10-fold
    excess of the unlabelled probe competing, a 100-fold excess of an unlabelled non-specific 16S fragment not displacing the labelled probe, purified SarA. It states no probe
    concentration, protein concentrations, buffer, incubation, gel, run, fit model, spread kind or replicate count. Preparations are unknown (the protein is SarA, the probe the
    srn_9340P225 fragment)."""
    record = blank_record('exp_sara_srn9340_emsa', 'source_pmc5137438', 'hypothesis_sara_binds_srn9340_promoter')
    locator = 'Results, SarA binding to the srn_9340 promoter'
    record['spans'] = {'span_kd': {'locator': locator, 'quote': 'apparent Kd of 11 ± 0.2 nM'},
                       'span_shift': {'locator': locator, 'quote': 'We observed a distinct SarA/srn_9340P225 complex'},
                       'span_excess': {'locator': locator, 'quote': 'A 10-fold excess of srn_9340P225effectively competed'},
                       'span_specific': {'locator': locator, 'quote': 'effectively competed with the labeled promoter fragment for SarA binding'},
                       'span_nonspecific': {'locator': locator, 'quote': 'did not displace the labeled one from the complex'},
                       'span_purified': {'locator': locator, 'quote': 'purified SarA'}}
    for name, (value, unit, span) in {'kd': (11.0, 'nM', 'span_kd'), 'kd_spread': (0.2, 'nM', 'span_kd'), 'specific_competitor_excess': (10.0, 'ratio', 'span_excess')}.items():
        record['quantities'][name] = point(value, unit, name, [span])
    for name, span in (('shift_detected', 'span_shift'), ('shift_abolished_by_specific_competitor', 'span_specific'), ('shift_not_abolished_by_nonspecific_competitor', 'span_nonspecific'), ('protein_purified', 'span_purified')):
        record['facts'][name] = fact('yes', [span])
    record['preparations']['dataset_ref'] = 'dataset_pmc5137438_emsa'
    return record


def synthetic_record(experiment_ref='exp_synthetic_emsa_1', probe_prep='prep_probe_a', protein_prep='prep_protein_a', dataset='dataset_emsa_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'probe_preparation_ref': probe_prep, 'protein_preparation_ref': protein_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'kd_spread': spread, 'fraction_shifted_highest': 92.0, 'protein_concentration_lowest': kd * 0.05, 'protein_concentration_highest': kd * 32.0, 'probe_concentration': kd * 0.025, 'probe_length': 28, 'salt_concentration': 100.0,
              'magnesium_concentration': 5.0, 'glycerol_percent': 10.0, 'nonspecific_competitor_amount': 50.0, 'specific_competitor_excess': 100.0, 'incubation_time': 30.0, 'incubation_temperature': 25.0, 'gel_percent': 6.0, 'run_time': 90.0,
              'run_voltage': 10.0, 'run_temperature': 4.0, 'titration_point_count': 11, 'shifted_species_count': 1, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record.update({'probe_type': 'dsdna', 'probe_label': 'p32', 'gel_type': 'native_polyacrylamide', 'nonspecific_competitor_type': 'poly_dI_dC', 'spread_kind': 'standard_error', 'fit_model': 'one_site'})
    record['choice_support'] = dict.fromkeys(CHOICES, 'direct')
    record['facts'] = {name: fact('yes', refs) for name in FACTS}
    return record


def qualitative_record(experiment_ref='exp_qualitative_emsa_1', probe_prep='prep_probe_q', protein_prep='prep_protein_q', dataset='dataset_emsa_q', assertion='hypothesis_synthetic_binding'):
    record = synthetic_record(experiment_ref, probe_prep, protein_prep, dataset, assertion=assertion)
    for name in ('kd', 'kd_spread', 'fraction_shifted_highest', 'protein_concentration_lowest', 'protein_concentration_highest', 'titration_point_count'):
        record['quantities'][name] = unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text')
    record['spread_kind'], record['fit_model'] = None, None
    record['choice_support']['spread_kind'] = record['choice_support']['fit_model'] = None
    record['facts']['probe_at_or_below_kd'] = fact('unknown')
    record['facts']['protein_range_brackets_kd'] = fact('unknown')
    return record


def multiple_species_record(experiment_ref='exp_multiple_species_emsa'):
    record = synthetic_record(experiment_ref)
    record['quantities']['shifted_species_count'] = point(2, 'count', 'shifted_species_count:' + experiment_ref, ['span_' + experiment_ref], 'shifted_species_count')
    return record
