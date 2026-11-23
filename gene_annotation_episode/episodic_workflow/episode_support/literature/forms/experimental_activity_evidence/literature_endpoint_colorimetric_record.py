"""The extracted record of ONE stopped colorimetric end-point experiment (type 'endpoint_colorimetric', class endpoint_conversion).

The experiment: one enzyme, one substrate, a reaction run for a set time and then STOPPED (by the colour reagent itself, an acid or heat), after which a
colour-forming reagent turns a product CLASS into a coloured compound read in a spectrophotometer or plate reader: malachite green with molybdate for
released phosphate, DNS or a bicinchoninic reagent for reducing ends, DTNB for a thiol, Nessler or Berthelot reagent for ammonia, a ferric hydroxamate,
a chromogenic product after the stop. The absorbance is turned into an amount of product with a PRODUCT STANDARD CURVE made in the reaction buffer. What the
experiment reports is ONE END POINT: the share of the substrate that was converted at the stated time, or the amount of product present then. It reports
no rate and no kinetic constant (a rate from a time course of the same assay is the activity_rate type stopped_colorimetric), and the colour names a product
class, not a separated product (a chromatogram of the same reaction is the type endpoint_hplc_uv). What the end point needs is blanks that catch the reagent
reacting with the substrate, the enzyme preparation or the buffer, a standard curve made in the reaction buffer that covers the amounts read, a stated
incubation time and stop, and a stated amount of substrate at the start for a share converted.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('endpoint_colorimetric'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as
               decided for the endpoint_conversion class (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no
               immobilized enzyme and no electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so
               the extraction leaves all four None.
quantities     The stated end point, each with the spread the passage gives for it:
                 conversion and conversion_spread                              percent or fraction  the share of the substrate converted at the end point, as stated
                 control_conversion                                           percent or fraction  the same share in the paper's own control (no enzyme, inactive enzyme, zero time)
                 net_conversion and net_conversion_spread                      percent or fraction  the share the paper itself gives after the control was taken away
                 product_concentration and product_concentration_spread       nM, uM or mM         the product (class) concentration in the reaction at the end point
                 product_amount                                               pmol, nmol or umol   the product (class) amount formed in the reaction at the end point
                 reaction_volume                                              uL or mL             the volume the product amount was formed in
               and what decides how far the end point can be trusted:
                 substrate_initial        nM, uM or mM            the substrate concentration at the start (the amount a share converted refers to)
                 endpoint_time            s, min or h             the time the reaction ran before it was stopped or read
                 product_read_on_curve    nM, uM, mM, pmol, nmol or umol   the largest product amount the standard curve gave for a test sample, in the standard curve's own terms
                 standard_curve_low       the same units          the lowest standard of the product standard curve
                 standard_curve_high      the same units          the highest standard of the product standard curve
                 standard_curve_points    count                   the number of standards (different amounts) of the standard curve
                 replicate_count          count                   the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
reagent_class  the class of the colour reagent (a plain choice for recording only; no criterion rests on it, because a choice carries no span after the leaf
               records are merged). The two choices are kept in the record for the reviewer.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, reagent_class), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about
how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else'
(the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an
unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is
only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_endpoint_colorimetric_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'endpoint_colorimetric'
QUANTITIES = ('conversion', 'conversion_spread', 'control_conversion', 'net_conversion', 'net_conversion_spread',
              'product_concentration', 'product_concentration_spread', 'product_amount', 'reaction_volume',
              'substrate_initial', 'endpoint_time', 'product_read_on_curve', 'standard_curve_low', 'standard_curve_high', 'standard_curve_points',
              'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
REAGENT_CLASSES = ('malachite_green_phosphate', 'reducing_sugar', 'thiol', 'hydroxamate', 'ammonia', 'chromogenic_product', 'other_colorimetric')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'no_substrate_control': YES_NO, 'zero_time_sample': YES_NO,
         'standard_curve_in_buffer': YES_NO, 'reagent_interference_checked': YES_NO, 'product_rises_with_enzyme': YES_NO,
         'product_identified_independently': YES_NO, 'reaction_stopped': YES_NO, 'same_time_for_compared_arms': YES_NO,
         'initial_substrate_determined': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO,
         'conversion_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
AMOUNT_UNITS = ('pmol', 'nmol', 'umol')
CONVERSION_UNITS = ('percent', 'fraction')
# The unit vocabulary of each quantity: the units a record may carry. A standard curve is stated either as concentrations or as amounts per tube or well.
UNITS = {'conversion': CONVERSION_UNITS, 'conversion_spread': CONVERSION_UNITS, 'control_conversion': CONVERSION_UNITS,
         'net_conversion': CONVERSION_UNITS, 'net_conversion_spread': CONVERSION_UNITS,
         'product_concentration': CONCENTRATION_UNITS, 'product_concentration_spread': CONCENTRATION_UNITS, 'product_amount': AMOUNT_UNITS,
         'reaction_volume': ('uL', 'mL'), 'substrate_initial': CONCENTRATION_UNITS, 'endpoint_time': ('s', 'min', 'h'),
         'product_read_on_curve': (*CONCENTRATION_UNITS, *AMOUNT_UNITS), 'standard_curve_low': (*CONCENTRATION_UNITS, *AMOUNT_UNITS),
         'standard_curve_high': (*CONCENTRATION_UNITS, *AMOUNT_UNITS), 'standard_curve_points': ('count',), 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
