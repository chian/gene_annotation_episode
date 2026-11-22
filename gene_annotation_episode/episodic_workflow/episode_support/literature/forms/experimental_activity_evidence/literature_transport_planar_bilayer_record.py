"""The extracted record of ONE planar lipid bilayer recording (type 'transport_planar_bilayer', class transport_response).

The assay: a purified channel or transporter (or proteoliposomes that carry it) is put into an artificial lipid bilayer that separates two
chambers (a painted or folded bilayer over an aperture, or a bilayer made at the tip of a pipette). A voltage is held across the bilayer and the
current is recorded. Insertion of one channel shows as a step of a fixed size, the unitary current; divided by the driving force it is the unitary
conductance. With two different ions in the two chambers (a bi-ionic or salt gradient) the voltage at which the current is zero, the reversal
potential, tells which ion passes more easily (the permeability ratio). The same bilayer without the protein is the control. Macroscopic current
of many channels in one bilayer is read the same way. The recording says that this protein moves charge across a membrane and, by the reversal
potential, which ion carries it; it does not say how fast a substrate is moved by a carrier in a cell.

This is what a leaf extraction holds for one such recording, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('transport_planar_bilayer'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys
               are used as decided 2026-11-22 (owner to confirm): the purified protein preparation is the analyte_preparation_ref; the
               proteoliposome batch fused into the bilayer is the immobilized_preparation_ref; the bilayer cup or aperture is not a sample
               preparation shared between results, so surface_ref stays None. No passage states a preparation reference, so the extraction
               leaves all four None.
quantities     unitary_conductance and unitary_conductance_spread   pS or nS    the single-channel conductance, already divided by the driving force
               unitary_current                                      pA or nA    the SIZE of the single-channel current (no sign)
               baseline_noise                                       pA or nA    the root-mean-square noise of the recording
               holding_voltage                                      mV          the voltage the unitary current was measured at, with its sign
               reversal_potential                                   mV          the voltage at which the current is zero, with its sign
               permeability_ratio                                   ratio       the permeability of the more permeant ion over that of the less permeant one
               charge_rate                                          charges_per_s  the current divided by the elementary charge, one channel
               event_count                                          count       the number of single-channel events behind the stated size
               bilayer_count                                        count       the number of independent bilayers recorded
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the conductance spread is. A plain choice: it
               is kept in the record for the converter (which turns a spread into a variance); no criterion rests on a choice.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

The two voltages are the only fields that may be negative or zero (a recording is often made at a negative voltage and a reversal potential may be
negative or zero); every other number is above 0.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_transport_planar_bilayer_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'transport_planar_bilayer'
QUANTITIES = ('unitary_conductance', 'unitary_conductance_spread', 'unitary_current', 'baseline_noise', 'holding_voltage', 'reversal_potential',
              'permeability_ratio', 'charge_rate', 'event_count', 'bilayer_count')
SIGNED_QUANTITIES = ('holding_voltage', 'reversal_potential')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'protein_free_bilayer_control_done': YES_NO, 'bilayer_integrity_checked': YES_NO, 'solutions_stated': YES_NO, 'driving_force_corrected': YES_NO,
         'bi_ionic_gradient_done': YES_NO, 'named_ion_preferred': YES_NO, 'blocker_control_done': YES_NO, 'purified_protein': YES_NO,
         'independent_bilayers': YES_NO, 'transport_detected_above_control': YES_NO}

CONDUCTANCE_UNITS = ('pS', 'nS')
CURRENT_UNITS = ('pA', 'nA')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'unitary_conductance': CONDUCTANCE_UNITS, 'unitary_conductance_spread': CONDUCTANCE_UNITS, 'unitary_current': CURRENT_UNITS, 'baseline_noise': CURRENT_UNITS,
         'holding_voltage': ('mV',), 'reversal_potential': ('mV',), 'permeability_ratio': ('ratio',), 'charge_rate': ('charges_per_s',),
         'event_count': ('count',), 'bilayer_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
