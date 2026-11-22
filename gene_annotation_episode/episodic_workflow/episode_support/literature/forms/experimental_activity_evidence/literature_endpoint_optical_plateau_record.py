"""The extracted record of ONE reaction run to an optical plateau (type 'endpoint_optical_plateau', class endpoint_conversion). DRAFT 2026-11-22,
owner to correct.

The method: one enzyme and one substrate in a cuvette or a plate; the absorbance (or the fluorescence) of a chromophoric or fluorogenic substrate or
product is read until it stops changing, and the final change is turned into the share of the substrate converted, or into the product amount, with the
extinction coefficient or with a full-conversion reference (the same substrate amount converted completely, or a free-fluorophore standard). It is an end
point, not a rate: the initial slope of the same trace is spectro_direct or fluorogenic (activity_rate); the same reaction stopped at a fixed time and read
with a colour reagent is a different type.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and
a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('endpoint_optical_plateau'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as
               decided for the endpoint_conversion class (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no
               immobilized enzyme and no surface, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference,
               so the extraction leaves all four None.
quantities     The four effect quantities of the class this method can state, each with the spread the passage gives for it (the unit of the quantity):
                 conversion_percent and conversion_percent_spread                 percent or fraction   the share of the substrate converted at the plateau, as stated
                 net_conversion_percent and net_conversion_percent_spread         percent or fraction   the same minus the paper's own control, when the paper states that value itself
                 product_amount and product_amount_spread                         nM, uM or mM          the product (or the substrate used up) at the plateau
                 time_to_plateau and time_to_plateau_spread                       s, min or h           the time the signal took to reach its plateau (a point value, not a bound)
               the control beside the test value:
                 control_conversion                                               percent or fraction   the conversion the paper's no-enzyme or inactive-enzyme control shows
               and the numbers that decide how far the signal change can be trusted as a conversion:
                 substrate_initial        nM, uM or mM             the substrate concentration at the start: the denominator of the fraction
                 signal_change_total      AU or RFU                the final signal change of the test (absorbance units or relative fluorescence units)
                 signal_change_baseline   AU or RFU                the signal change of the no-enzyme baseline over the same time
                 signal_change_full       AU or RFU                the signal change of the full-conversion reference (complete conversion of the same substrate amount, or a free-fluorophore standard)
                 extinction_coefficient   M^-1 cm^-1 or mM^-1 cm^-1  the extinction coefficient used to turn an absorbance change into a concentration
                 path_length              cm or mm                 the optical path length
                 wavelength               nm                       the wavelength read (for fluorescence the emission wavelength)
                 absorbance_max           AU                       the highest absorbance reached in the measurement
                 replicate_count          count                    the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about
how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or
'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or
'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default
it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_endpoint_optical_plateau_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'endpoint_optical_plateau'
QUANTITIES = ('conversion_percent', 'conversion_percent_spread', 'net_conversion_percent', 'net_conversion_percent_spread', 'control_conversion',
              'product_amount', 'product_amount_spread', 'time_to_plateau', 'time_to_plateau_spread', 'substrate_initial',
              'signal_change_total', 'signal_change_baseline', 'signal_change_full', 'extinction_coefficient', 'path_length', 'wavelength',
              'absorbance_max', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control_done': YES_NO, 'inactive_enzyme_control_done': YES_NO, 'control_read_over_same_time': YES_NO,
         'full_conversion_reference_done': YES_NO, 'plateau_stable': YES_NO, 'signal_in_linear_range': YES_NO, 'inner_filter_checked': YES_NO,
         'enzyme_dependence_shown': YES_NO, 'initial_substrate_determined': YES_NO, 'product_identified_by_standard': YES_NO,
         'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'conversion_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
CONVERSION_UNITS = ('percent', 'fraction')
TIME_UNITS = ('s', 'min', 'h')
SIGNAL_UNITS = ('AU', 'RFU')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'conversion_percent': CONVERSION_UNITS, 'conversion_percent_spread': CONVERSION_UNITS, 'net_conversion_percent': CONVERSION_UNITS,
         'net_conversion_percent_spread': CONVERSION_UNITS, 'control_conversion': CONVERSION_UNITS,
         'product_amount': CONCENTRATION_UNITS, 'product_amount_spread': CONCENTRATION_UNITS, 'time_to_plateau': TIME_UNITS, 'time_to_plateau_spread': TIME_UNITS,
         'substrate_initial': CONCENTRATION_UNITS, 'signal_change_total': SIGNAL_UNITS, 'signal_change_baseline': SIGNAL_UNITS, 'signal_change_full': SIGNAL_UNITS,
         'extinction_coefficient': ('M^-1 cm^-1', 'mM^-1 cm^-1'), 'path_length': ('cm', 'mm'), 'wavelength': ('nm',), 'absorbance_max': ('AU',),
         'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
