"""The extracted record of ONE continuous direct spectrophotometric enzyme assay (type 'spectro_direct', class activity_rate).

The first experiment type of the activity_rate class (built 2026-11-21 by the SOP, steps 1 to 8); the other eighteen types of the class copy its
shape. The assay: one enzyme, one substrate, a chromophore that changes by itself during the reaction (NAD(P)H at 340 nm, a nitrophenol
at 405 nm, a coloured product or substrate), the absorbance read continuously in the cuvette or plate, the initial slope turned into a rate
with the extinction coefficient.

This is what a leaf extraction holds for one such assay, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('spectro_direct'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The
               class keys are used as decided 2026-11-21 (owner to confirm): the enzyme preparation is the analyte_preparation_ref;
               this type has no immobilized enzyme and no electrode, so immobilized_preparation_ref and surface_ref stay None.
               No passage states a preparation reference, so the extraction leaves all four None.
quantities     The four effect quantities of the class, each with the spread the passage gives for it (the unit of the quantity):
                 catalytic_efficiency (kcat/Km) and catalytic_efficiency_spread     M^-1 s^-1, mM^-1 s^-1 or uM^-1 s^-1
                 turnover (kcat) and turnover_spread                                s^-1 or min^-1
                 specific_activity and specific_activity_spread                     U/mg, umol/min/mg or nmol/min/mg
                 rate_over_control and rate_over_control_spread                     fold (the rate of the enzyme over the paper's own control)
               and the conditions that decide how far a rate can be trusted:
                 km                       nM, uM or mM                the Michaelis constant the passage reports
                 substrate_concentration  nM, uM or mM                the substrate concentration at which the reported rate was measured
                 enzyme_concentration     nM or uM                    the enzyme concentration of that measurement
                 substrate_consumed_percent  percent                  the share of the substrate consumed in the window the rate was taken from
                 wavelength               nm                          the wavelength the absorbance was read at
                 extinction_coefficient   M^-1 cm^-1 or mM^-1 cm^-1  the extinction coefficient used to turn absorbance into concentration
                 absorbance_max           AU                          the highest absorbance reached in the measurement
                 enzyme_mass              kDa                         the molar mass of the enzyme (a subunit) the passage gives
                 replicate_count          count                       the number of replicate experiments
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) of the saturation curve, or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_spectro_direct_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'spectro_direct'
QUANTITIES = ('catalytic_efficiency', 'catalytic_efficiency_spread', 'turnover', 'turnover_spread', 'specific_activity', 'specific_activity_spread',
              'rate_over_control', 'rate_over_control_spread', 'km', 'substrate_concentration', 'enzyme_concentration', 'substrate_consumed_percent',
              'wavelength', 'extinction_coefficient', 'absorbance_max', 'enzyme_mass', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'no_substrate_control': YES_NO, 'rate_proportional_to_enzyme': YES_NO,
         'linear_progress_curve': YES_NO, 'active_site_concentration_determined': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO,
         'product_identified': YES_NO, 'independent_replicates': YES_NO, 'activity_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
EFFICIENCY_UNITS = ('M^-1 s^-1', 'mM^-1 s^-1', 'uM^-1 s^-1')
TURNOVER_UNITS = ('s^-1', 'min^-1')
SPECIFIC_ACTIVITY_UNITS = ('U/mg', 'umol/min/mg', 'nmol/min/mg')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'catalytic_efficiency': EFFICIENCY_UNITS, 'catalytic_efficiency_spread': EFFICIENCY_UNITS, 'turnover': TURNOVER_UNITS, 'turnover_spread': TURNOVER_UNITS,
         'specific_activity': SPECIFIC_ACTIVITY_UNITS, 'specific_activity_spread': SPECIFIC_ACTIVITY_UNITS, 'rate_over_control': ('fold',), 'rate_over_control_spread': ('fold',),
         'km': CONCENTRATION_UNITS, 'substrate_concentration': CONCENTRATION_UNITS, 'enzyme_concentration': ('nM', 'uM'), 'substrate_consumed_percent': ('percent',),
         'wavelength': ('nm',), 'extinction_coefficient': ('M^-1 cm^-1', 'mM^-1 cm^-1'), 'absorbance_max': ('AU',), 'enzyme_mass': ('kDa',), 'replicate_count': ('count',),
         'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
