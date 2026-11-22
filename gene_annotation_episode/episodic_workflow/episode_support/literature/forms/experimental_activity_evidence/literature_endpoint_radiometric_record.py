"""The extracted record of ONE radiometric end-point conversion experiment (type 'endpoint_radiometric', class endpoint_conversion).

A type of the endpoint_conversion class (DRAFT built 2026-11-22 by the SOP, copying the shape of spectro_direct and using the class core of
A105_ENDPOINT_CONVERSION_INVENTORY.md). The experiment: one enzyme, a substrate that carries a radioactive label (14C, 3H, 32P, 33P, 35S), the
reaction run for ONE stated time and stopped, the labelled product separated from the labelled substrate (thin-layer or paper chromatography, filter
binding, ion exchange, precipitation, a trapped gas such as 14CO2, a gel read by a phosphorimager) and its radioactivity counted. The result is how
much of the label ended in the product at that time (a share converted), or how much product there was. It is one time point, not a rate: a
time course read for its slope is the activity_rate class. The product is found by the label alone, so what the product is rests on the separation.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('endpoint_radiometric'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are
               used as decided in the class note (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no
               immobilized enzyme and no electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation
               reference, so the extraction leaves all four None.
quantities     The three ways the class states an end point, each with the spread the passage gives for it (the unit of the quantity):
                 conversion and conversion_spread                    percent or fraction   the share of the label (or of the substrate) that was converted
                                                                                           to product at the stated time, as the passage gives it
                 control_conversion and control_conversion_spread    percent or fraction   the same share in the paper's own control (no enzyme, boiled
                                                                                           or inactive enzyme, or time zero) at the same time
                 net_conversion and net_conversion_spread            percent or fraction   the share converted AFTER the paper has subtracted its own
                                                                                           control, when the passage gives that corrected number itself
                 product_amount and product_amount_spread           nmol, pmol, umol, nM, uM or mM   the amount (or concentration) of labelled product formed
               and the conditions that decide how far the number can be trusted:
                 reaction_volume          uL or mL              the volume of the reaction in which the product amount was formed
                 endpoint_time            s, min or h           the time at which the reaction was stopped and read
                 counts_test              cpm, dpm or arbitrary the product counts of the test reaction
                 counts_background        cpm, dpm or arbitrary the counts of the paper's own blank, in the same counting unit
                 signal_over_background   fold                  the counts of the test over those of the blank, when the passage gives the ratio itself
                 specific_radioactivity   Ci/mmol, mCi/mmol, uCi/umol, cpm/pmol or dpm/pmol   the specific radioactivity of the labelled substrate used
                 replicate_count          count                 the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation' or 'confidence_interval': what the spreads are.
label_isotope  the radioactive label (a choice, recorded and not judged).
separation_method  how the labelled product was separated from the labelled substrate (a choice, recorded and not judged).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, label_isotope, separation_method), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Not in the record, on purpose: the radiochemical purity of the labelled substrate (supplier certificates are rarely quoted in a paper, so it would
almost always be unknown), a rate, a kcat or a specific activity (the activity_rate class), and a time to completion (another end-point type).

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_endpoint_radiometric_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'endpoint_radiometric'
QUANTITIES = ('conversion', 'conversion_spread', 'control_conversion', 'control_conversion_spread', 'net_conversion', 'net_conversion_spread',
              'product_amount', 'product_amount_spread', 'reaction_volume', 'endpoint_time', 'counts_test', 'counts_background', 'signal_over_background',
              'specific_radioactivity', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
LABEL_ISOTOPES = ('14C', '3H', '32P', '33P', '35S', '125I', 'other')
SEPARATION_METHODS = ('thin_layer_or_paper', 'filter_binding', 'ion_exchange', 'precipitation', 'gas_trapping', 'hplc_with_radiodetector',
                      'gel_electrophoresis', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control_done': YES_NO, 'inactive_enzyme_control_done': YES_NO, 'zero_time_sample_done': YES_NO, 'separation_control_done': YES_NO,
         'reaction_stopped_before_analysis': YES_NO, 'same_time_for_compared_arms': YES_NO, 'fraction_over_total_label': YES_NO,
         'conversion_depends_on_enzyme': YES_NO, 'product_identified_by_standard': YES_NO, 'label_in_product_position': YES_NO,
         'counting_efficiency_corrected': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO,
         'conversion_detected_above_control': YES_NO}

SHARE_UNITS = ('percent', 'fraction')
AMOUNT_UNITS = ('nmol', 'pmol', 'umol', 'nM', 'uM', 'mM')
COUNT_UNITS = ('cpm', 'dpm', 'arbitrary')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'conversion': SHARE_UNITS, 'conversion_spread': SHARE_UNITS, 'control_conversion': SHARE_UNITS, 'control_conversion_spread': SHARE_UNITS,
         'net_conversion': SHARE_UNITS, 'net_conversion_spread': SHARE_UNITS, 'product_amount': AMOUNT_UNITS, 'product_amount_spread': AMOUNT_UNITS,
         'reaction_volume': ('uL', 'mL'), 'endpoint_time': ('s', 'min', 'h'), 'counts_test': COUNT_UNITS, 'counts_background': COUNT_UNITS,
         'signal_over_background': ('fold',), 'specific_radioactivity': ('Ci/mmol', 'mCi/mmol', 'uCi/umol', 'cpm/pmol', 'dpm/pmol'),
         'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
