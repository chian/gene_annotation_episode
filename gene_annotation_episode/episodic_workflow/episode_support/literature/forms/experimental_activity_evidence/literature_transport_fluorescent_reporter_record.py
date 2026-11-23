"""The extracted record of ONE fluorescent-reporter transport experiment in cells (type 'transport_fluorescent_reporter', class transport_response).

DRAFT of 2026-11-22 (owner to correct), built by the SOP from the structure of 'spectro_direct' with the transport_response class core. The
experiment: cells (a native or a heterologous host) that carry the studied transporter, channel or pump are read by fluorescence while a
substrate or an ion moves across the membrane. What is read is one of: a fluorescent substrate analogue taken up or pumped out (for example
2-NBDG for glucose carriers, ethidium or a Hoechst or rhodamine dye for efflux pumps); an indicator dye that reports the substrate or ion
inside the cells (a Ca2+ dye, a pH dye, thallium in the FluxOR plate assay as a surrogate of K+); or a genetically encoded sensor (a glucose, ATP
or fluoride sensor). The signal is read continuously or at set times, on a plate reader, a microscope or a flow cytometer. The result is
usually relative: the signal (its slope or its change) over the paper's own control cells, in fold, and only after a calibration of the indicator a
concentration. Whether the fluorescent molecule IS the substrate, and whether the control cells show the same signal, decide how far it means
transport by this protein.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('transport_fluorescent_reporter'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys
               as decided in the transport_response inventory (section 6, owner to confirm): the cell culture or transfection that carries the
               transporter is the analyte_preparation_ref; cells are not immobilized, there is no electrode, so immobilized_preparation_ref and
               surface_ref stay None. No passage states a preparation reference, so the extraction leaves all four None.
quantities     the effect quantities and the spread of each, then the conditions that decide how far the signal can be trusted:
                 fold_over_control and fold_over_control_spread   fold     the signal (its slope or its change) of the cells with the transporter over the paper's own control
                                                                            cells (untransfected, empty vector, parent strain) or over the baseline before the substrate
                 km and km_spread                                  nM, uM or mM   the Km (or K0.5, or the EC50 of the signal) of the transported substrate the passage reports
                 substrate_concentration                           nM, uM or mM   the concentration of the substrate or fluorescent molecule at which the signal was measured
                 z_prime_factor                                    ratio     the Z' factor of the assay window, when the passage gives it
                 replicate_count                                   count     the number of replicate experiments
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) of the concentration-response, or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are. A plain choice; no criterion rests on it
               (a choice holds no span in the merged record); it is read only to turn a stated spread into a variance.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below. Every criterion of the grader rests on a quantity or a fact.
choice_support name -> support of each plain choice field (spread_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_transport_fluorescent_reporter_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'transport_fluorescent_reporter'
QUANTITIES = ('fold_over_control', 'fold_over_control_spread', 'km', 'km_spread', 'substrate_concentration', 'z_prime_factor', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'untransfected_control_done': YES_NO, 'no_substrate_control_done': YES_NO, 'background_fluorescence_subtracted': YES_NO, 'signal_drift_controlled': YES_NO,
         'indicator_calibrated': YES_NO, 'analogue_is_native_substrate': YES_NO, 'competitor_control_done': YES_NO, 'indicator_specificity_shown': YES_NO,
         'expression_confirmed': YES_NO, 'cells_intact_checked': YES_NO, 'linear_interval_shown': YES_NO, 'independent_replicates': YES_NO,
         'transport_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'fold_over_control': ('fold',), 'fold_over_control_spread': ('fold',), 'km': CONCENTRATION_UNITS, 'km_spread': CONCENTRATION_UNITS,
         'substrate_concentration': CONCENTRATION_UNITS, 'z_prime_factor': ('ratio',), 'replicate_count': ('count',), 'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
