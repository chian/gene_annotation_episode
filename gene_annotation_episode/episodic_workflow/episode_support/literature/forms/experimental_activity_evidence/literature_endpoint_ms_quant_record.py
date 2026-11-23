"""The extracted record of ONE fixed-time enzyme reaction whose product is quantified by mass spectrometry (type 'endpoint_ms_quant', class endpoint_conversion).

DRAFT of 2026-11-22 (owner to correct), built from the SOP (steps 1 to 5) on the shape of the spectro_direct record; the class core is the one of
docs/axis_restructure_20261117/A105_ENDPOINT_CONVERSION_INVENTORY.md (sections 2 and 3.2). The assay: one enzyme, one substrate, a reaction stopped
at a stated time (a quench: acid, an organic solvent, heat or a filter), the product measured by LC-MS, LC-MS/MS, GC-MS or direct-infusion mass
spectrometry against an internal standard and a calibration made with an authentic standard, ideally in the matrix of the reaction. The result is
how much of the substrate was converted, how much product there was, or how long completion took, at that one end point: not a rate.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('endpoint_ms_quant'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are
               used as decided for the class (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no
               immobilized enzyme and no surface, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation
               reference, so the extraction leaves all four None.
quantities     The five effect quantities of the class (QUANTITY_KINDS['endpoint_conversion']), each with the spread the passage gives for it:
                 conversion_fraction and conversion_fraction_spread        percent or fraction: the share of the substrate converted, as stated
                 conversion_difference and conversion_difference_spread    percent or fraction: the share converted MINUS the paper's own control, as stated
                 completion_time_ratio and completion_time_ratio_spread    fold: the reference completion time over the test completion time, as stated
                 completion_time and completion_time_spread                s, min or h: the time to reach the stated completion or equilibrium
                 endpoint_amount and endpoint_amount_spread                nM, uM, mM, or pmol, nmol, umol (an amount needs reaction_volume to become a concentration)
               and what decides how far the result can be trusted:
                 control_conversion         percent or fraction   the share converted in the paper's own control (no enzyme, inactive enzyme, zero time)
                 substrate_initial          nM, uM, mM, pmol, nmol, umol   the initial substrate the share is taken from
                 reaction_volume            uL or mL              the volume of the reaction, which turns an amount into a concentration
                 endpoint_time              s, min or h           the time at which the end point was read
                 calibration_low, calibration_high   nM, uM, mM   the lowest and the highest concentration of the calibration standards
                 calibration_points         count                 the number of concentration levels of the calibration curve
                 quantification_limit       nM, uM, mM            the lowest concentration the passage says is quantified (LLOQ, LOQ)
                 detection_limit            nM, uM, mM            the lowest concentration the passage says is detected (LOD)
                 replicate_count            count                 the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation' or 'confidence_interval': what the spreads are (a plain choice, recorded, never read by a criterion).
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

VERSION = 'a105_endpoint_ms_quant_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'endpoint_ms_quant'
QUANTITIES = ('conversion_fraction', 'conversion_fraction_spread', 'conversion_difference', 'conversion_difference_spread', 'completion_time_ratio', 'completion_time_ratio_spread',
              'completion_time', 'completion_time_spread', 'endpoint_amount', 'endpoint_amount_spread', 'control_conversion', 'substrate_initial', 'reaction_volume', 'endpoint_time',
              'calibration_low', 'calibration_high', 'calibration_points', 'quantification_limit', 'detection_limit', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control_done': YES_NO, 'inactive_enzyme_control_done': YES_NO, 'zero_time_sample_done': YES_NO, 'enzyme_dependence_shown': YES_NO,
         'internal_standard_used': YES_NO, 'matrix_matched_calibration': YES_NO, 'authentic_standard_used': YES_NO, 'ms_ms_confirmation': YES_NO, 'accurate_mass_match': YES_NO,
         'amounts_within_calibration_range': YES_NO, 'reaction_stopped_before_analysis': YES_NO, 'same_time_for_compared_arms': YES_NO, 'initial_substrate_determined': YES_NO,
         'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'conversion_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
AMOUNT_UNITS = ('pmol', 'nmol', 'umol')
CONVERSION_UNITS = ('percent', 'fraction')
TIME_UNITS = ('s', 'min', 'h')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'conversion_fraction': CONVERSION_UNITS, 'conversion_fraction_spread': CONVERSION_UNITS, 'conversion_difference': CONVERSION_UNITS, 'conversion_difference_spread': CONVERSION_UNITS,
         'completion_time_ratio': ('fold',), 'completion_time_ratio_spread': ('fold',), 'completion_time': TIME_UNITS, 'completion_time_spread': TIME_UNITS,
         'endpoint_amount': (*CONCENTRATION_UNITS, *AMOUNT_UNITS), 'endpoint_amount_spread': (*CONCENTRATION_UNITS, *AMOUNT_UNITS), 'control_conversion': CONVERSION_UNITS,
         'substrate_initial': (*CONCENTRATION_UNITS, *AMOUNT_UNITS), 'reaction_volume': ('uL', 'mL'), 'endpoint_time': TIME_UNITS,
         'calibration_low': CONCENTRATION_UNITS, 'calibration_high': CONCENTRATION_UNITS, 'calibration_points': ('count',), 'quantification_limit': CONCENTRATION_UNITS,
         'detection_limit': CONCENTRATION_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
