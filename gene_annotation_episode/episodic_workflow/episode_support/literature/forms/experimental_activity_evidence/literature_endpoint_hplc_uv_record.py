"""The extracted record of ONE fixed-time enzyme reaction read by HPLC (type 'endpoint_hplc_uv', class endpoint_conversion). DRAFT of 2026-11-22, owner to correct.

The assay: one enzyme, one substrate, a reaction run for a stated time and then stopped (a quench by acid, solvent or heat, or a filtration that
removes the enzyme); the substrate and the product are separated on a column and read with an optical detector (UV, diode array) or a refractive-index
detector, and their amounts come from peak areas against a standard curve of an authentic standard. The result is how much of the substrate was
converted, or how much product there was, at that one time: an end point, not a rate (a rate is the activity_rate class's) and not the time the reaction
took to finish (that is the endpoint_time_course_completion type). HPLC with mass-spectrometric detection is endpoint_ms_quant; a colour reagent is
endpoint_colorimetric; NMR integrals are endpoint_nmr.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status,
reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable',
value None and a reason; it is never 0 and never omitted. A stated number is above 0 (a conversion of nothing is the fact
conversion_detected_above_control answered no, never the number 0).

Record fields
-------------
version, experiment_type ('endpoint_hplc_uv'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as
               decided for the class (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no immobilized enzyme and no
               electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the extraction leaves
               all four None.
quantities     The three effect quantities of this type, each with the spread the passage gives for it:
                 conversion_percent and conversion_spread          percent   the share of the initial substrate converted at the end point, as stated
                 net_conversion_percent and net_conversion_spread  percent   the same share minus the paper's own control, ONLY when the passage states it
                 product_amount and product_amount_spread          nM, uM or mM   the product concentration at the end point
               the paper's own control beside the test:
                 control_conversion_percent                        percent   the share converted in the no-enzyme or inactive-enzyme control
               and the conditions that decide how far an HPLC result can be trusted:
                 substrate_initial        nM, uM or mM   the substrate concentration at the start (the denominator of a share)
                 endpoint_time            s, min or h    the time at which the reaction was stopped and sampled
                 enzyme_concentration     nM, uM or mg/mL   the enzyme in the reaction (recorded; no criterion rests on it)
                 standard_curve_low and standard_curve_high   nM, uM or mM   the lowest and the highest concentration of the standard curve
                 standard_curve_points    count          the number of different concentrations of the standard curve
                 detection_limit          nM, uM or mM   the detection or quantification limit of the method
                 replicate_count          count          the number of replicate (independent) reactions
                 injection_replicates     count          the number of repeated injections of one reaction sample (recorded; they are not replicates)
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
detector       'uv', 'diode_array', 'refractive_index', 'other' or None: how the peaks were read. Recorded for the reviewer; no criterion rests on a choice
               (a choice holds no span in the merged record).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, detector), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact
about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or
'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or
'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default
it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_endpoint_hplc_uv_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'endpoint_hplc_uv'
QUANTITIES = ('conversion_percent', 'conversion_spread', 'net_conversion_percent', 'net_conversion_spread', 'control_conversion_percent', 'product_amount',
              'product_amount_spread', 'substrate_initial', 'endpoint_time', 'enzyme_concentration', 'standard_curve_low', 'standard_curve_high',
              'standard_curve_points', 'detection_limit', 'replicate_count', 'injection_replicates')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
DETECTORS = ('uv', 'diode_array', 'refractive_index', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control_done': YES_NO, 'inactive_enzyme_control_done': YES_NO, 'zero_time_sample_done': YES_NO, 'enzyme_dependence_shown': YES_NO,
         'authentic_standard_used': YES_NO, 'peak_confirmed_by_second_method': YES_NO, 'substrate_loss_matches_product_gain': YES_NO,
         'reaction_stopped_before_analysis': YES_NO, 'same_time_for_compared_arms': YES_NO, 'initial_substrate_determined': YES_NO,
         'both_species_quantified': YES_NO, 'calibration_in_matrix': YES_NO, 'internal_standard_used': YES_NO, 'independent_replicates': YES_NO,
         'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'conversion_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'conversion_percent': ('percent',), 'conversion_spread': ('percent',), 'net_conversion_percent': ('percent',), 'net_conversion_spread': ('percent',),
         'control_conversion_percent': ('percent',), 'product_amount': CONCENTRATION_UNITS, 'product_amount_spread': CONCENTRATION_UNITS,
         'substrate_initial': CONCENTRATION_UNITS, 'endpoint_time': ('s', 'min', 'h'), 'enzyme_concentration': ('nM', 'uM', 'mg/mL'),
         'standard_curve_low': CONCENTRATION_UNITS, 'standard_curve_high': CONCENTRATION_UNITS, 'standard_curve_points': ('count',),
         'detection_limit': CONCENTRATION_UNITS, 'replicate_count': ('count',), 'injection_replicates': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
