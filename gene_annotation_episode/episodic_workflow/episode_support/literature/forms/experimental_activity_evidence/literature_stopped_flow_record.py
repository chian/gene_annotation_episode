"""The extracted record of ONE stopped-flow rapid-mixing enzyme experiment (type 'stopped_flow', class activity_rate).

Drafted 2026-11-22 from the structure of the first type of the class, spectro_direct (its record, extraction, criteria, grader and converter are the
template); every number and every choice of field below is a DRAFT for the owner to correct. The experiment: the enzyme and its substrate (or
the enzyme and a ligand) are driven together into an observation cell in about a millisecond (the dead time) and the absorbance or the
fluorescence is read from then on, so the first turnovers can be followed before the reaction settles into its steady state. It reports the rate
constant of one phase of the signal: the single-turnover rate (the enzyme in excess over the substrate), the rate of a burst of product, the
observed rate constant k_obs and how it depends on the substrate, and sometimes the steady-state turnover after the burst. A first-order rate
constant does not depend on how the signal is calibrated, which is why this record holds no extinction coefficient.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('stopped_flow'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are
               used as decided 2026-11-21 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no immobilized
               enzyme and no electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so
               the extraction leaves all four None.
quantities     The three effect quantities of the type, each with the spread the passage gives for it (the unit of the quantity):
                 catalytic_efficiency (kcat/Km, or the second-order rate constant of the chemical reaction) and catalytic_efficiency_spread
                                          M^-1 s^-1, mM^-1 s^-1 or uM^-1 s^-1
                 steady_state_turnover (kcat of the steady-state phase after the burst) and steady_state_turnover_spread       s^-1 or min^-1
                 single_turnover_rate (rate constant of the chemical step under single turnover or at saturating substrate, k_chem, k_max, the burst rate
                                          constant) and single_turnover_rate_spread                                                     s^-1 or min^-1
                 observed_rate_constant (the largest k_obs of the phase of product formation or substrate loss) and
                                          observed_rate_constant_spread                                                                 s^-1 or min^-1
               and the conditions that decide how far a rate constant can be trusted:
                 burst_amplitude              mol/mol_site, nM or uM     the size of the burst: per active site, or as a concentration
                 half_saturation_concentration  nM, uM or mM             the substrate concentration at half the limiting k_obs (Kd, K1/2 or Km, as the passage names it)
                 enzyme_concentration         nM, uM or mM               the enzyme concentration of the experiment (after mixing)
                 substrate_concentration      nM, uM or mM               the substrate concentration of the experiment (after mixing)
                 dead_time                    ms or s                    the dead time of the instrument
                 shots_averaged               count                      the number of shots (traces) averaged into one trace
                 replicate_count              count                      the number of independent experiments
concentration_series
               operand whose 'value' is a list of substrate concentrations (nM, uM or mM) at which k_obs was measured, or None.
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are (the standard error of a fit counts as
               'standard_error').
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_stopped_flow_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'stopped_flow'
QUANTITIES = ('catalytic_efficiency', 'catalytic_efficiency_spread', 'steady_state_turnover', 'steady_state_turnover_spread', 'single_turnover_rate', 'single_turnover_rate_spread',
              'observed_rate_constant', 'observed_rate_constant_spread', 'burst_amplitude', 'half_saturation_concentration', 'enzyme_concentration', 'substrate_concentration',
              'dead_time', 'shots_averaged', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'no_enzyme_control': YES_NO, 'inactive_enzyme_control': YES_NO, 'no_substrate_control': YES_NO, 'phase_assigned_to_chemical_step': YES_NO,
         'product_identified': YES_NO, 'single_turnover_conditions': YES_NO, 'active_site_concentration_determined': YES_NO, 'native_substrate': YES_NO,
         'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'activity_detected_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
EFFICIENCY_UNITS = ('M^-1 s^-1', 'mM^-1 s^-1', 'uM^-1 s^-1')
RATE_CONSTANT_UNITS = ('s^-1', 'min^-1')
# The unit vocabulary of each quantity (and of the concentration series): the units a record may carry.
UNITS = {'catalytic_efficiency': EFFICIENCY_UNITS, 'catalytic_efficiency_spread': EFFICIENCY_UNITS,
         'steady_state_turnover': RATE_CONSTANT_UNITS, 'steady_state_turnover_spread': RATE_CONSTANT_UNITS,
         'single_turnover_rate': RATE_CONSTANT_UNITS, 'single_turnover_rate_spread': RATE_CONSTANT_UNITS,
         'observed_rate_constant': RATE_CONSTANT_UNITS, 'observed_rate_constant_spread': RATE_CONSTANT_UNITS,
         'burst_amplitude': ('mol/mol_site', 'nM', 'uM'), 'half_saturation_concentration': CONCENTRATION_UNITS, 'enzyme_concentration': CONCENTRATION_UNITS,
         'substrate_concentration': CONCENTRATION_UNITS, 'dead_time': ('ms', 's'), 'shots_averaged': ('count',), 'replicate_count': ('count',),
         'concentration_series': CONCENTRATION_UNITS}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
