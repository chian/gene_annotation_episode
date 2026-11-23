"""The extracted record of ONE two-electrode voltage clamp experiment on Xenopus oocytes (type 'transport_oocyte_two_electrode', class transport_response).

DRAFT of 2026-11-22 (owner to correct). The assay: oocytes of the frog Xenopus laevis are injected with the cRNA of the transporter or channel under test (matched
control oocytes are injected with water or left uninjected, from the same batch), kept for a few days to express it, and then each oocyte is held at a set membrane
voltage with two microelectrodes, one that measures the voltage and one that injects the current that keeps it there. The substrate is added to the bath while the
current is recorded; the substrate-induced current is the change of the current of the same oocyte from before the substrate to during it. What such an experiment
reports is that current (in nA or uA) over the current of the control oocytes, an apparent Km (the half-saturating concentration) from a series of substrate
concentrations, and whether the current (or its reversal voltage) depends on the ion that is replaced. A current is a flow of CHARGE, not of the substrate: an
electroneutral transporter gives none, and a carrier with an uncoupled leak or a host channel can give one without moving the substrate; so the type asks beside the
current whether the substrate itself was seen to move. It is NOT this method when a labelled substrate is counted in whole cells (cell tracer uptake, even in oocytes),
when a patch pipette records one cell or one patch, when a purified protein is recorded in a planar bilayer, when a solid-supported membrane is used, or when only growth
depends on the transport.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a reason; it
is never 0 and never omitted. A number is always above 0: a current is recorded as its size, and its direction is the plain choice current_direction.

Record fields
-------------
version, experiment_type ('transport_oocyte_two_electrode'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). Mapping of the class note of 2026-11-22
               (owner to confirm): the batch of injected oocytes that makes the protein is the analyte_preparation_ref; an oocyte has no vesicle batch and the electrodes
               are not a sample preparation shared between results, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference,
               so the extraction leaves all four None.
quantities     The two effect quantities of the class that a two-electrode clamp states, each with the spread the passage gives for it (in the unit of the quantity):
                 km and km_spread                                  nM, uM or mM   the apparent Km (K0.5, K1/2, the half-saturating substrate concentration) of the substrate-induced current
                 fold_over_control and fold_over_control_spread    fold           the substrate-induced current of the oocytes with the protein over that of the paper's own control oocytes
               and the numbers that decide how far a current can be trusted (context, never the effect):
                 current                  nA or uA        the size of the substrate-induced current of the oocytes with the protein, at the voltage the passage states
                 control_current          nA or uA        the size of the substrate-induced current of the control oocytes, measured the same way
                 substrate_concentration  nM, uM or mM    the single substrate concentration at which that current (or the fold) was measured
                 oocyte_count             count           the number of oocytes recorded (the n of a mean)
                 batch_count              count           the number of independent batches of oocytes (oocytes of different donor frogs, injected on different occasions)
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) of the concentration-response curve, or None.
choices        plain choices, kept for the reviewer; NO criterion rests on a choice (a choice holds no span in the merged record), so everything a criterion needs is a
               quantity or a yes/no fact:
                 spread_kind        'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are
                 current_direction  'inward' or 'outward' or None: the direction of the substrate-induced current as the passage states it
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (spread_kind, current_direction), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Not asked, and why: a turnover or a unitary conductance (a whole-oocyte current is the sum of many molecules, and a count of active molecules is almost never stated),
a charge per substrate molecule (it needs a simultaneous tracer measurement and is rare), the holding voltage as a number (it is negative for most clamps and a number
of the form is always above 0; the fact holding_voltage_stated carries it with its quote), and the reversal voltage (its meaning needs the ion and the concentration
change; the fact ion_dependence_shown carries what the passage says).

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how well its
quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the
topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader
does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go through
the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_transport_oocyte_two_electrode_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'transport_oocyte_two_electrode'
QUANTITIES = ('km', 'km_spread', 'fold_over_control', 'fold_over_control_spread', 'current', 'control_current', 'substrate_concentration', 'oocyte_count', 'batch_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
CURRENT_DIRECTIONS = ('inward', 'outward')
# The plain choice fields: name -> vocabulary. They are kept in the record for the reviewer; no criterion rests on one.
CHOICES = {'spread_kind': SPREAD_KINDS, 'current_direction': CURRENT_DIRECTIONS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
# A fact the passage can only state as done (a passage does not say that it left its clamp voltage unstated, or that its control oocytes showed a current of no size).
YES_ONLY = ('yes', 'unknown', 'not_applicable')
FACTS = {'uninjected_control_done': YES_NO, 'control_shows_no_substrate_current': YES_ONLY, 'same_oocyte_baseline_done': YES_NO, 'leak_subtracted': YES_NO,
         'non_substrate_gives_no_current': YES_NO, 'ion_dependence_shown': YES_NO, 'substrate_uptake_confirmed': YES_NO, 'inactive_mutant_gives_no_current': YES_NO,
         'expression_confirmed': YES_NO, 'holding_voltage_stated': YES_ONLY, 'native_substrate': YES_NO, 'independent_batches': YES_NO,
         'transport_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
CURRENT_UNITS = ('nA', 'uA')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'km': CONCENTRATION_UNITS, 'km_spread': CONCENTRATION_UNITS, 'fold_over_control': ('fold',), 'fold_over_control_spread': ('fold',),
         'current': CURRENT_UNITS, 'control_current': CURRENT_UNITS, 'substrate_concentration': CONCENTRATION_UNITS, 'oocyte_count': ('count',),
         'batch_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
