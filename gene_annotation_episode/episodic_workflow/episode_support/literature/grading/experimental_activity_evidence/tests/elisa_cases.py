"""ELISA binding experiment records for the ELISA grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC record (not a publication) used to exercise every
criterion's supported path. Its numbers, worked by hand: apparent KD 20 nM (standard error 2 nM), a competition Ki of
30 nM (ratio 1.5), an EC50 of 28 nM and an IC50 of 45 nM kept as separate values; twelve concentrations from 1 nM
(0.05 x KD) to 2048 nM (102.4 x KD); a plateau of 1.2 OD over a background of 0.06 OD (ratio 20); a binding step of 90 min;
three independent experiments of triplicate wells; a four-parameter logistic fit in a saturation titration.
sparse_record: only a KD and what a bare abstract gives; everything else is an unavailable operand or an 'unknown' fact.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_elisa_record import CHOICE_FIELDS, EXPERIMENT_TYPE, FACTS, QUANTITIES, VERSION, fact, point, unavailable

UNITS = {'kd': 'nM', 'ki': 'nM', 'ec50': 'nM', 'ic50': 'nM', 'kd_spread': 'nM', 'ki_spread': 'nM', 'coating_concentration': 'ug/mL', 'signal_maximum': 'OD', 'signal_background': 'OD', 'wash_count': 'count', 'titration_point_count': 'count', 'technical_replicate_count': 'count', 'incubation_time': 'min', 'temperature': 'C', 'replicate_count': 'count'}


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'titrant_preparation_ref': None, 'fixed_partner_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': {'value': None, 'unit': 'nM', 'status': 'unavailable', 'reason': 'not_given_in_the_inspected_source_text', 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': 'concentration_series', 'support': None}, 'assay_format': None, 'detection_format': None, 'spread_kind': None, 'fit_model': None, 'readout_signal': None, 'enzyme_conjugate': None, 'blocking_agent': None, 'choice_support': dict.fromkeys(CHOICE_FIELDS), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_elisa', kd=20.0):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_kd': {'locator': 'synthetic', 'quote': 'synthetic fixture: a KD only'}}
    record['quantities']['kd'] = point(kd, 'nM', 'kd', ['span_kd'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_elisa_1', titrant_prep='prep_titrant_a', fixed_prep='prep_coated_a', dataset='dataset_elisa_1', kd=20.0, spread=2.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'titrant_preparation_ref': titrant_prep, 'fixed_partner_preparation_ref': fixed_prep, 'dataset_ref': dataset}
    values = {'kd': kd, 'ki': kd * 1.5, 'ec50': kd * 1.4, 'ic50': kd * 2.25, 'kd_spread': spread, 'ki_spread': spread * 1.5, 'coating_concentration': 2.0, 'signal_maximum': 1.2, 'signal_background': 0.06, 'wash_count': 3, 'titration_point_count': 12, 'technical_replicate_count': 3, 'incubation_time': 90.0, 'temperature': 25.0, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = {**point([kd / 20 * 2 ** step for step in range(12)], 'nM', 'series:' + experiment_ref, refs, 'concentration_series')}
    record['assay_format'] = 'saturation_titration'
    record['detection_format'] = 'indirect'
    record['spread_kind'] = 'standard_error'
    record['fit_model'] = 'four_parameter_logistic'
    record['readout_signal'] = 'absorbance'
    record['enzyme_conjugate'] = 'horseradish_peroxidase'
    record['blocking_agent'] = 'bsa'
    record['choice_support'] = dict.fromkeys(CHOICE_FIELDS, 'direct')      # a hand-built record: every stated choice is direct
    answers ={'blank_subtracted': 'yes', 'nonspecific_binding_checked': 'yes', 'saturation_reached': 'yes', 'signal_in_linear_range': 'yes', 'wash_dissociation_considered': 'yes', 'equilibrium_reached': 'yes', 'avidity_excluded': 'yes', 'coated_protein_active': 'yes', 'detection_does_not_interfere': 'yes', 'independent_experiments': 'yes', 'single_estimate_method': 'no'}
    record['facts'] = {name: fact(answer, refs) for name, answer in answers.items()}
    return record


def real_record():
    """The published ELISA-type solid-phase binding of clusterin (Clu) and the receptor-associated protein (RAP) to the VLDLR
    ectodomain (Nature Structural & Molecular Biology 2025, doi 10.1038/s41594-025-01631-4, PMC12527946), only what its Methods
    paragraph 'Solid-phase binding assay' states: a plate coated with 10 ug/mL VLDLR-ed, blocked with 2% BSA, the ligands bound for
    1 h at room temperature, three washes with blocking solution, an HRP-conjugated secondary antibody, absorbance at 450 nm, the
    no-ligand well signal subtracted, and KD values fitted with a one-site binding model. The KD, EC50, IC50 or Ki values are in the
    Results (not in the paragraph), so none is given here; the concentrations, the replicates, the plateau, the temperature (only
    'room temperature') and the controls other than the blank are not stated. Preparations are unknown."""
    record = blank_record('exp_clu_vldlr_elisa', 'source_pmc12527946', 'hypothesis_clu_binds_vldlr')
    locator = 'Methods, Solid-phase binding assay'
    record['spans'] = {'span_coating': {'locator': locator, 'quote': '10 µg ml−1 VLDLR-ed'},
                       'span_time': {'locator': locator, 'quote': 'ligands Clu or RAP in blocking solution for 1 h'},
                       'span_washes': {'locator': locator, 'quote': 'The plate was washed three times with blocking solution'},
                       'span_enzyme': {'locator': locator, 'quote': 'horseradish peroxidase (HRP)-conjugated'},
                       'span_blocking': {'locator': locator, 'quote': '2% BSA and 0.05% Tween-20'},
                       'span_readout': {'locator': locator, 'quote': 'Absorbance at 450 nm was measured'},
                       'span_model': {'locator': locator, 'quote': 'binding, saturation, one-site-specific binding'},
                       'span_blank': {'locator': locator, 'quote': 'the no-ligand well signal was subtracted'}}
    quantities = {'coating_concentration': (10.0, 'ug/mL', 'span_coating'), 'incubation_time': (60.0, 'min', 'span_time'), 'wash_count': (3, 'count', 'span_washes')}
    for name, (value, unit, span) in quantities.items():
        record['quantities'][name] = point(value, unit, name, [span])
    record['fit_model'] = '1:1'
    record['readout_signal'] = 'absorbance'
    record['enzyme_conjugate'] = 'horseradish_peroxidase'
    record['blocking_agent'] = 'bsa'
    record['choice_support'].update({'fit_model': 'direct', 'readout_signal': 'direct', 'enzyme_conjugate': 'direct', 'blocking_agent': 'direct'})      # the stated choices
    record['facts']['blank_subtracted'] = fact('yes', ['span_blank'])
    record['preparations']['dataset_ref'] = 'dataset_pmc12527946_elisa'
    return record
