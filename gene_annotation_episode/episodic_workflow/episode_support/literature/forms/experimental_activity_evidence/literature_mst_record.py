"""The extracted record of ONE MST (microscale thermophoresis) binding experiment, in solution, in capillaries.

What a leaf extraction holds for one microscale thermophoresis (MST) binding experiment (for example on a NanoTemper
Monolith, with a fluorescent label or label-free): one binding partner is held at a fixed, constant concentration and
is the one that is detected (labelled with a dye, or detected through its intrinsic tryptophan fluorescence), the other
partner (the titrant) is added in a dilution series, the samples are drawn into capillaries, an infrared laser heats a
small spot, and the binding is read from the change of the normalized fluorescence Fnorm (the fluorescence after
heating, F-hot, over the fluorescence before heating, F-cold) with the titrant concentration, as a titration (KD) or as a
competition (an unlabelled ligand displaces the labelled partner; Ki). One experiment, or replicate titrations reported
as one result, in the same operand shape as the SPR, ITC, BLI, GCI, FP and FRET records and the existing A105 assay
grading inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source
did not give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain
constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

MST differs from the other methods in what is measured and what can go wrong: the signal (the thermophoresis, the
temperature-jump of the dye, or the change of the initial fluorescence) depends on the size, the charge and the hydration
shell of the detected partner, so a binding that does not change them gives no signal; the detected partner must be at a
constant concentration in every capillary, so the initial fluorescence (the fluorescence before heating) must not change
with the titrant, and a change of it (quenching or enhancement by the ligand, or by its absorbance) can mimic binding
(the SD-test and the plot of the initial fluorescence against the titrant check this); aggregation or adsorption of a
partner to the capillary wall changes the shape of the fluorescence peak in the capillary scan and the signal; the
fluorescence must be within the range the instrument can read; the read has a time window for F-hot, and a window that
starts too early reads the temperature-jump of the dye instead of the thermophoresis; the label (a covalent NHS dye, a
His-tag dye, a fluorescent protein) can alter the binding; and the signal-to-noise of the curve decides whether a KD can
be fitted. The form keeps exactly those things.

Record fields
-------------
version, experiment_type ('mst'), experiment_ref, source_ref, assertion_ref
preparations   titrant_preparation_ref (the partner added in a series, or in competition the unlabelled competitor),
               fixed_partner_preparation_ref (the detected partner held at a fixed concentration), dataset_ref: each a
               string or None (unknown). The converter hands them to the merger as its dependence keys (titrant as the
               analyte key, the fixed partner as the other partner; an MST experiment in solution has no surface).
quantities     kd, ki, ec50, kd_spread, ki_spread, labelled_concentration, fnorm_amplitude, fnorm_noise, signal_to_noise, led_power,
               ir_laser_power, fhot_time, titration_point_count, incubation_time, temperature, replicate_count: one operand
               each.
               Units: kd/ki/ec50/kd_spread/ki_spread/labelled_concentration pM, nM, uM or mM; fnorm_amplitude and fnorm_noise 'permille'
               (the change of Fnorm between the unbound and the bound state, in per mille, as a positive number; fnorm_noise is the stated
               noise of Fnorm, the scatter of the points about the fit or of the repeated reads, in per mille, which lets the sheet
               read the amplitude against the paper's own instrument noise when no signal-to-noise is stated);
               signal_to_noise 'ratio'; led_power and ir_laser_power 'percent' (the excitation LED power and the infrared
               laser (MST) power as the passage gives them in percent); fhot_time s or ms (the time after the infrared
               laser is switched on at which F-hot is read, the start of the F-hot window); titration_point_count and
               replicate_count 'count'; incubation_time s, min or h; temperature C or K.
concentration_series
               operand whose 'value' is a list of titrant concentrations (unit pM, nM, uM or mM), or None when not given.
               In the competition format it is the competitor series.
assay_format   'direct_titration' (the detected partner is titrated with its partner; KD) or 'competition' (an unlabelled
               ligand displaces the detected partner; Ki) or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread / ki_spread are.
fit_model      '1:1', 'hill', 'quadratic', 'competitive_binding', 'other' or None.
readout_signal 'thermophoresis' (Fnorm read at an F-hot time after the temperature jump has finished), 't_jump' (Fnorm read
               in the first second after the infrared laser is switched on, the temperature jump of the dye),
               'initial_fluorescence' (the change of the fluorescence before heating is the binding signal) or None.
capillary_type 'standard', 'premium', 'hydrophilic', 'other' or None. The capillary the samples were drawn into, kept in
               the record for the reviewer; no criterion judges it.
label_type     'covalent_nhs_dye' (a dye attached to lysines by an NHS ester), 'his_tag_nta_dye' (a dye carried by a
               tris-NTA group on a His tag), 'fluorescent_protein_fusion' (for example GFP), 'label_free_intrinsic_fluorescence'
               (the intrinsic tryptophan fluorescence of the label-free instrument), 'other' or None.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a
               controlled answer only.
               binding_detected is the experiment's stated yes/no result (the passage
               says the two partners bound, or says they did not); no criterion reads
               it. It lets a result stated without a constant count (owner, 2026-11-22).
choice_support name -> support of each plain choice field (the choice fields of the extraction: assay_format, spread_kind, fit_model,
               readout_signal, capillary_type, label_type), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries
'support', the extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or
fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the topic but is really
about another measurement or condition). An unavailable operand, an 'unknown' fact and an unstated choice carry None. The
grader does not judge it; the converter does. Rule for the constructors: they take ``support`` and default it to
'direct', and the default is only for forms built by tests that do not go through the extraction (the extraction always
passes the model's answer).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_spr_record

SUPPORTS = ('direct', 'implied', 'about_something_else')


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {**literature_spr_record.point(value, unit, key, refs, native_component), 'support': support}


def unavailable(unit, key, reason):
    return {**literature_spr_record.unavailable(unit, key, reason), 'support': None}


def fact(answer, refs=(), support='direct'):
    return {**literature_spr_record.fact(answer, refs), 'support': None if answer == 'unknown' else support}

VERSION = 'a105_mst_record'
EXPERIMENT_TYPE = 'mst'
QUANTITIES = ('kd', 'ki', 'ec50', 'kd_spread', 'ki_spread', 'labelled_concentration', 'fnorm_amplitude', 'fnorm_noise', 'signal_to_noise', 'led_power', 'ir_laser_power', 'fhot_time', 'titration_point_count', 'incubation_time', 'temperature', 'replicate_count')
PREPARATION_KEYS = ('titrant_preparation_ref', 'fixed_partner_preparation_ref', 'dataset_ref')
ASSAY_FORMATS = ('direct_titration', 'competition')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('1:1', 'hill', 'quadratic', 'competitive_binding', 'other')
READOUT_SIGNALS = ('thermophoresis', 't_jump', 'initial_fluorescence')
CAPILLARY_TYPES = ('standard', 'premium', 'hydrophilic', 'other')
LABEL_TYPES = ('covalent_nhs_dye', 'his_tag_nta_dye', 'fluorescent_protein_fusion', 'label_free_intrinsic_fluorescence', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'initial_fluorescence_checked': YES_NO, 'initial_fluorescence_consistent': YES_NO, 'fluorescence_intensity_in_range': YES_NO, 'aggregation_or_adsorption_checked': YES_NO, 'detergent_or_carrier_in_buffer': YES_NO, 'labelled_partner_at_or_below_kd': YES_NO, 'tight_binding_considered': YES_NO, 'equilibrium_reached': YES_NO, 'labelling_does_not_alter_binding': YES_NO, 'nonspecific_binding_checked': YES_NO, 'independent_titrations': YES_NO, 'single_estimate_method': YES_NO, 'binding_detected': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'ki': CONCENTRATION_UNITS, 'ec50': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'ki_spread': CONCENTRATION_UNITS, 'labelled_concentration': CONCENTRATION_UNITS, 'fnorm_amplitude': ('permille',), 'fnorm_noise': ('permille',), 'signal_to_noise': ('ratio',), 'led_power': ('percent',), 'ir_laser_power': ('percent',), 'fhot_time': ('s', 'ms'), 'titration_point_count': ('count',), 'incubation_time': ('s', 'min', 'h'), 'temperature': ('C', 'K'), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
