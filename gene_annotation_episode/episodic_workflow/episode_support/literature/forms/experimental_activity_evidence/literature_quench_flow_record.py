"""The extracted record of ONE rapid chemical quench-flow enzyme experiment (type 'quench_flow', class activity_rate).

Draft built 2026-11-22 from the structure of the first activity_rate type (spectro_direct). The experiment: one enzyme and its substrate are
mixed in a quench-flow instrument (or by hand) and left to react for a set time, from milliseconds to seconds; the reaction is then stopped
at once by a quench (acid, base, EDTA, a denaturant), and the product is separated from the substrate and counted (radioactivity after
thin-layer chromatography or a gel, HPLC, or mass spectrometry). Each time point is a separate mixing and quenching, so the time course is built
from many discontinuous points. Two designs are common: a burst (substrate in excess over enzyme: a fast first turnover, the burst, followed by a slower
steady-state line) and a single turnover (enzyme in excess over substrate: one exponential, whose rate constant is that of the chemical step).
It is not stopped-flow (an optical trace read in the mixing cell) and not a continuous or end-point assay of one long reaction.

This is what a leaf extraction holds for one such experiment, in the operand shape the existing A105 assay grading inputs use (value, unit,
status, reason, measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with
status 'unavailable', value None and a reason; it is never 0 and never omitted.

Record fields
-------------
version, experiment_type ('quench_flow'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys are
               used as decided 2026-11-21 (owner to confirm): the enzyme preparation is the analyte_preparation_ref; this type has no immobilized
               enzyme and no electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a preparation reference, so the
               extraction leaves all four None.
quantities     The two rate quantities the method reports, each with the spread the passage gives for it:
                 chemical_rate_constant and chemical_rate_constant_spread   s^-1 or min^-1   the observed rate constant of the single-turnover or burst
                                                                                              phase (k_obs, k_burst, k_chem, k_pol, k_cat of a single turnover)
                 turnover and turnover_spread                               s^-1 or min^-1   the steady-state rate per enzyme (per active site) after the
                                                                                              burst, or the kcat the passage gives
               the burst, and the conditions that decide how far the rate and the amplitude can be trusted:
                 burst_amplitude              nM, uM or mM   the amplitude of the burst: the product made in the fast phase
                 burst_amplitude_per_enzyme   ratio          the same amplitude as moles of product per mole of enzyme (active sites)
                 enzyme_concentration         nM, uM or mM   the enzyme concentration in the reaction after mixing
                 substrate_concentration      nM, uM or mM   the substrate concentration in the reaction after mixing
                 shortest_time                ms or s        the earliest time point (the shortest reaction time before the quench)
                 longest_time                 ms or s        the latest time point of the time course
                 time_point_count             count          the number of reaction times of the time course
                 replicate_count              count          the number of replicate experiments
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are (a plain choice, for recording).
detection_method  how the product was separated and counted: one of DETECTION_METHODS or None (a plain choice, for recording only).
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below.
choice_support name -> support of each plain choice field (spread_kind, detection_method), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

No criterion rests on a plain choice: a choice carries no span after the merge of the leaf records, so everything a criterion needs is a
quantity or a yes/no fact with its quote.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the
extraction's fact about how well its quote supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it
only by implication) or 'about_something_else' (the quote is on the topic but is really about another measurement or condition). An
unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it; the
converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go
through the extraction (the extraction always passes the model's answer).
"""

VERSION = 'a105_quench_flow_record'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'quench_flow'
QUANTITIES = ('chemical_rate_constant', 'chemical_rate_constant_spread', 'turnover', 'turnover_spread', 'burst_amplitude', 'burst_amplitude_per_enzyme',
              'enzyme_concentration', 'substrate_concentration', 'shortest_time', 'longest_time', 'time_point_count', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
DETECTION_METHODS = ('radioactivity_after_separation', 'chromatography', 'mass_spectrometry', 'gel_or_thin_layer', 'other_separation')
# The plain choice fields (recording only): name -> vocabulary.
CHOICES = {'spread_kind': SPREAD_KINDS, 'detection_method': DETECTION_METHODS}
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'zero_time_control': YES_NO, 'no_enzyme_control': YES_NO, 'quench_stops_reaction': YES_NO, 'enzyme_dependence_shown': YES_NO,
         'product_identified': YES_NO, 'product_quantified_against_standard': YES_NO, 'single_turnover_conditions': YES_NO,
         'multiple_turnover_conditions': YES_NO, 'time_course_fitted': YES_NO, 'active_site_concentration_determined': YES_NO,
         'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'product_formed_above_control': YES_NO}

CONCENTRATION_UNITS = ('nM', 'uM', 'mM')
RATE_CONSTANT_UNITS = ('s^-1', 'min^-1')
TIME_UNITS = ('ms', 's')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'chemical_rate_constant': RATE_CONSTANT_UNITS, 'chemical_rate_constant_spread': RATE_CONSTANT_UNITS, 'turnover': RATE_CONSTANT_UNITS,
         'turnover_spread': RATE_CONSTANT_UNITS, 'burst_amplitude': CONCENTRATION_UNITS, 'burst_amplitude_per_enzyme': ('ratio',),
         'enzyme_concentration': CONCENTRATION_UNITS, 'substrate_concentration': CONCENTRATION_UNITS, 'shortest_time': TIME_UNITS,
         'longest_time': TIME_UNITS, 'time_point_count': ('count',), 'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
