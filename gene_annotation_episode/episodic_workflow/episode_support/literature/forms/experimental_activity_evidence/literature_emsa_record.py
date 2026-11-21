"""The extracted record of ONE electrophoretic mobility shift assay (EMSA, gel shift) experiment: a labelled nucleic acid probe (DNA or RNA; radioactive, fluorescent, biotin or infrared labelled) is incubated with a protein and the mixture is run on a native gel; the protein-probe complex migrates more slowly than the free probe, so a shifted band shows binding. The result is QUALITATIVE (a shifted band is seen, or not) or, when the protein is titrated and the fraction of the probe that is shifted is read against the protein concentration, an apparent dissociation constant KD.

What a leaf extraction holds for one EMSA experiment: a labelled probe (a DNA or RNA oligonucleotide or fragment, double or single stranded, labelled with 32P, a fluorophore, biotin read by chemiluminescence, or an infrared dye) is incubated with a protein (purified, or in an extract) in a binding buffer (salt, magnesium, glycerol, often a non-specific competitor nucleic acid such as poly(dI-dC) or salmon sperm DNA) for a time at a temperature, and the mixture is loaded on a native polyacrylamide or agarose gel and run (often in the cold room, at a set voltage, for a set time). Free probe runs fast; probe bound to the protein runs slower, a shifted band. Specificity is shown by competition: an excess of the same unlabelled (cold, specific) probe abolishes the shift, an excess of an unrelated (non-specific) nucleic acid does not; a probe whose binding site is mutated does not shift; a lane of probe alone and a control with a non-specific protein (BSA, or the tag alone) show no shift; an antibody against the protein added to the reaction gives a further retarded band (a supershift) or removes the shifted band, which shows which protein is in the complex. When the protein is titrated, the fraction of the probe in the shifted band (read by densitometry or phosphorimager) against the protein concentration is fitted (a one-site binding model, a Hill model, or a quadratic model for tight binding) to give an apparent KD.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA and pull-down records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What an EMSA shows and what it does not, and what can go wrong, is what the form keeps. The KD is an APPARENT constant, with caveats: the gel is not at equilibrium during the run (a complex that dissociates quickly while it migrates is lost, and the cage effect of the gel can hold a complex together that would fall apart in solution, so the apparent affinity can be too weak or too strong); a smear between the shifted band and the free probe shows dissociation during the run; the probe concentration must be at or below the KD (above it the titration is stoichiometric and the shifted fraction reports the probe concentration, not the KD; a quadratic fit then applies); the protein concentrations must span the KD (the lowest well below it, the highest high enough to shift most of the probe); the binding must be at equilibrium before loading (shown by a time course); the protein must be pure, or its identity confirmed by a supershift; several shifted species (several complexes, or several proteins) cannot be described by one site; and the replicates are independent experiments.

Record fields
-------------
version, experiment_type ('emsa'), experiment_ref, source_ref, assertion_ref
preparations   probe_preparation_ref (the labelled nucleic acid probe), protein_preparation_ref (the protein that is titrated or added), dataset_ref: each a
               string or None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them to the
               merger as its dependence keys (the protein as the analyte key, the probe as the other partner; there is no surface).
quantities     kd, kd_spread, fraction_shifted_highest, protein_concentration_lowest, protein_concentration_highest, probe_concentration, probe_length,
               salt_concentration, magnesium_concentration, glycerol_percent, nonspecific_competitor_amount, specific_competitor_excess, incubation_time,
               incubation_temperature, gel_percent, run_time, run_voltage, run_temperature, titration_point_count, shifted_species_count, replicate_count:
               one operand each.
               Units: kd, kd_spread, protein_concentration_lowest, protein_concentration_highest and probe_concentration pM, nM, uM or mM (kd the apparent
               dissociation constant the source gives; kd_spread its spread; protein_concentration_lowest and _highest the lowest and the highest protein
               concentration of the titration; probe_concentration the concentration of the labelled probe in the reaction); fraction_shifted_highest
               'percent' (the percent of the probe in the shifted band at the highest protein concentration); probe_length 'bp' or 'nt'; salt_concentration
               and magnesium_concentration 'mM' or 'M'; glycerol_percent and gel_percent 'percent'; nonspecific_competitor_amount 'ng' or 'ug' (per reaction);
               specific_competitor_excess 'ratio' (the fold excess of the unlabelled specific probe over the labelled probe); incubation_time and run_time
               's', 'min' or 'h'; incubation_temperature and run_temperature 'C' or 'K'; run_voltage 'V' or 'V/cm'; titration_point_count,
               shifted_species_count and replicate_count 'count'.
probe_type     'dsdna' (double-stranded DNA), 'ssdna' (single-stranded DNA), 'rna', 'other' or None.
probe_label    'p32' (32P, radioactive), 'fluorescent', 'biotin_chemiluminescence' (biotin read by chemiluminescence), 'infrared', 'other' or None.
gel_type       'native_polyacrylamide', 'agarose', 'other' or None.
nonspecific_competitor_type
               'poly_dI_dC', 'salmon_sperm_dna', 'trna', 'other' or None: the non-specific competitor nucleic acid in the binding reaction. Kept in the record
               for the reviewer.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread is.
fit_model      'one_site' (a one-site binding model), 'hill' (a model with a free Hill slope), 'quadratic' (the quadratic solution for tight binding), 'two_site',
               'other' or None.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (probe_type, probe_label, gel_type, nonspecific_competitor_type, spread_kind, fit_model),
               None when the choice is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's
fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (the quote states it only by
implication), 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand and
an 'unknown' fact carry support None. The grader keeps it and does not judge it; the converter does. Rule for the constructors: they take
``support`` and default it to 'direct' only so that forms built by tests, which do not go through the extraction, are direct; the extraction always
passes the model's own value.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_spr_record

SUPPORTS = ('direct', 'implied', 'about_something_else')


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {**literature_spr_record.point(value, unit, key, refs, native_component), 'support': support}


def unavailable(unit, key, reason):
    return {**literature_spr_record.unavailable(unit, key, reason), 'support': None}


def fact(answer, refs=(), support='direct'):
    return {**literature_spr_record.fact(answer, refs), 'support': None if answer == 'unknown' else support}


VERSION = 'a105_emsa_record_v1'
EXPERIMENT_TYPE = 'emsa'
QUANTITIES = ('kd', 'kd_spread', 'fraction_shifted_highest', 'protein_concentration_lowest', 'protein_concentration_highest', 'probe_concentration', 'probe_length', 'salt_concentration', 'magnesium_concentration', 'glycerol_percent', 'nonspecific_competitor_amount', 'specific_competitor_excess', 'incubation_time', 'incubation_temperature', 'gel_percent', 'run_time', 'run_voltage', 'run_temperature', 'titration_point_count', 'shifted_species_count', 'replicate_count')
PREPARATION_KEYS = ('probe_preparation_ref', 'protein_preparation_ref', 'dataset_ref')
PROBE_TYPES = ('dsdna', 'ssdna', 'rna', 'other')
PROBE_LABELS = ('p32', 'fluorescent', 'biotin_chemiluminescence', 'infrared', 'other')
GEL_TYPES = ('native_polyacrylamide', 'agarose', 'other')
COMPETITOR_TYPES = ('poly_dI_dC', 'salmon_sperm_dna', 'trna', 'other')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('one_site', 'hill', 'quadratic', 'two_site', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'shift_detected': YES_NO, 'shift_abolished_by_specific_competitor': YES_NO, 'shift_not_abolished_by_nonspecific_competitor': YES_NO, 'mutant_probe_does_not_shift': YES_NO, 'probe_alone_lane_shown': YES_NO, 'nonspecific_protein_control_done': YES_NO, 'free_probe_quantified': YES_NO, 'probe_at_or_below_kd': YES_NO, 'equilibrium_reached': YES_NO, 'supershift_confirms_protein_identity': YES_NO, 'protein_purified': YES_NO, 'complex_survives_gel_run': YES_NO, 'protein_range_brackets_kd': YES_NO, 'independent_experiments': YES_NO, 'single_estimate_method': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
TIME_UNITS = ('s', 'min', 'h')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'fraction_shifted_highest': ('percent',), 'protein_concentration_lowest': CONCENTRATION_UNITS, 'protein_concentration_highest': CONCENTRATION_UNITS, 'probe_concentration': CONCENTRATION_UNITS, 'probe_length': ('bp', 'nt'), 'salt_concentration': ('mM', 'M'), 'magnesium_concentration': ('mM', 'M'), 'glycerol_percent': ('percent',), 'nonspecific_competitor_amount': ('ng', 'ug'), 'specific_competitor_excess': ('ratio',), 'incubation_time': TIME_UNITS, 'incubation_temperature': ('C', 'K'), 'gel_percent': ('percent',), 'run_time': TIME_UNITS, 'run_voltage': ('V', 'V/cm'), 'run_temperature': ('C', 'K'), 'titration_point_count': ('count',), 'shifted_species_count': ('count',), 'replicate_count': ('count',)}
