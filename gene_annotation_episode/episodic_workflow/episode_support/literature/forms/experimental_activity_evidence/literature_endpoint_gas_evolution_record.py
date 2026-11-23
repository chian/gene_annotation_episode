"""The extracted record of ONE gas-evolution end-point enzyme experiment (type 'endpoint_gas_evolution', class endpoint_conversion). DRAFT of 2026-11-22, owner to correct.

The assay: one enzyme, one substrate, a reaction run in a closed vessel (a sealed vial or serum bottle with a gas-tight stopper, or a closed manometer flask),
and a gas product (H2, CO2, CH4, N2O, O2) that collects in the headspace. At a stated time the headspace is sampled with a gas-tight syringe and read by gas
chromatography (thermal-conductivity, flame-ionisation, electron-capture or mass-spectrometric detection) or by manometry, and the total gas formed is
reported as an amount (nmol, umol) or as a percent of the theoretical yield. The result is how much gas had formed at that one time: an end point, not a
rate (a rate is the activity_rate class's) and not the time the reaction took to finish (that is endpoint_time_course_completion). A product that is not
a gas is one of the other nine endpoint types (HPLC, mass spectrometry, NMR, colour reagent, radioactivity, gel, optical plateau, second enzyme).

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status,
reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable',
value None and a reason; it is never 0 and never omitted. A stated number is above 0 (no gas formed is the fact gas_detected_above_control answered
no, never the number 0).

Record fields
-------------
version, experiment_type ('endpoint_gas_evolution'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as
               decided for the class (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no immobilized enzyme and no
               electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the extraction leaves
               all four None.
quantities     The three effect quantities of this type, each with the spread the passage gives for it:
                 conversion_percent and conversion_spread          percent   the percent of the theoretical gas yield (the share of the substrate turned
                                                                             into the gas) at the end point, as stated
                 net_conversion_percent and net_conversion_spread  percent   the same percent minus the paper's own control, ONLY when the passage states it
                 gas_amount and gas_amount_spread                  nmol, umol or mmol   the total gas formed in the vessel at the end point (headspace plus
                                                                             what the passage counts as dissolved)
               the paper's own control beside the test:
                 control_conversion_percent                        percent   the same percent in the no-enzyme or inactive-enzyme vessel
                 control_gas_amount                                nmol, umol or mmol   the gas in that control vessel
               the vessel, the denominator and the read time:
                 headspace_volume and liquid_volume                uL or mL  the gas and the liquid volumes of the closed vessel
                 theoretical_yield                                 nmol, umol or mmol   the gas amount the paper expects if all the substrate were converted
                 endpoint_time                                     s, min or h   the time at which the headspace was read
               and the conditions that decide how far a gas reading can be trusted:
                 calibration_low and calibration_high              nmol, umol or mmol   the smallest and the largest known gas amount of the calibration
                 detection_limit                                   nmol, umol or mmol   the detection or quantification limit of the gas reading
                 replicate_count                                   count     the number of replicate (independent) vessels
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
gas_species    'h2', 'co2', 'ch4', 'n2o', 'o2', 'other' or None: which gas was measured. Recorded for the reviewer; no criterion rests on a choice (a choice
               holds no span in the merged record).
readout_method 'gc_tcd', 'gc_fid', 'gc_ecd', 'gc_ms', 'manometry', 'other' or None: how the gas was read. Recorded for the reviewer, as above.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, gas_species, readout_method), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact
about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or
'about_something_else' (the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or
'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default
it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_endpoint_gas_evolution_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'endpoint_gas_evolution'
QUANTITIES = ('conversion_percent', 'conversion_spread', 'net_conversion_percent', 'net_conversion_spread', 'control_conversion_percent', 'gas_amount',
              'gas_amount_spread', 'control_gas_amount', 'theoretical_yield', 'headspace_volume', 'liquid_volume', 'endpoint_time', 'calibration_low',
              'calibration_high', 'detection_limit', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
GAS_SPECIES = ('h2', 'co2', 'ch4', 'n2o', 'o2', 'other')
READOUT_METHODS = ('gc_tcd', 'gc_fid', 'gc_ecd', 'gc_ms', 'manometry', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control_done': YES_NO, 'inactive_enzyme_control_done': YES_NO, 'zero_time_sample_done': YES_NO, 'leak_control_done': YES_NO,
         'enzyme_dependence_shown': YES_NO, 'gas_identified_by_detector': YES_NO, 'calibration_gas_in_same_vessel': YES_NO, 'dissolved_gas_accounted_for': YES_NO,
         'same_time_for_compared_arms': YES_NO, 'initial_substrate_determined': YES_NO, 'independent_replicates': YES_NO, 'native_substrate': YES_NO,
         'purified_enzyme': YES_NO, 'gas_detected_above_control': YES_NO}

AMOUNT_UNITS = ('nmol', 'umol', 'mmol')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'conversion_percent': ('percent',), 'conversion_spread': ('percent',), 'net_conversion_percent': ('percent',), 'net_conversion_spread': ('percent',),
         'control_conversion_percent': ('percent',), 'gas_amount': AMOUNT_UNITS, 'gas_amount_spread': AMOUNT_UNITS, 'control_gas_amount': AMOUNT_UNITS,
         'theoretical_yield': AMOUNT_UNITS, 'headspace_volume': ('uL', 'mL'), 'liquid_volume': ('uL', 'mL'), 'endpoint_time': ('s', 'min', 'h'),
         'calibration_low': AMOUNT_UNITS, 'calibration_high': AMOUNT_UNITS, 'detection_limit': AMOUNT_UNITS, 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
