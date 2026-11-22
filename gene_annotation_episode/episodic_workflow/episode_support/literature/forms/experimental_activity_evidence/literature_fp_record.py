"""The extracted record of ONE fluorescence polarization / fluorescence anisotropy (FP/FA) binding experiment.

What a leaf extraction holds for one FP binding experiment: a fluorescently labelled tracer (probe) at a fixed
concentration is mixed with a titrant series, and the binding is read from the rise of the polarization (mP) or
anisotropy (r) of the emitted light as the tracer is bound. One experiment, or replicate titrations reported as one
result, in the same operand shape as the SPR, ITC, BLI and GCI records and the existing A105 assay grading inputs (value,
unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an
operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors
point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

FP differs from the surface and calorimetric methods in what the experiment is: it is a solution measurement without a
surface, read at equilibrium from a signal whose total span (the window between free and bound tracer) is small; the
constant that is read off the curve is the tracer's KD only when the tracer concentration is at or below that KD
(otherwise the tracer depletes the titrant and a quadratic, tight-binding fit is needed); a change of the tracer's total
fluorescence on binding (quantum yield) distorts the fraction bound unless it is corrected; and in the competition
(displacement) format an unlabelled ligand displaces the tracer and what is read is an inhibition constant Ki, a different
quantity from the direct-titration KD. The form keeps exactly those things.

Record fields
-------------
version, experiment_type ('fp'), experiment_ref, source_ref, assertion_ref
preparations   titrant_preparation_ref (the protein or ligand titrated), tracer_preparation_ref (the labelled partner),
               dataset_ref: each a string or None (unknown). The converter hands them to the merger as its dependence
               keys (titrant as the analyte key, tracer as the other partner; an FP experiment has no surface).
quantities     kd, ki, kd_spread, ki_spread, ic50, tracer_concentration, signal_minimum, signal_maximum, signal_noise,
               total_intensity_change, assay_volume, incubation_time, temperature, replicate_count: one operand each.
               Units: kd/ki/kd_spread/ki_spread/ic50/tracer_concentration pM, nM, uM or mM; signal_minimum and signal_maximum
               mP or r (the polarization in millipolarization units, or the anisotropy); signal_noise mP only (the standard
               deviation of replicate polarization reads, so the window can be read against the paper's own noise; an
               anisotropy noise is not converted and stays unavailable); ic50 is the half-inhibition concentration of a
               competition, which the competitor series should bracket; total_intensity_change percent
               (the size of the relative change of the tracer's total fluorescence intensity on binding); assay_volume uL
               or mL; incubation_time s, min or h; temperature C or K; replicate_count count.
concentration_series
               operand whose 'value' is a list of titrant concentrations (unit pM, nM, uM or mM), or None when not given.
               In the competition format it is the competitor series.
assay_format   'direct_titration' (the tracer is titrated with its partner; KD) or 'competition' (an unlabelled ligand
               displaces the tracer; Ki) or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread / ki_spread are.
intensity_change_direction
               'increase' or 'decrease' or None: whether the tracer's total fluorescence intensity rose or fell on binding
               (the size is total_intensity_change; the direction fixes the size of the bias of the apparent KD).
series_kind    'titrant' (the series is the partner added to the tracer) or 'competitor' (the series is the unlabelled
               competitor of a competition) or None.
fit_model      '1:1', 'hill', 'quadratic', 'competitive_binding', 'other' or None.
plate_type     'black_non_binding', 'black_standard', 'cuvette', 'other' or None. The plate or cell the reads were made in,
               kept in the record for the reviewer; no criterion judges it.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a
               controlled answer only.
               binding_detected is the experiment's stated yes/no result (the passage says the two partners bound, or says
               they did not); no criterion reads it. It lets a result that is stated without a constant count (owner, 2026-11-22).
choice_support name -> support of each plain choice field (assay_format, spread_kind, fit_model, plate_type), None when the
               field is not stated.
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

VERSION = 'a105_fp_record_v2'
EXPERIMENT_TYPE = 'fp'
QUANTITIES = ('kd', 'ki', 'kd_spread', 'ki_spread', 'ic50', 'tracer_concentration', 'signal_minimum', 'signal_maximum', 'signal_noise', 'total_intensity_change', 'assay_volume', 'incubation_time', 'temperature', 'replicate_count')
PREPARATION_KEYS = ('titrant_preparation_ref', 'tracer_preparation_ref', 'dataset_ref')
ASSAY_FORMATS = ('direct_titration', 'competition')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('1:1', 'hill', 'quadratic', 'competitive_binding', 'other')
PLATE_TYPES = ('black_non_binding', 'black_standard', 'cuvette', 'other')
INTENSITY_DIRECTIONS = ('increase', 'decrease')
SERIES_KINDS = ('titrant', 'competitor')
CHOICES = ('assay_format', 'spread_kind', 'fit_model', 'plate_type', 'intensity_change_direction', 'series_kind')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'tracer_at_or_below_kd': YES_NO, 'equilibrium_reached': YES_NO, 'tight_binding_considered': YES_NO, 'intensity_change_checked': YES_NO, 'free_probe_baseline_measured': YES_NO, 'nonspecific_binding_checked': YES_NO, 'unlabelled_competitor_displaces': YES_NO, 'surface_adsorption_prevented': YES_NO, 'independent_titrations': YES_NO, 'single_estimate_method': YES_NO, 'binding_detected': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
SIGNAL_UNITS = ('mP', 'r')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'ki': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'ki_spread': CONCENTRATION_UNITS, 'ic50': CONCENTRATION_UNITS, 'tracer_concentration': CONCENTRATION_UNITS, 'signal_minimum': SIGNAL_UNITS, 'signal_maximum': SIGNAL_UNITS, 'signal_noise': ('mP',),'total_intensity_change': ('percent',), 'assay_volume': ('uL', 'mL'), 'incubation_time': ('s', 'min', 'h'), 'temperature': ('C', 'K'), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
