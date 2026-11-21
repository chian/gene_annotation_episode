"""The extracted record of ONE size-exclusion chromatography (SEC, gel filtration), with or without in-line multi-angle light scattering (SEC-MALS), complex experiment: two proteins are mixed and run on a size-exclusion column; if they form a complex the mixture elutes earlier than either component run alone, in a co-elution peak whose SDS-PAGE (or absorbance) shows both partners; SEC-MALS gives the absolute molar mass of the peak (and so the stoichiometry of the complex) in solution. The result is mostly QUALITATIVE or semi-quantitative (a complex peak, a shift of the elution volume, a measured molar mass against the expected one, a stoichiometry); occasionally the mixture is titrated and an apparent dissociation constant KD is derived from the areas of the complex and the free-component peaks.

What a leaf extraction holds for one SEC experiment: a mixture of two proteins (each at a concentration, in a volume, incubated for a time before the injection) is injected on a size-exclusion column (Superdex, Superose or another resin; a flow rate; a temperature) in a running buffer (salt) and the elution is followed by absorbance (A280, A260), by refractive index, by light scattering or by fluorescence. Each component is run alone on the same column; the complex peak is the one that elutes earlier than either. The elution volume (the volume at the peak) is not a mass: it reflects the hydrodynamic radius, so the column is calibrated with standards of known size if a mass is read from it; SEC-MALS measures the molar mass of the peak directly by light scattering and refractive index, and so also shows aggregation (the polydispersity Mw/Mn) and the stoichiometry. The fractions of the peak are run on SDS-PAGE to show which proteins are in it. A mutant that does not bind, or an unrelated protein, run in place of one partner is the single-component control. When the mixture is titrated, the areas of the complex peak and the free-component peak give the fraction bound and an apparent KD.
One experiment, or replicate experiments reported as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down and EMSA records and the existing A105 assay grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

What an SEC shows and what it does not, and what can go wrong, is what the form keeps. The sample is DILUTED on the column (about ten- to twenty-fold between the injection and the peak): a complex with a KD above the concentration in the peak dissociates on the column, so a weak complex can be missed and the concentration that matters is the one in the peak, not the injected one; a complex that exchanges quickly (fast on and off) elutes as one broadened peak between the free and the complex positions and is not resolved; the elution volume depends on the hydrodynamic radius and the shape of the molecules, not on mass alone, so a shifted elution volume is not a mass (the molar mass is the MALS result, or a calibration against standards); the resin can interact with the protein (at low ionic strength, or by sticky proteins), which delays the elution; aggregates elute early and can be taken for a complex (the polydispersity Mw/Mn of a monodisperse peak is close to 1); the shift must be seen against each component alone on the same column, and a control with a non-binding component shows that the shift is not nonspecific; the apparent KD from peak areas is read at non-equilibrium and diluted conditions, and the replicates are independent experiments.

Record fields
-------------
version, experiment_type ('sec'), experiment_ref, source_ref, assertion_ref
preparations   component_a_preparation_ref, component_b_preparation_ref (the two proteins that are mixed, in the order the caller names them), dataset_ref: each a
               string or None (unknown). They are references to records, which the caller supplies; no passage states them. The converter hands them to the
               merger as its dependence keys (component a as the analyte key, component b as the other partner; there is no surface).
quantities     kd, kd_spread, complex_elution_volume, component_elution_volume_earlier, component_elution_volume_later, elution_volume_shift,
               complex_mass_measured, complex_mass_theoretical, component_mass_measured_larger, component_mass_measured_smaller, stoichiometry_ratio,
               polydispersity, flow_rate, run_temperature, loaded_concentration, loaded_volume, salt_concentration, incubation_time, replicate_count:
               one operand each.
               Units: kd and kd_spread pM, nM, uM or mM (the apparent dissociation constant from peak areas and its spread); complex_elution_volume,
               component_elution_volume_earlier, component_elution_volume_later and elution_volume_shift 'mL' (the elution volume at the peak of the complex, of
               the component that elutes earlier alone and of the one that elutes later alone, and the shift between the complex and the earlier component);
               complex_mass_measured, complex_mass_theoretical, component_mass_measured_larger and component_mass_measured_smaller 'kDa' (the molar mass of the
               complex peak by MALS, the mass the complex should have, and the molar mass by MALS of the larger and of the smaller component run alone);
               stoichiometry_ratio and polydispersity 'ratio' (the molar ratio of the components in the complex, first named over second named; Mw/Mn);
               flow_rate 'mL/min'; run_temperature 'C' or 'K'; loaded_concentration 'nM', 'uM' or 'mM' (the concentration of the mixture that was injected);
               loaded_volume 'uL' or 'mL'; salt_concentration 'mM' or 'M' (monovalent salt of the running buffer); incubation_time 's', 'min' or 'h' (before
               the injection); replicate_count 'count'.
column_type    'superdex', 'superose', 'srt' (SRT SEC), 'other' or None.
detection      'absorbance_280', 'absorbance_260', 'refractive_index', 'light_scattering', 'fluorescence', 'other' or None. The detector on which the result is read.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread is.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (column_type, detection, spread_kind), None when the choice is not stated.
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


VERSION = 'a105_sec_record_v1'
EXPERIMENT_TYPE = 'sec'
QUANTITIES = ('kd', 'kd_spread', 'complex_elution_volume', 'component_elution_volume_earlier', 'component_elution_volume_later', 'elution_volume_shift', 'complex_mass_measured', 'complex_mass_theoretical', 'component_mass_measured_larger', 'component_mass_measured_smaller', 'stoichiometry_ratio', 'polydispersity', 'flow_rate', 'run_temperature', 'loaded_concentration', 'loaded_volume', 'salt_concentration', 'incubation_time', 'replicate_count')
PREPARATION_KEYS = ('component_a_preparation_ref', 'component_b_preparation_ref', 'dataset_ref')
COLUMN_TYPES = ('superdex', 'superose', 'srt', 'other')
DETECTIONS = ('absorbance_280', 'absorbance_260', 'refractive_index', 'light_scattering', 'fluorescence', 'other')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'complex_peak_detected': YES_NO, 'components_run_alone': YES_NO, 'complex_peak_analysed_by_sds_page': YES_NO, 'free_peak_decreases_with_titration': YES_NO, 'mals_mass_matches_complex': YES_NO, 'column_calibrated_with_standards': YES_NO, 'buffer_rules_out_resin_interaction': YES_NO, 'complex_stable_on_column': YES_NO, 'aggregation_absent': YES_NO, 'single_component_control_done': YES_NO, 'independent_experiments': YES_NO, 'single_estimate_method': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
TIME_UNITS = ('s', 'min', 'h')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'complex_elution_volume': ('mL',), 'component_elution_volume_earlier': ('mL',), 'component_elution_volume_later': ('mL',), 'elution_volume_shift': ('mL',), 'complex_mass_measured': ('kDa',), 'complex_mass_theoretical': ('kDa',), 'component_mass_measured_larger': ('kDa',), 'component_mass_measured_smaller': ('kDa',), 'stoichiometry_ratio': ('ratio',), 'polydispersity': ('ratio',), 'flow_rate': ('mL/min',), 'run_temperature': ('C', 'K'), 'loaded_concentration': ('nM', 'uM', 'mM'), 'loaded_volume': ('uL', 'mL'), 'salt_concentration': ('mM', 'M'), 'incubation_time': TIME_UNITS, 'replicate_count': ('count',)}
