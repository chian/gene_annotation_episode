"""The extracted record of ONE solid-supported membrane (SSM) electrophysiology experiment (type 'transport_ssm_electrophysiology', class transport_response).

The assay: proteoliposomes (or membrane fragments) of a transporter, channel or pump are adsorbed on a gold sensor that carries a lipid layer
(the solid-supported membrane). The solution over the sensor is exchanged for one that holds the substrate (a substrate concentration jump). Charge that
moves during the transport cycles of an electrogenic protein is read as a transient current, coupled through the capacitance of the sensor; the
peak of the transient (nA) and its integral (the charge, nC) are read, and the peak current is followed over a series of substrate concentrations to
give the apparent Km. The voltage is not clamped and the current is a transient, not a steady flux. The amplitude depends on how much protein is
on the sensor, so the usable results are the Km and the fold over a control sensor (empty liposomes) or over a jump without substrate. Patch clamp,
two-electrode clamp and planar bilayer recordings (clamped voltage, steady current) and radiotracer uptake are other methods.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('transport_ssm_electrophysiology'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys
               are used as decided 2026-11-22 (owner to confirm): the purified protein or membrane preparation is the analyte_preparation_ref,
               the proteoliposome batch on the sensor is the immobilized_preparation_ref, the gold sensor is the surface_ref. No passage states
               a preparation reference, so the extraction leaves all four None.
quantities     The effect quantities of the class that this method can state, each with the spread the passage gives for it:
                 km                      nM, uM or mM     the apparent Km (K0.5) of the substrate from the peak current (or charge) against concentration
                 km_spread               nM, uM or mM     its reported uncertainty
                 fold_over_control       fold             how many times larger the signal is than that of the paper's own control sensor or jump
                 fold_over_control_spread  fold            its reported uncertainty
               and the context that decides how far a transient current can be trusted (never an effect of this class):
                 peak_current            pA, nA or uA     the peak of the transient current after the jump (magnitude)
                 charge                  pC, nC or uC     the charge translocated (the integral of the transient)
                 decay_time              ms or s          the decay time constant of the transient
                 jump_substrate_concentration  nM, uM or mM   the substrate concentration of the jump at which the peak current or charge was read
                 sensor_count            count            the number of sensors (the sampling unit of the readings)
                 preparation_count       count            the number of independent proteoliposome preparations
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) of the peak-current series, or None.
spread_kind    'standard_error', 'standard_deviation' or 'confidence_interval' (or None): what the spreads are.
readout        'peak_current' or 'integrated_charge' (or None): what the stated Km or fold was derived from. Recorded only; no criterion reads it.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, readout), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_transport_ssm_electrophysiology_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'transport_ssm_electrophysiology'
QUANTITIES = ('km', 'km_spread', 'fold_over_control', 'fold_over_control_spread', 'peak_current', 'charge', 'decay_time', 'jump_substrate_concentration',
              'sensor_count', 'preparation_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
READOUTS = ('peak_current', 'integrated_charge')
# The plain choice fields: name -> its vocabulary. A choice is recorded only; no criterion rests on one (a choice carries no span after the merge).
CHOICES = {'spread_kind': SPREAD_KINDS, 'readout': READOUTS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'empty_liposome_sensor_done': YES_NO, 'non_substrate_jump_done': YES_NO, 'buffer_jump_artefact_subtracted': YES_NO, 'solutions_matched_except_substrate': YES_NO,
         'sensor_capacitance_stated': YES_NO, 'same_sensor_reference_jump': YES_NO, 'blocker_control_done': YES_NO, 'ion_substitution_done': YES_NO,
         'inactive_protein_control_done': YES_NO, 'electrogenic_transport_stated': YES_NO, 'native_substrate': YES_NO, 'independent_sensors': YES_NO,
         'independent_preparations': YES_NO, 'transport_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry. 'fold' is the paper's word for the ratio;
# the converter reads it as the sheet's 'dimensionless' exactly (a stated n-fold is n).
UNITS = {'km': CONCENTRATION_UNITS, 'km_spread': CONCENTRATION_UNITS, 'fold_over_control': ('fold',), 'fold_over_control_spread': ('fold',),
         'peak_current': ('pA', 'nA', 'uA'), 'charge': ('pC', 'nC', 'uC'), 'decay_time': ('ms', 's'), 'jump_substrate_concentration': CONCENTRATION_UNITS,
         'sensor_count': ('count',), 'preparation_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
