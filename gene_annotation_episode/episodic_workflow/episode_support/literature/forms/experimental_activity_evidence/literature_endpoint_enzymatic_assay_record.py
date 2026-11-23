"""The extracted record of ONE end-point determination with a second enzyme (type 'endpoint_enzymatic_assay', class endpoint_conversion).

DRAFT (2026-11-22), owner to correct. The method: a first enzyme acts on its substrate for a stated time and the reaction is stopped; the
substrate that is left or the product that was formed is then measured at the end by a SECOND, specific enzyme (formate by formate
dehydrogenase, glucose by glucose oxidase with peroxidase, ammonia by glutamate dehydrogenase, ethanol, lactate), read from a reporter
(NAD(P)H at 340 nm, a dye) against a standard series of the same analyte run through the same second-enzyme assay. It reports one time point
or a yield: a share of the substrate converted, or an amount of product. Rates and kinetic constants belong to activity_rate.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('endpoint_enzymatic_assay'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The first
               enzyme's preparation is the analyte_preparation_ref; nothing here is immobilized and there is no surface, so
               immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the extraction
               leaves all four None.
quantities     The effect quantities of the class that this method states, each with the spread the passage gives for it:
                 conversion_percent and conversion_percent_spread              percent or fraction  the share of the substrate converted at the end point
                 net_conversion_percent and net_conversion_percent_spread      percent or fraction  the same after the paper's own control is subtracted
                 product_amount and product_amount_spread                      nM, uM, mM, pmol, nmol or umol  the product formed
               and what decides how far they can be trusted:
                 reaction_volume          uL or mL                  the volume of the first enzyme's reaction (needed to turn a product amount in mol into a concentration)
                 substrate_initial        nM, uM or mM              the substrate concentration at the start (the denominator of the share)
                 endpoint_time            s, min or h               the time at which the first reaction was stopped or read
                 second_enzyme_incubation s, min or h               how long the sample was incubated with the second enzyme before the signal was read
                 standard_series_low and standard_series_high       the lowest and highest standard of the analyte (nM, uM, mM, pmol, nmol, umol)
                 standard_series_points   count                     the number of different standards
                 standard_curve_r_squared dimensionless             R squared of the standard curve
                 read_amount              nM, uM, mM, pmol, nmol or umol  the analyte as it was read against the standard series (after any dilution)
                 detection_limit          nM, uM or mM              the smallest analyte the assay tells from the blank
                 replicate_count          count                     the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are (a plain choice, recorded only).
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

VERSION = 'a105_endpoint_enzymatic_assay_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'endpoint_enzymatic_assay'
QUANTITIES = ('conversion_percent', 'conversion_percent_spread', 'net_conversion_percent', 'net_conversion_percent_spread', 'product_amount', 'product_amount_spread',
              'reaction_volume', 'substrate_initial', 'endpoint_time', 'second_enzyme_incubation', 'standard_series_low', 'standard_series_high', 'standard_series_points',
              'standard_curve_r_squared', 'read_amount', 'detection_limit', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'zero_time_sample': YES_NO, 'reaction_stopped_before_analysis': YES_NO,
         'same_time_for_compared_arms': YES_NO, 'standard_series_through_second_enzyme': YES_NO, 'read_amount_within_standard_series': YES_NO,
         'matrix_matched_standards': YES_NO, 'spike_recovery_done': YES_NO, 'second_enzyme_specificity_checked': YES_NO, 'reporter_conversion_complete': YES_NO,
         'initial_substrate_determined': YES_NO, 'product_confirmed_independently': YES_NO, 'substrate_loss_matches_product_gain': YES_NO,
         'enzyme_dependence_shown': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO,
         'conversion_detected_above_control': YES_NO}

CONVERSION_UNITS = ('percent', 'fraction')
CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
AMOUNT_UNITS = ('pmol', 'nmol', 'umol')
CONCENTRATION_OR_AMOUNT_UNITS = (*CONCENTRATION_UNITS, *AMOUNT_UNITS)
TIME_UNITS = ('s', 'min', 'h')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'conversion_percent': CONVERSION_UNITS, 'conversion_percent_spread': CONVERSION_UNITS, 'net_conversion_percent': CONVERSION_UNITS, 'net_conversion_percent_spread': CONVERSION_UNITS,
         'product_amount': CONCENTRATION_OR_AMOUNT_UNITS, 'product_amount_spread': CONCENTRATION_OR_AMOUNT_UNITS, 'reaction_volume': ('uL', 'mL'),
         'substrate_initial': CONCENTRATION_UNITS, 'endpoint_time': TIME_UNITS, 'second_enzyme_incubation': TIME_UNITS,
         'standard_series_low': CONCENTRATION_OR_AMOUNT_UNITS, 'standard_series_high': CONCENTRATION_OR_AMOUNT_UNITS, 'standard_series_points': ('count',),
         'standard_curve_r_squared': ('dimensionless',), 'read_amount': CONCENTRATION_OR_AMOUNT_UNITS, 'detection_limit': CONCENTRATION_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
