"""The extracted record of ONE optical equilibrium measurement of a reaction mixture (type 'distribution_optical_equilibrium', class product_distribution).

First DRAFT (2026-11-22, owner to confirm), built by the A105 SOP (steps 1 to 3 and 5) on the structure of the first type built outside the binding
class, spectro_direct, and of the class's first type, distribution_nmr. The measurement: an enzyme reaction (or its reverse) is left to run in a cuvette or
plate until the absorbance (or the fluorescence) of the mixture stops changing; at that plateau the mixture is at equilibrium, and because the species
have their own spectra (NADH at 340 nm is the classic case, or a chromophoric substrate or product) the plateau signal and the spectrum of each pure
species give the composition: the share of one species in the mixture, or the ratio of the two sides. Nothing is separated; the species are told apart
by their spectra only. What makes the composition an equilibrium is shown by the plateau itself (no change any more) and above all by reaching the same
composition from both sides (from the substrate and from the product) or from several initial concentrations.

This is what a leaf extraction holds for one such measurement, in the operand shape the existing A105 assay grading inputs use (value, unit, status,
reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable',
value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('distribution_optical_equilibrium'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as
               decided for the product_distribution class (owner to confirm): the enzyme preparation is the analyte_preparation_ref; no type of this
               class has an immobilized enzyme, a surface or an electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a
               preparation reference, so the extraction leaves all four None.
quantities     The two effect quantities of this method, each with the spread the passage gives for it (the unit of the quantity). ONE record states the
               composition as seen from ONE species: the species the identity block names as the partner (the claimed side). The other species of the
               mixture are the same experiment seen from the other side. An optical plateau gives an equilibrium composition only, so the two product-share
               quantities of the class (product_fraction and product_fraction_ratio) are not part of this record.
                 equilibrium_fraction (and _spread)   fraction or percent   the share of the partner species in the mixture at equilibrium
                 equilibrium_ratio (and _spread)      dimensionless         the ratio of the partner species to the other side at equilibrium
                                                                            (an equilibrium constant with a unit has no place in the class: it stays unavailable)
               and what decides how far the composition can be trusted:
                 wavelength            nm        the wavelength the signal was read at
                 extinction_coefficient M^-1 cm^-1 or mM^-1 cm^-1   the extinction coefficient used to turn the plateau absorbance into a concentration
                 absorbance_max        AU        the highest absorbance reached in the measurement (an absorbance reading only)
                 plateau_change_percent percent   how much the signal still changed over the plateau window the passage states (the greatest change stated)
                 replicate_count       count     the number of independent experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval', 'range' or None: what the spreads are.
readout        'absorbance', 'fluorescence' or None: what was read (recorded, no criterion rests on it).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, readout), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact
about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or
'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or
'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default
it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_distribution_optical_equilibrium_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'distribution_optical_equilibrium'
QUANTITIES = ('equilibrium_fraction', 'equilibrium_fraction_spread', 'equilibrium_ratio', 'equilibrium_ratio_spread',
              'wavelength', 'extinction_coefficient', 'absorbance_max', 'plateau_change_percent', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval', 'range')
READOUTS = ('absorbance', 'fluorescence')
# The plain choice fields of the record: name -> the vocabulary of its answers. A choice carries no span after the merge, so no criterion rests on one.
CHOICES = {'spread_kind': SPREAD_KINDS, 'readout': READOUTS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'pure_species_spectra_measured': YES_NO, 'all_absorbing_species_accounted': YES_NO, 'constant_refers_to_one_step': YES_NO,
         'no_enzyme_control_done': YES_NO, 'inactive_enzyme_control_done': YES_NO, 'plateau_stable': YES_NO, 'approached_from_both_sides': YES_NO,
         'same_value_at_several_initial_concentrations': YES_NO, 'independent_replicates': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO,
         'claimed_product_detected': YES_NO}

FRACTION_UNITS = ('fraction', 'percent')
RATIO_UNITS = ('dimensionless',)
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'equilibrium_fraction': FRACTION_UNITS, 'equilibrium_fraction_spread': FRACTION_UNITS, 'equilibrium_ratio': RATIO_UNITS, 'equilibrium_ratio_spread': RATIO_UNITS,
         'wavelength': ('nm',), 'extinction_coefficient': ('M^-1 cm^-1', 'mM^-1 cm^-1'), 'absorbance_max': ('AU',), 'plateau_change_percent': ('percent',),
         'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
