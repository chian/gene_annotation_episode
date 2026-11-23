"""The extracted record of ONE FCS (fluorescence correlation spectroscopy) or FCCS (dual-colour fluorescence cross-correlation) binding titration.

What a leaf extraction holds for one fluorescence correlation spectroscopy binding experiment: a fluorescently labelled
partner is held at a fixed, low concentration (about one to ten nM, so that a few molecules, about 0.1 to 10, are in
the confocal detection volume at any time), the other partner (the titrant) is added in a series, the fluctuations of the
fluorescence of the small confocal volume are autocorrelated, and the KD is fitted from the change with the titrant
concentration of what the correlation curve reports about the labelled partner: its diffusion time (or its diffusion
coefficient, which becomes slower when it binds the larger partner) and the fraction of it that is bound, or its brightness
(counts per molecule), or, in the dual-colour variant (FCCS), the amplitude of the cross-correlation of two differently
labelled partners that diffuse together. One experiment, or replicate titrations reported as one result, in the same operand
shape as the SPR, ITC, BLI, GCI, FP, FRET, MST and Trp records and the existing A105 assay grading inputs (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not give is an operand
with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain constructors point, unavailable
and fact are the SPR record module's; they are shared because they only build operands.

FCS differs from the other methods in what is measured and what can go wrong: the signal is the diffusion, which depends only
weakly on the size of the partner (the diffusion time grows with the cube root of the mass, so doubling the mass changes it
by only about 26 percent, and a two-component fit can only separate two species when their diffusion times differ by at
least about 1.6-fold); the amplitude of the correlation is the inverse of the number of molecules in the confocal volume, so the
labelled partner must be at a low concentration; the confocal volume (its structure parameter) must be calibrated with a
reference dye of known diffusion coefficient (for example Rhodamine 6G or Alexa 488) before a diffusion time can be turned
into a diffusion coefficient; a fit with one component of a mixture of free and bound partner gives only an apparent time, so
the fraction bound needs the free and the bound reference times, and a two-component fit is stable only when the free time is
fixed from a measurement of the free partner; the triplet state of the dye adds a fast decay that has to be included; the
brightness of the complex can differ from that of the free partner and then changes the weights of the two species;
aggregates and bright outliers distort the curve; photobleaching and saturation of the dye at a high laser power shorten the
apparent diffusion time; the sample can adsorb to the chamber surface (passivated chambers, a carrier protein or a detergent
prevent it); the dye can change the binding; and in FCCS the spectral cross-talk between the channels has to be corrected. The
form keeps exactly those things.

Record fields
-------------
version, experiment_type ('fcs'), experiment_ref, source_ref, assertion_ref
preparations   titrant_preparation_ref (the partner added in a series), fixed_partner_preparation_ref (the labelled partner held
               at a low constant concentration), dataset_ref: each a string or None (unknown). The converter hands them to the
               merger as its dependence keys (titrant as the analyte key, the labelled partner as the other partner; a titration
               in solution has no surface).
quantities     kd, kd_spread, labelled_concentration, free_diffusion_time, free_diffusion_time_spread, bound_diffusion_time,
               free_diffusion_coefficient, bound_diffusion_coefficient, fraction_bound_maximum, particle_number, detection_volume,
               structure_parameter, mass_ratio, brightness,
               laser_power, measurement_time, measurement_repeat_count, titration_point_count, incubation_time, temperature,
               replicate_count: one operand each.
               Units: kd/kd_spread/labelled_concentration pM, nM, uM or mM; free_diffusion_time and bound_diffusion_time us or
               ms (the diffusion time of the free labelled partner and of its fully bound complex); free_diffusion_time_spread us or
               ms (the stated scatter, standard deviation or error, of the free diffusion time over repeated measurements: the
               paper's own noise of the diffusion time, against which the size of the diffusion change is judged); detection_volume
               fL (the effective confocal detection volume, with which a labelled concentration is turned into a particle number); free_diffusion_coefficient and
               bound_diffusion_coefficient 'um2/s'; fraction_bound_maximum 'percent' (the largest fraction of the labelled partner
               that is bound, at the highest titrant concentration); particle_number 'molecules' (the average number of
               fluorescent molecules in the confocal volume, N, the inverse of the correlation amplitude); structure_parameter
               'ratio' (the axial over the lateral radius of the confocal volume); mass_ratio 'ratio' (the molecular mass of the
               complex over that of the free labelled partner, as the source gives it); brightness 'kHz' (the counts per second
               per molecule in kilohertz, the molecular brightness); laser_power nW, uW or mW (the laser power at the sample);
               measurement_time s or min (the duration of one measurement of one sample); measurement_repeat_count,
               titration_point_count and replicate_count 'count'; incubation_time s, min or h; temperature C or K.
concentration_series
               operand whose 'value' is a list of titrant concentrations (unit pM, nM, uM or mM), or None when not given.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread is.
fit_model      '1:1' (a one-site model), 'hill', 'quadratic' (tight binding), 'other' or None. The model of the binding curve.
diffusion_model
               'one_component' (a single diffusing species, giving an apparent time), 'two_component' (the free and the bound
               species with separate times and fractions), 'anomalous' (a diffusion with an anomaly exponent), 'other' or None.
               The model the correlation curves were fitted with.
readout_signal 'diffusion_time' (the diffusion time or the fraction bound from it is the binding signal), 'diffusion_coefficient'
               (the diffusion coefficient is), 'brightness' (the change of the molecular brightness is), 'cross_correlation'
               (the amplitude of the dual-colour cross-correlation, FCCS, is) or None.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a
               controlled answer only.
               binding_detected is the experiment's stated yes/no result (the passage says the two partners bound, or says
               they did not); no criterion reads it. It lets a result that is stated without a constant count (owner, 2026-11-22).
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.
choice_support name -> 'direct', 'implied', 'about_something_else' or None, for each of the four choice fields (CHOICE_FIELDS): how well the
               quote of that stated choice supports it; None when the choice is not stated.

Support (how well a stated field's quote supports it)
-----------------------------------------------------
Every stated field carries a fixed-vocabulary fact 'support' (SUPPORTS: 'direct', 'implied', 'about_something_else'): in a quantity operand
(and in the concentration series) and in a fact entry, as a 'support' key beside source_refs; for a choice field in choice_support. An
unavailable operand, an 'unknown' fact and a choice that is not stated carry None. The extraction always sets it from the model's answer.
The constructors ``point`` and ``fact`` below default it to 'direct' ONLY so that tests that build a record by hand (not through the
extraction) need not name it; ``unavailable`` and an 'unknown' fact are always None. The grader keeps the support and does not judge it;
the converter (the sheet side) turns it into a degree.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence import literature_spr_record
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS

VERSION = 'a105_fcs_record'
EXPERIMENT_TYPE = 'fcs'
QUANTITIES = ('kd', 'kd_spread', 'labelled_concentration', 'free_diffusion_time', 'free_diffusion_time_spread', 'bound_diffusion_time', 'free_diffusion_coefficient', 'bound_diffusion_coefficient', 'fraction_bound_maximum', 'particle_number', 'detection_volume', 'structure_parameter', 'mass_ratio', 'brightness', 'laser_power', 'measurement_time', 'measurement_repeat_count', 'titration_point_count', 'incubation_time', 'temperature', 'replicate_count')
PREPARATION_KEYS = ('titrant_preparation_ref', 'fixed_partner_preparation_ref', 'dataset_ref')
CHOICE_FIELDS = ('spread_kind', 'fit_model', 'diffusion_model', 'readout_signal')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('1:1', 'hill', 'quadratic', 'other')
DIFFUSION_MODELS = ('one_component', 'two_component', 'anomalous', 'other')
READOUT_SIGNALS = ('diffusion_time', 'diffusion_coefficient', 'brightness', 'cross_correlation')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'confocal_volume_calibrated': YES_NO, 'triplet_state_modelled': YES_NO, 'free_diffusion_time_fixed': YES_NO, 'brightness_change_accounted': YES_NO, 'crosstalk_corrected': YES_NO, 'background_corrected': YES_NO, 'aggregates_checked': YES_NO, 'photobleaching_or_saturation_checked': YES_NO, 'surface_adsorption_prevented': YES_NO, 'labelling_does_not_alter_binding': YES_NO, 'nonbinding_control_done': YES_NO, 'labelled_partner_at_or_below_kd': YES_NO, 'tight_binding_considered': YES_NO, 'equilibrium_reached': YES_NO, 'independent_titrations': YES_NO, 'single_estimate_method': YES_NO, 'binding_detected': YES_NO}


def _checked(support):
    if support not in SUPPORTS:
        raise ValueError('support must be one of ' + ', '.join(SUPPORTS) + ': ' + repr(support))
    return support


def point(value, unit, key, refs, native_component=None, support='direct'):
    """A stated operand with its support (default 'direct': see the module docstring)."""
    return {**literature_spr_record.point(value, unit, key, refs, native_component), 'support': _checked(support)}


def unavailable(unit, key, reason):
    return {**literature_spr_record.unavailable(unit, key, reason), 'support': None}


def fact(answer, refs=(), support='direct'):
    """A fact entry: a stated answer carries its support (default 'direct'); 'unknown' carries None (and no support may be given for it)."""
    if answer == 'unknown':
        if support not in ('direct', None):
            raise ValueError('an unknown fact carries no support')
        return {**literature_spr_record.fact(answer, refs), 'support': None}
    return {**literature_spr_record.fact(answer, refs), 'support': _checked(support)}


CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'labelled_concentration': CONCENTRATION_UNITS, 'free_diffusion_time': ('us', 'ms'), 'free_diffusion_time_spread': ('us', 'ms'), 'bound_diffusion_time': ('us', 'ms'), 'free_diffusion_coefficient': ('um2/s',), 'bound_diffusion_coefficient': ('um2/s',), 'fraction_bound_maximum': ('percent',), 'particle_number': ('molecules',), 'detection_volume': ('fL',), 'structure_parameter': ('ratio',), 'mass_ratio': ('ratio',), 'brightness': ('kHz',), 'laser_power': ('nW', 'uW', 'mW'), 'measurement_time': ('s', 'min'), 'measurement_repeat_count': ('count',), 'titration_point_count': ('count',), 'incubation_time': ('s', 'min', 'h'), 'temperature': ('C', 'K'), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
