"""The extracted record of ONE intrinsic tryptophan (and tyrosine) fluorescence quenching / enhancement binding titration.

What a leaf extraction holds for one steady-state fluorescence titration of a protein with a ligand in which the binding
is read from the change of the protein's own (intrinsic) fluorescence, mostly of its tryptophan residues: the protein is
held at a fixed, constant concentration, the ligand (the titrant) is added in a series, the fluorescence emission is
recorded at each step, and the KD is fitted from the fractional change of the fluorescence (a quenching, or an
enhancement) as it saturates with the ligand concentration. One experiment, or replicate titrations reported as one
result, in the same operand shape as the SPR, ITC, BLI, GCI, FP, FRET and MST records and the existing A105 assay grading
inputs (value, unit, status, reason, measurement_keys, source_refs, origin, native_component). A value the source did not
give is an operand with status 'unavailable', value None and a reason; it is never 0 and never omitted. The plain
constructors point, unavailable and fact are the SPR record module's; they are shared because they only build operands.

Intrinsic fluorescence quenching differs from the other methods in what is measured and what can go wrong: the readout is
indirect (nothing is detected of the complex itself; a tryptophan near enough to the binding site, or to a part that moves
on binding, must change its emission, so a ligand that binds without changing the environment of a tryptophan gives no
signal); the excitation wavelength decides which residues are read (295 nm excites tryptophan almost alone, 280 nm
excites tyrosine as well); it is very sensitive to the inner-filter effect (a ligand that absorbs at the excitation or at
the emission wavelength lowers the measured fluorescence with no binding at all, and is corrected with an absorbance-based
formula or with a titration of free tryptophan or N-acetyl-tryptophanamide, NATA); the ligand may itself fluoresce; the
added ligand dilutes the protein; the buffer has its own signal; the tryptophans can be photobleached; and a quenching can
be static (a complex is formed, which a KD describes) or dynamic (collisional, described by the Stern-Volmer constant Ksv,
which is a quenching efficiency and is NOT a dissociation constant). The form keeps exactly those things.

Record fields
-------------
version, experiment_type ('trp_quenching'), experiment_ref, source_ref, assertion_ref
preparations   titrant_preparation_ref (the ligand added in a series), fixed_partner_preparation_ref (the protein whose
               fluorescence is read, held at a constant concentration), dataset_ref: each a string or None (unknown). The
               converter hands them to the merger as its dependence keys (titrant as the analyte key, the protein as the
               other partner; a titration in solution has no surface).
quantities     kd, kd_spread, ksv, protein_concentration, excitation_wavelength, emission_wavelength, emission_shift,
               fluorescence_change, ligand_absorbance, added_volume_fraction, titration_point_count, concentration_lowest,
               concentration_highest, incubation_time, temperature, replicate_count: one operand each.
               Units: kd/kd_spread/protein_concentration pM, nM, uM or mM; ksv 'M^-1' (the Stern-Volmer quenching constant,
               kept apart from the KD); excitation_wavelength, emission_wavelength and emission_shift 'nm' (the emission
               shift as a positive number, its direction is emission_shift_direction); fluorescence_change 'percent' (the
               change of the fluorescence between the free protein and the saturated complex, as a positive number, its
               direction is change_direction); ligand_absorbance 'AU' (the absorbance of the ligand, at the highest
               concentration used, at the excitation or at the emission wavelength: the largest the passage gives);
               concentration_lowest and concentration_highest pM, nM, uM or mM (the lowest and the highest ligand concentration of
               the series, for a passage that gives a range and not a list; a zero blank is not a lowest concentration);
               added_volume_fraction 'percent' (the total volume of ligand added, over the starting volume of the protein
               sample); titration_point_count and replicate_count 'count'; incubation_time s, min or h (the time allowed
               after each addition before the read); temperature C or K.
concentration_series
               operand whose 'value' is a list of titrant (ligand) concentrations (unit pM, nM, uM or mM), or None when not
               given.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None. What kd_spread is.
fit_model      '1:1' (a one-site hyperbola), 'hill', 'quadratic' (tight binding), 'stern_volmer' (the Stern-Volmer equation,
               which gives Ksv), 'other' or None.
change_direction
               'quenching' (the fluorescence decreases on binding), 'enhancement' (it increases) or None.
emission_shift_direction
               'blue' (the emission maximum moves to shorter wavelengths on binding), 'red' (to longer) or None.
facts          name -> {'answer', 'source_refs'}. Names and answer sets in FACTS below. No fact holds text: a
               controlled answer only.
choice_support name -> support of each plain choice field (the choice fields of the extraction: spread_kind, fit_model,
               change_direction, emission_shift_direction), None when the field is not stated.
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

VERSION = 'a105_trp_record_v1'
EXPERIMENT_TYPE = 'trp_quenching'
QUANTITIES = ('kd', 'kd_spread', 'ksv', 'protein_concentration', 'excitation_wavelength', 'emission_wavelength', 'emission_shift', 'fluorescence_change', 'ligand_absorbance', 'added_volume_fraction', 'titration_point_count', 'concentration_lowest', 'concentration_highest', 'incubation_time', 'temperature', 'replicate_count')
PREPARATION_KEYS = ('titrant_preparation_ref', 'fixed_partner_preparation_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FIT_MODELS = ('1:1', 'hill', 'quadratic', 'stern_volmer', 'other')
CHANGE_DIRECTIONS = ('quenching', 'enhancement')
SHIFT_DIRECTIONS = ('blue', 'red')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'inner_filter_corrected': YES_NO, 'ligand_absorbance_negligible': YES_NO, 'dilution_corrected': YES_NO, 'buffer_blank_subtracted': YES_NO, 'ligand_only_control_measured': YES_NO, 'nonbinding_control_done': YES_NO, 'trp_analogue_control_done': YES_NO, 'signal_localised_to_binding_site': YES_NO, 'signal_saturates': YES_NO, 'quenching_is_static': YES_NO, 'photobleaching_checked': YES_NO, 'protein_at_or_below_kd': YES_NO, 'tight_binding_considered': YES_NO, 'equilibrium_reached': YES_NO, 'independent_titrations': YES_NO, 'single_estimate_method': YES_NO}

CONCENTRATION_UNITS = ('pM', 'nM', 'uM', 'mM')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'kd': CONCENTRATION_UNITS, 'kd_spread': CONCENTRATION_UNITS, 'ksv': ('M^-1',), 'protein_concentration': CONCENTRATION_UNITS, 'excitation_wavelength': ('nm',), 'emission_wavelength': ('nm',), 'emission_shift': ('nm',), 'fluorescence_change': ('percent',), 'ligand_absorbance': ('AU',), 'added_volume_fraction': ('percent',), 'titration_point_count': ('count',), 'concentration_lowest': CONCENTRATION_UNITS, 'concentration_highest': CONCENTRATION_UNITS, 'incubation_time': ('s', 'min', 'h'), 'temperature': ('C', 'K'), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}
