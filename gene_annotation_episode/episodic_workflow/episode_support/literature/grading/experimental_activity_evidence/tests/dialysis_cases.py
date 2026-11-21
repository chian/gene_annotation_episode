"""Equilibrium dialysis / ultrafiltration binding experiment records for the dialysis grader, converter and merger tests.

synthetic_record: a fully specified, explicitly SYNTHETIC QUANTITATIVE record (not a publication) used to exercise every criterion's supported path. Its numbers, worked by hand: a
saturation series of six total ligand concentrations (50, 100, 200, 400, 800 and 1600 nM; 0.25 to 8 times the KD) of a ligand against 1000 nM of a protein in a rapid equilibrium dialysis (RED) device (membrane cutoff 10 kDa, 100 uL of the
protein chamber against 300 uL of buffer, 37 C, pH 7.4, 150 mM salt) kept for 6 hours, with the ligand measured by LC-MS/MS; at one reading the total ligand concentration is 500 nM, the free ligand 200 nM and the bound 300 nM
(60 percent bound, 40 percent unbound, a fraction bound of 0.6 and a fraction unbound of 0.4); a KD of 200 nM (standard error 20 nM, one-site fit), a Ki of 500 nM (standard error 50 nM) and one binding site per protein; recovery 95 percent,
adsorption to the membrane and the device 5 percent, a volume shift of 3 percent; two cells per experiment and three independent experiments; every control done and passed (binding observed, an equilibrium time course, a
mass balance, adsorption checked and corrected, volume shift corrected, a stable ligand, a free ligand measured directly, a protein that stays behind the membrane, a buffer-only control, a protein concentration above the KD, one method).
qualitative_record: the same experiment reported only as a fraction bound at one concentration: no KD, no Ki, no Bmax, no series and no fit model (the protein-over-KD fact is unknown).
sparse_record: only the statement that binding was observed; everything else is an unavailable operand or an 'unknown' fact.
low_binding_record: the qualitative record with a percent bound of 3 (and a percent unbound of 97) and no statement of binding.
real_record: see below (the published case).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dialysis_record import EXPERIMENT_TYPE, FACTS, QUANTITIES, UNITS as UNIT_VOCABULARIES, VERSION, fact, point, unavailable

UNITS = {name: units[0] for name, units in UNIT_VOCABULARIES.items()}
UNITS.update({name: 'nM' for name in ('kd', 'kd_spread', 'ki', 'ki_spread', 'ligand_total_concentration', 'free_ligand_concentration', 'bound_ligand_concentration', 'protein_concentration', 'ligand_range_lowest', 'ligand_range_highest', 'concentration_series')})
UNITS.update({'bmax': 'ratio', 'equilibration_time': 'h'})
CHOICES = ('separation_method', 'device_type', 'detection', 'spread_kind', 'fit_model')
KD_FIELDS = ('kd', 'kd_spread', 'bmax', 'ki', 'ki_spread', 'ligand_range_lowest', 'ligand_range_highest', 'titration_point_count')
SERIES = [50.0, 100.0, 200.0, 400.0, 800.0, 1600.0]


def blank_record(experiment_ref, source_ref, assertion_ref):
    return {'version': VERSION, 'experiment_type': EXPERIMENT_TYPE, 'experiment_ref': experiment_ref, 'source_ref': source_ref, 'assertion_ref': assertion_ref, 'preparations': {'ligand_preparation_ref': None, 'protein_preparation_ref': None, 'dataset_ref': None}, 'quantities': {name: unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text') for name in QUANTITIES}, 'concentration_series': unavailable('nM', 'concentration_series', 'not_given_in_the_inspected_source_text'), **dict.fromkeys(CHOICES), 'choice_support': dict.fromkeys(CHOICES), 'facts': {name: fact('unknown') for name in FACTS}, 'spans': {}}


def sparse_record(experiment_ref='exp_sparse_dialysis'):
    record = blank_record(experiment_ref, 'source_sparse', 'hypothesis_synthetic_binding')
    record['spans'] = {'span_binding': {'locator': 'synthetic', 'quote': 'synthetic fixture: binding was observed'}}
    record['facts']['binding_detected'] = fact('yes', ['span_binding'])
    return record


def synthetic_record(experiment_ref='exp_synthetic_dialysis_1', ligand='prep_ligand_a', protein='prep_protein_a', dataset='dataset_dialysis_1', kd=200.0, spread=20.0, assertion='hypothesis_synthetic_binding'):
    record = blank_record(experiment_ref, 'source_synthetic', assertion)
    refs = ['span_' + experiment_ref]
    record['spans'] = {refs[0]: {'locator': 'synthetic', 'quote': 'synthetic fixture'}}
    record['preparations'] = {'ligand_preparation_ref': ligand, 'protein_preparation_ref': protein, 'dataset_ref': dataset}
    values = {'kd': kd, 'kd_spread': spread, 'bmax': 1.0, 'ki': 500.0, 'ki_spread': 50.0, 'percent_bound': 60.0, 'percent_unbound': 40.0, 'fraction_bound': 0.6, 'fraction_unbound': 0.4, 'ligand_total_concentration': 500.0, 'free_ligand_concentration': 200.0,
              'bound_ligand_concentration': 300.0, 'protein_concentration': 1000.0, 'ligand_range_lowest': 50.0, 'ligand_range_highest': 1600.0, 'titration_point_count': 6, 'membrane_cutoff': 10.0, 'equilibration_time': 6.0, 'run_temperature': 37.0, 'buffer_ph': 7.4,
              'salt_concentration': 150.0, 'protein_chamber_volume': 100.0, 'buffer_chamber_volume': 300.0, 'recovery': 95.0, 'membrane_adsorption': 5.0, 'volume_shift': 3.0, 'technical_replicate_count': 2, 'replicate_count': 3}
    for name, value in values.items():
        record['quantities'][name] = point(value, UNITS[name], name + ':' + experiment_ref, refs, name)
    record['concentration_series'] = point(list(SERIES), 'nM', 'series:' + experiment_ref, refs, 'concentration_series')
    record.update({'separation_method': 'rapid_equilibrium_dialysis', 'device_type': 'red_device', 'detection': 'lc_msms', 'spread_kind': 'standard_error', 'fit_model': 'one_site'})
    record['choice_support'] = dict.fromkeys(CHOICES, 'direct')
    record['facts'] = {name: fact('yes', refs) for name in FACTS}
    return record


def qualitative_record(experiment_ref='exp_qualitative_dialysis_1', ligand='prep_ligand_aq', protein='prep_protein_aq', dataset='dataset_dialysis_q', assertion='hypothesis_synthetic_binding'):
    record = synthetic_record(experiment_ref, ligand, protein, dataset, assertion=assertion)
    for name in KD_FIELDS:
        record['quantities'][name] = unavailable(UNITS[name], name, 'not_given_in_the_inspected_source_text')
    record['concentration_series'] = unavailable('nM', 'concentration_series', 'not_given_in_the_inspected_source_text')
    record['spread_kind'] = record['fit_model'] = None
    record['choice_support']['spread_kind'] = record['choice_support']['fit_model'] = None
    record['facts']['protein_at_or_above_kd'] = fact('unknown')
    return record


def low_binding_record(experiment_ref='exp_low_binding_dialysis'):
    record = qualitative_record(experiment_ref)
    refs = ['span_' + experiment_ref]
    record['quantities']['percent_bound'] = point(3.0, 'percent', 'percent_bound:' + experiment_ref, refs, 'percent_bound')
    record['quantities']['percent_unbound'] = point(97.0, 'percent', 'percent_unbound:' + experiment_ref, refs, 'percent_unbound')
    for name in ('fraction_bound', 'fraction_unbound'):
        record['quantities'][name] = unavailable('ratio', name, 'not_given_in_the_inspected_source_text')
    record['facts']['binding_detected'] = fact('unknown')
    return record


# The published text the grader tests quote from: PMC7996760 (Perfluoroalkyl Acid Binding with Peroxisome Proliferator-Activated Receptors alpha, gamma and delta, and Fatty Acid Binding Proteins by Equilibrium
# Dialysis with a Comparison of Methods, Toxics 2021, 9(3), 45, doi 10.3390/toxics9030045, PMID 33652875, CC BY 4.0).
REAL_SOURCE = 'PMC7996760'
REAL_LOCATOR = 'Methods, equilibrium dialysis (EqD) experiments'
REAL_QUOTES = {
    'span_cutoff': 'molecular weight cutoff: 10kDa',
    'span_ph': 'phosphate buffered saline (pH 7.4)',
    'span_buffer_volume': 'first adding 1.2 mL of the 18.1 mS/cm phosphate buffered saline',
    'span_protein_volume': 'the total volume in the dialysis cup was brought to 100 μL',
    'span_time': 'for 36 h to reach equilibrium',
    'span_duplicate': 'All dialysis tests were performed in duplicate',
    'span_retained': 'impermeable to the proteins used',
    'span_device': 'A Slide-a-Lyzer mini dialysis cup containing a semi-permeable membrane',
}


def real_record():
    """The two published Methods paragraphs on the equilibrium dialysis of the perfluoroalkyl acids with the proteins (PMC7996760, Toxics 2021, CC BY 4.0), only what they state about the experiment: a Slide-a-Lyzer mini dialysis
    cup with a 10 kDa cutoff membrane in a tube with 1.2 mL of phosphate buffered saline (pH 7.4), a final volume of 100 uL in the cup, a membrane that is impermeable to the proteins, 36 h on a rocker to reach equilibrium, and the dialysis
    tests in duplicate. It states no KD, no percent bound and no result, no protein concentration as one value (1 uM for three proteins and 0.48 uM for two), no salt, no temperature in degrees, no detection, no control result and no
    independent experiments. Preparations are unknown (the ligands are perfluoroalkyl acids, the proteins are L-FABP, I-FABP and PPAR-alpha, -gamma and -delta)."""
    record = blank_record('exp_pfas_protein_eqd_methods', 'source_pmc7996760', 'hypothesis_pfas_binds_protein')
    record['spans'] = {span: {'locator': REAL_LOCATOR, 'quote': quote} for span, quote in REAL_QUOTES.items()}
    for name, (value, unit, span) in {'membrane_cutoff': (10.0, 'kDa', 'span_cutoff'), 'buffer_ph': (7.4, 'pH', 'span_ph'), 'buffer_chamber_volume': (1.2, 'mL', 'span_buffer_volume'),
                                      'protein_chamber_volume': (100.0, 'uL', 'span_protein_volume'), 'equilibration_time': (36.0, 'h', 'span_time'), 'technical_replicate_count': (2, 'count', 'span_duplicate')}.items():
        record['quantities'][name] = point(value, unit, name, [span])
    record['facts']['protein_retained'] = fact('yes', ['span_retained'])
    record['separation_method'] = 'equilibrium_dialysis'
    record['device_type'] = 'dialysis_cup'
    record['choice_support'].update(separation_method='direct', device_type='direct')
    record['preparations']['dataset_ref'] = 'dataset_pmc7996760_eqd_methods'
    return record


def real_kd_record():
    """The published Results paragraph of the same paper on the PFHxA - PPAR-alpha pair (PMC7996760, CC BY 4.0), only what it states about that experiment: binding was observed by the EqD experiments, the KD is 0.097 uM,
    and the method is dialysis. It states no spread of the KD, no concentration, time, device, detection, control or replicate. The binding of PFBA and PFHpA, which it says did not bind, is another experiment."""
    record = blank_record('exp_pfhxa_ppar_alpha_eqd', 'source_pmc7996760', 'hypothesis_pfhxa_binds_ppar_alpha')
    locator = 'Results, PPAR-alpha'
    record['spans'] = {'span_binding': {'locator': locator, 'quote': 'Strong binding for PFHxA (Figure 4A) and PFNA (Figure 4B) were observed via EqD experiments'},
                       'span_kd': {'locator': locator, 'quote': 'the KD of 0.097 μM for PFHxA'}}
    record['quantities']['kd'] = point(0.097, 'uM', 'kd', ['span_kd'])
    record['facts']['binding_detected'] = fact('yes', ['span_binding'])
    record['separation_method'] = 'equilibrium_dialysis'
    record['choice_support']['separation_method'] = 'direct'
    record['preparations']['dataset_ref'] = 'dataset_pmc7996760_eqd_results'
    return record
