"""The extracted record of ONE isothermal titration calorimetry enzyme-kinetics experiment (type 'itc_kinetics', class activity_rate).

DRAFT of the activity_rate class (built 2026-11-22 from the spectro_direct template, A105 SOP steps 1 and 5; all numbers of the converter are
EXPERT_REVIEW, owner to confirm). The assay: one enzyme and one substrate in a calorimeter cell, the enzyme (or the substrate) injected once or
in several injections, the heat of the reaction read continuously as thermal power (ucal/s, uW). The power is proportional to the rate: power =
rate x cell volume x apparent reaction enthalpy, so the rate follows from the power and an enthalpy that was measured on its own (the heat of
complete conversion of a known amount of substrate). The assay is label-free and works for any reaction that gives heat; it does not say what
the product is. It is NOT the binding titration of type 'itc' (that one reports a binding constant, a stoichiometry and an enthalpy of binding);
this type reports a rate, kcat, Km or a specific activity from a heat rate.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('itc_kinetics'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys
               are used as decided 2026-11-21 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no
               immobilized enzyme and no electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation
               reference, so the extraction leaves all four None.
quantities     The four effect quantities of the class, each with the spread the passage gives for it (the unit of the quantity):
                 catalytic_efficiency (kcat/Km) and catalytic_efficiency_spread     M^-1 s^-1, mM^-1 s^-1 or uM^-1 s^-1
                 turnover (kcat) and turnover_spread                                s^-1 or min^-1
                 specific_activity and specific_activity_spread                     U/mg, umol/min/mg or nmol/min/mg
                 rate_over_control and rate_over_control_spread                     fold (the rate of the enzyme over the paper's own control)
               and the conditions that decide how far a rate can be trusted:
                 km                       nM, uM or mM                the Michaelis constant the passage reports
                 substrate_concentration  nM, uM or mM                the substrate concentration at which the reported rate was measured
                 enzyme_concentration     nM or uM                    the enzyme concentration of that measurement
                 substrate_consumed_percent  percent                  the share of the substrate consumed when the rate was read
                 reaction_enthalpy        kcal/mol or kJ/mol          the size (no sign) of the apparent molar enthalpy of the reaction that turns power into rate
                 thermal_power            nW, uW or ucal/s            the thermal power of the enzyme reaction (the steady level above the baseline)
                 dilution_power           nW, uW or ucal/s            the thermal power of the control injection (substrate into buffer, or enzyme into buffer)
                 baseline_noise           nW, uW or ucal/s            the noise of the baseline power
                 enzyme_mass              kDa                         the molar mass of the enzyme (a subunit) the passage gives
                 replicate_count          count                       the number of replicate experiments
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) of the saturation curve, or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
injection_mode 'single_injection', 'multiple_injection' or None: how the reaction was started (recorded only; no criterion reads it).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, injection_mode), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_itc_kinetics_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'itc_kinetics'
QUANTITIES = ('catalytic_efficiency', 'catalytic_efficiency_spread', 'turnover', 'turnover_spread', 'specific_activity', 'specific_activity_spread',
              'rate_over_control', 'rate_over_control_spread', 'km', 'substrate_concentration', 'enzyme_concentration', 'substrate_consumed_percent',
              'reaction_enthalpy', 'thermal_power', 'dilution_power', 'baseline_noise', 'enzyme_mass', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
INJECTION_MODES = ('single_injection', 'multiple_injection')
# The plain choice fields: name -> its vocabulary. They are recorded only; no criterion rests on a choice (a choice carries no span after the merge).
CHOICES = {'spread_kind': SPREAD_KINDS, 'injection_mode': INJECTION_MODES}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'substrate_into_buffer_control': YES_NO, 'enzyme_into_buffer_control': YES_NO, 'rate_proportional_to_enzyme': YES_NO,
         'product_identified': YES_NO, 'enthalpy_determined_in_assay_buffer': YES_NO, 'steady_power_plateau': YES_NO, 'response_time_accounted': YES_NO,
         'active_site_concentration_determined': YES_NO, 'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO,
         'activity_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
EFFICIENCY_UNITS = ('M^-1 s^-1', 'mM^-1 s^-1', 'uM^-1 s^-1')
TURNOVER_UNITS = ('s^-1', 'min^-1')
SPECIFIC_ACTIVITY_UNITS = ('U/mg', 'umol/min/mg', 'nmol/min/mg')
POWER_UNITS = ('nW', 'uW', 'ucal/s')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'catalytic_efficiency': EFFICIENCY_UNITS, 'catalytic_efficiency_spread': EFFICIENCY_UNITS, 'turnover': TURNOVER_UNITS, 'turnover_spread': TURNOVER_UNITS,
         'specific_activity': SPECIFIC_ACTIVITY_UNITS, 'specific_activity_spread': SPECIFIC_ACTIVITY_UNITS, 'rate_over_control': ('fold',), 'rate_over_control_spread': ('fold',),
         'km': CONCENTRATION_UNITS, 'substrate_concentration': CONCENTRATION_UNITS, 'enzyme_concentration': ('nM', 'uM'), 'substrate_consumed_percent': ('percent',),
         'reaction_enthalpy': ('kcal/mol', 'kJ/mol'), 'thermal_power': POWER_UNITS, 'dilution_power': POWER_UNITS, 'baseline_noise': POWER_UNITS,
         'enzyme_mass': ('kDa',), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
