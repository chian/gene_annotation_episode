"""The extracted record of ONE oxygen-electrode enzyme assay (type 'oxygen_electrode', class activity_rate).

An experiment type of the activity_rate class (drafted 2026-11-22 from the first type, spectro_direct; the structure is copied, the content is this
method's own). The assay: one enzyme and its substrate in a closed, stirred, temperature-controlled chamber with an oxygen sensor (a Clark-type
polarographic electrode, a high-resolution respirometer, or an optical sensor), the dissolved oxygen read continuously; the slope of the oxygen trace
after the enzyme (or the substrate) is added is the rate of oxygen consumption (an oxidase or oxygenase) or of oxygen evolution (a catalase or a
water-oxidizing enzyme). The sensor is calibrated with air-saturated buffer and with a zero-oxygen buffer.

This is what a leaf extraction holds for one such assay, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('oxygen_electrode'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The
               class keys are used as decided 2026-11-21 (owner to confirm): the enzyme preparation is the analyte_preparation_ref;
               this type has no immobilized enzyme and no electrode of the claim, so immobilized_preparation_ref and surface_ref stay None.
               No passage states a preparation reference, so the extraction leaves all four None.
quantities     The four effect quantities of the class, each with the spread the passage gives for it (the unit of the quantity). A specific
               activity is a rate of oxygen uptake or evolution per mass of protein (umol O2/min/mg is U/mg); a plain rate with no enzyme amount
               (nmol O2/min, uM/min) is none of the four and is not asked:
                 catalytic_efficiency (kcat/Km) and catalytic_efficiency_spread     M^-1 s^-1, mM^-1 s^-1 or uM^-1 s^-1
                 turnover (kcat) and turnover_spread                                s^-1 or min^-1
                 specific_activity and specific_activity_spread                     U/mg, umol/min/mg or nmol/min/mg
                 rate_over_control and rate_over_control_spread                     fold (the oxygen rate with the enzyme over the paper's own control)
               and the conditions that decide how far a rate can be trusted:
                 km                       nM, uM or mM                the Michaelis constant for the substrate the passage reports
                 substrate_concentration  nM, uM or mM                the substrate concentration at which the reported rate was measured
                 enzyme_concentration     nM or uM                    the enzyme concentration of that measurement
                 oxygen_consumed_percent  percent                     the share of the dissolved oxygen consumed (or, for evolution, produced over the starting oxygen) in the window the rate was taken from
                 starting_oxygen          nM, uM or mM                the dissolved oxygen concentration at the start of the measurement (for example the air-saturated value the passage states)
                 oxygen_km                nM, uM or mM                the Michaelis constant of the enzyme for oxygen, when the passage reports it
                 enzyme_mass              kDa                         the molar mass of the enzyme (a subunit) the passage gives
                 replicate_count          count                       the number of replicate experiments
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) of the saturation curve, or None.
choices        spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
               sensor_kind    'clark_type_electrode', 'optical_sensor', 'high_resolution_respirometer' or None: the oxygen sensor.
               oxygen_change  'consumption', 'evolution' or None: whether the enzyme takes up or gives off oxygen.
               The sensor and the direction are kept in the record for the reviewer; no criterion rests on a choice (a choice holds no span after the merge).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (the three choices), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_oxygen_electrode_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'oxygen_electrode'
QUANTITIES = ('catalytic_efficiency', 'catalytic_efficiency_spread', 'turnover', 'turnover_spread', 'specific_activity', 'specific_activity_spread',
              'rate_over_control', 'rate_over_control_spread', 'km', 'substrate_concentration', 'enzyme_concentration', 'oxygen_consumed_percent',
              'starting_oxygen', 'oxygen_km', 'enzyme_mass', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
SENSOR_KINDS = ('clark_type_electrode', 'optical_sensor', 'high_resolution_respirometer')
OXYGEN_CHANGES = ('consumption', 'evolution')
# The plain choice fields of the record: name -> its vocabulary. Each is kept at the top level of the record with its support in 'choice_support'.
CHOICES = {'spread_kind': SPREAD_KINDS, 'sensor_kind': SENSOR_KINDS, 'oxygen_change': OXYGEN_CHANGES}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'no_substrate_control': YES_NO, 'electrode_calibrated': YES_NO,
         'rate_proportional_to_enzyme': YES_NO, 'oxygen_use_coupled': YES_NO, 'product_identified': YES_NO, 'linear_oxygen_trace': YES_NO,
         'active_site_concentration_determined': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO,
         'oxygen_change_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
EFFICIENCY_UNITS = ('M^-1 s^-1', 'mM^-1 s^-1', 'uM^-1 s^-1')
TURNOVER_UNITS = ('s^-1', 'min^-1')
SPECIFIC_ACTIVITY_UNITS = ('U/mg', 'umol/min/mg', 'nmol/min/mg')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'catalytic_efficiency': EFFICIENCY_UNITS, 'catalytic_efficiency_spread': EFFICIENCY_UNITS, 'turnover': TURNOVER_UNITS, 'turnover_spread': TURNOVER_UNITS,
         'specific_activity': SPECIFIC_ACTIVITY_UNITS, 'specific_activity_spread': SPECIFIC_ACTIVITY_UNITS, 'rate_over_control': ('fold',), 'rate_over_control_spread': ('fold',),
         'km': CONCENTRATION_UNITS, 'substrate_concentration': CONCENTRATION_UNITS, 'enzyme_concentration': ('nM', 'uM'), 'oxygen_consumed_percent': ('percent',),
         'starting_oxygen': CONCENTRATION_UNITS, 'oxygen_km': CONCENTRATION_UNITS, 'enzyme_mass': ('kDa',), 'replicate_count': ('count',),
         'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
