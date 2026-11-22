"""The extracted record of ONE patch-clamp experiment on cells (type 'transport_patch_clamp', class transport_response).

DRAFT built 2026-11-22 on the shape of literature_spectro_direct_record.py, with the class core of transport_response (A105_TRANSPORT_RESPONSE_INVENTORY.md,
sections 2 to 4). Owner to correct. The experiment: a cell that makes the protein under test (HEK, CHO or another host, or a native cell) is held by a
glass pipette in the whole-cell, inside-out, outside-out or cell-attached configuration; the membrane current is recorded under a voltage step, ramp or
holding voltage, with and without the substrate, a blocker or a replaced ion, and in control cells that do not make the protein. What such an experiment
reports is a current, a current density, a reversal potential, the conductance of one channel (from single-channel events or the slope of a single-channel
current-voltage curve), a charge flow per second, or the current of the cells with the protein over that of the control cells. It is NOT this method when
the cell is a Xenopus oocyte clamped with two electrodes, when the protein is purified and put into a planar lipid bilayer or onto a solid-supported
membrane, when the substrate is a labelled tracer counted after filtration, or when a dye or an ion indicator is read by fluorescence.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a
reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('transport_patch_clamp'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are used as the
               class note of 2026-11-22 sets them (owner to confirm): the cell culture (or transfection) that makes the protein is the analyte_preparation_ref;
               the patch pipette is not a sample preparation that results share, and a cell has no vesicle batch and no sensor, so immobilized_preparation_ref
               and surface_ref stay None. No passage states a preparation reference, so the extraction leaves all four None.
quantities     The three effect quantities of the class that a patch-clamp experiment states, each with the spread the passage gives for it (in the unit of the
               quantity):
                 unitary_conductance and unitary_conductance_spread     pS or nS      the conductance of ONE channel, from single-channel events or the slope of a
                                                                                       single-channel current-voltage curve (not a whole-cell conductance)
                 charge_rate and charge_rate_spread                     charges/s     the elementary charges that pass per second through one channel or
                                                                                       transporter, as the passage states it
                 fold_over_control and fold_over_control_spread         fold          the current (or current density) of the cells with the protein over that
                                                                                       of the paper's own control cells, or of the response over the baseline
               and the conditions that decide how far a recording can be trusted:
                 holding_voltage      mV      the voltage the current or conductance was taken at (signed)
                 reversal_potential   mV      the measured reversal potential of the current (signed)
                 nernst_potential     mV      the equilibrium (Nernst) potential of the ion the passage tests as the carrier, for the recording solutions (signed)
                 series_resistance    MOhm    the series (access) resistance of the whole-cell recording
                 seal_resistance      MOhm or GOhm   the resistance of the seal between pipette and membrane
                 cell_count           count   the number of cells (or patches) the result is taken from: the sampling unit of the method
                 batch_count          count   the number of independent transfections, cultures or preparations those cells came from
               A current in pA or nA and a current density in pA/pF are NOT asked: a current without its control cells is no effect, and a current depends on the
               expression level, the cell size and the voltage, so no criterion reads it. A Km or EC50 is not asked either (a dose-response of a current is
               kept for the oocyte type; here the effect is the conductance, the charge rate or the fold over the control).
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
patch_configuration  'whole_cell', 'inside_out', 'outside_out', 'cell_attached' or None. Kept for the reviewer; no criterion rests on a choice (a choice holds
               no span in the merged record).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, patch_configuration), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Signed numbers. The three voltages keep their sign (SIGNED_QUANTITIES): a reversal potential of -35 mV is -35, and 0 mV is a possible stated value. Every other
quantity is a positive number.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how
well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else'
(the quote is on the topic but is really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an
unstated choice carry None. The grader does not judge it; the converter does. The constructors take ``support`` and default it to 'direct'; the default is
only for forms built by tests that do not go through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_transport_patch_clamp_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'transport_patch_clamp'
QUANTITIES = ('unitary_conductance', 'unitary_conductance_spread', 'charge_rate', 'charge_rate_spread', 'fold_over_control', 'fold_over_control_spread',
              'holding_voltage', 'reversal_potential', 'nernst_potential', 'series_resistance', 'seal_resistance', 'cell_count', 'batch_count')
SIGNED_QUANTITIES = ('holding_voltage', 'reversal_potential', 'nernst_potential')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
PATCH_CONFIGURATIONS = ('whole_cell', 'inside_out', 'outside_out', 'cell_attached')
# The plain choice fields: name -> vocabulary. They are kept in the record for the reviewer; no criterion rests on one.
CHOICES = {'spread_kind': SPREAD_KINDS, 'patch_configuration': PATCH_CONFIGURATIONS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'untransfected_control_done': YES_NO, 'inactive_mutant_control_done': YES_NO, 'substrate_free_control_done': YES_NO, 'ion_substitution_done': YES_NO,
         'blocker_control_done': YES_NO, 'series_resistance_compensated': YES_NO, 'leak_subtracted': YES_NO, 'driving_force_corrected': YES_NO,
         'single_channel_resolved': YES_NO, 'independent_preparations': YES_NO, 'native_substrate': YES_NO, 'transport_detected_above_control': YES_NO}

CONDUCTANCE_UNITS = ('pS', 'nS')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'unitary_conductance': CONDUCTANCE_UNITS, 'unitary_conductance_spread': CONDUCTANCE_UNITS, 'charge_rate': ('charges/s',), 'charge_rate_spread': ('charges/s',),
         'fold_over_control': ('fold',), 'fold_over_control_spread': ('fold',), 'holding_voltage': ('mV',), 'reversal_potential': ('mV',), 'nernst_potential': ('mV',),
         'series_resistance': ('MOhm',), 'seal_resistance': ('MOhm', 'GOhm'), 'cell_count': ('count',), 'batch_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
