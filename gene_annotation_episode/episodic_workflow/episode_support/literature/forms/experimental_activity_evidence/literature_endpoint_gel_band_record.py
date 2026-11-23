"""The extracted record of ONE gel or TLC end-point conversion experiment (type 'endpoint_gel_band', class endpoint_conversion). DRAFT 2026-11-22, owner to correct.

The assay: an enzyme is mixed with its substrate and, at a stated time, the reaction is stopped and the mixture is separated on a gel or a thin-layer
plate (a denaturing polyacrylamide gel for nuclease, ligase, polymerase or kinase products and for a protease cleavage by SDS-PAGE, a native or mobility-shift
gel, a TLC plate for nucleotides, lipids or sugars). The substrate band and the product band are made visible by a stain, a fluorescent label or a
radiolabel and read by densitometry or phosphorimaging. The result is the share of the substrate that was converted at that one time (the product
band over the substrate plus the product bands of the same lane), a time point and not a rate, or only the sentence that a product band is present
or absent. Rates and kinetic constants belong to the activity_rate class; the share of the products among themselves at equilibrium belongs to product_distribution.
The same gel read for a slope over time is not this type.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable',
value None and a reason; it is never 0 and never omitted. A conversion of 0 percent is a stated value (no product band) and is allowed for the three
conversion quantities.

Record fields
-------------
version, experiment_type ('endpoint_gel_band'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys
               (decided for the class, owner to confirm): the enzyme preparation is the analyte_preparation_ref; no enzyme is immobilized and no
               surface is used, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the
               extraction leaves all four None.
quantities     conversion_percent and conversion_spread         percent or fraction   the share of the substrate converted at the end point, as the passage states it, and its spread
               net_conversion_percent and net_conversion_spread percent or fraction   the same share after the paper's own control was subtracted, only when the passage states the corrected value itself
               control_conversion                               percent or fraction   the share converted in the paper's own control lane (no enzyme, inactive enzyme), beside the test value
               endpoint_time                                    s, min or h           the time at which the reaction was stopped and the end point read
               replicate_count                                  count                 the number of independent experiments (separate gels)
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
fraction_defined_over
               'substrate_only', 'substrate_plus_product' or 'total_lane' or None: what the share is a fraction of (the substrate bands only, the substrate plus
               the product bands of the lane, or all bands of the lane). Kept in the record for the reviewer; no criterion rests on a choice (a choice holds no
               span in the merged record), so the same statement is also the fact fraction_from_same_lane_bands.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, fraction_defined_over), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

What a gel or TLC end point shows and what can go wrong is what the form keeps. The band of a product is identified by where it runs against a
size marker or an authentic standard (mobility), not by what it is; a contaminating enzyme of the preparation or a spontaneous breakdown of the
substrate puts the same band on the gel, so the no-enzyme lane and the inactive-enzyme (catalytic mutant, heat-killed, EDTA or inhibitor) lane decide
what the band means, and a zero-time lane shows that the substrate preparation did not already hold the product. Densitometry is linear only inside a range: a
saturated or over-exposed band reads low and a faint band reads against its background. The share is meaningful when it is taken from the bands of one lane
(loading differences cancel) and when the reaction was stopped before loading, so that the time of the lane is the time of the stop.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_endpoint_gel_band_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'endpoint_gel_band'
QUANTITIES = ('conversion_percent', 'conversion_spread', 'net_conversion_percent', 'net_conversion_spread', 'control_conversion', 'endpoint_time', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
FRACTION_DEFINED_OVER = ('substrate_only', 'substrate_plus_product', 'total_lane')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_lane_done': YES_NO, 'inactive_enzyme_lane_done': YES_NO, 'zero_time_lane_done': YES_NO, 'product_depends_on_active_enzyme': YES_NO,
         'band_identified_by_marker': YES_NO, 'signal_within_linear_range': YES_NO, 'fraction_from_same_lane_bands': YES_NO, 'reaction_stopped_before_loading': YES_NO,
         'same_time_for_compared_lanes': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'conversion_detected_above_control': YES_NO}
# The plain choice fields (recorded only; no criterion rests on one): name -> its vocabulary.
CHOICES = {'spread_kind': SPREAD_KINDS, 'fraction_defined_over': FRACTION_DEFINED_OVER}

CONVERSION_UNITS = ('percent', 'fraction')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'conversion_percent': CONVERSION_UNITS, 'conversion_spread': CONVERSION_UNITS, 'net_conversion_percent': CONVERSION_UNITS, 'net_conversion_spread': CONVERSION_UNITS,
         'control_conversion': CONVERSION_UNITS, 'endpoint_time': ('s', 'min', 'h'), 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
