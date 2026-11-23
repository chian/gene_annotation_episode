"""The extracted record of ONE NMR end-point conversion experiment (type 'endpoint_nmr', class endpoint_conversion).

DRAFT (built 2026-11-22 by the SOP, steps 1 to 3 and 5, from the structure of the spectro_direct template; owner to correct). The experiment: one enzyme
converts one substrate in a tube or a vial; a spectrum (1H, 13C, 31P, 19F ...) is recorded at a stated time, or when the reaction is complete, and the integrals of an
assigned substrate signal and an assigned product signal give the share of the substrate converted (product over substrate plus product), or the amount of product
against an internal standard. The result is ONE time point or a yield, never a rate (a rate from a series of spectra is the activity_rate type nmr_timecourse). A
time to completion belongs to the type that samples the reaction over time and is not a field here.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('endpoint_nmr'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as decided for the
               endpoint_conversion class (owner to confirm): the enzyme preparation is the analyte_preparation_ref; no type of the class immobilises the enzyme or uses a
               surface, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the extraction leaves all four None.
quantities     Twelve operands, each with the unit of its own vocabulary (UNITS):
                 conversion               percent or fraction   the share of the substrate converted at the end point, from the integrals, as the passage states it
                 conversion_spread        percent or fraction   its stated spread (a number after a plus-minus sign, a standard error or deviation)
                 control_conversion       percent or fraction   the conversion of the paper's own control (no enzyme, inactive enzyme) read at the same time
                 net_conversion           percent or fraction   the control-corrected conversion, when the passage itself states that corrected value
                 product_concentration    uM or mM              the product amount at the end point, from the integrals against an internal standard
                 endpoint_time            s, min or h           the time at which the spectrum was read (or the reaction was stopped)
                 acquisition_duration     s, min or h           how long the spectrum took to record (the time the reaction runs during the read when it is not stopped)
                 relaxation_delay         ms or s               the relaxation (recycle) delay between scans
                 longest_t1               ms or s               the longest spin-lattice relaxation time T1 of the integrated signals, when the passage states it
                 signal_to_noise          dimensionless         the signal-to-noise ratio of the signal the conversion rests on
                 detection_limit          percent or fraction   the smallest conversion the spectrum could have shown, for a result stated as not detected
                 replicate_count          count                 the number of replicate reactions
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what conversion_spread is. A choice, kept for the converter's variance.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below. Sixteen yes/no facts; no fact holds text.
choice_support name -> support of each plain choice field (spread_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

No criterion rests on the choice spread_kind (a choice holds no span in the merged record): it only decides how the converter turns the spread into a variance.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how
well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the
quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice
carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by
tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_endpoint_nmr_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'endpoint_nmr'
QUANTITIES = ('conversion', 'conversion_spread', 'control_conversion', 'net_conversion', 'product_concentration', 'endpoint_time', 'acquisition_duration',
              'relaxation_delay', 'longest_t1', 'signal_to_noise', 'detection_limit', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'enzyme_dependence_shown': YES_NO, 'product_signal_assigned': YES_NO,
         'substrate_loss_matches_product_gain': YES_NO, 'quantitative_acquisition': YES_NO, 'signals_resolved': YES_NO, 'reaction_stopped_before_analysis': YES_NO,
         'same_time_for_compared_arms': YES_NO, 'initial_substrate_determined': YES_NO, 'both_species_integrated': YES_NO, 'internal_standard_used': YES_NO,
         'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'conversion_detected_above_control': YES_NO}

CONVERSION_UNITS = ('percent', 'fraction')
TIME_UNITS = ('s', 'min', 'h')
RELAXATION_UNITS = ('ms', 's')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'conversion': CONVERSION_UNITS, 'conversion_spread': CONVERSION_UNITS, 'control_conversion': CONVERSION_UNITS, 'net_conversion': CONVERSION_UNITS,
         'product_concentration': ('uM', 'mM'), 'endpoint_time': TIME_UNITS, 'acquisition_duration': TIME_UNITS, 'relaxation_delay': RELAXATION_UNITS,
         'longest_t1': RELAXATION_UNITS, 'signal_to_noise': ('dimensionless',), 'detection_limit': CONVERSION_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
