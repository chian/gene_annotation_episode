"""The extracted record of ONE sampled reaction followed to a stated completion or equilibrium (type 'endpoint_time_course_completion', class endpoint_conversion).

A type of the endpoint_conversion class (DRAFT built 2026-11-22 by the SOP, copying the shape of spectro_direct and using the class core of
A105_ENDPOINT_CONVERSION_INVENTORY.md; nothing was run). The experiment: one enzyme and one substrate, the reaction sampled over time (by NMR in the tube, HPLC
or mass spectrometry of quenched samples, an optical signal, a gel, whatever detector) until a STATED state is reached, for example "no substrate signal left", "the
product stops rising" or "the ratio of the two species no longer changes" (equilibrium). The result is the TIME to reach that state (a completion time, possibly only a
bound such as "more than 18 h" or "less than 10 min") and, when the paper compares two arms (the enzyme against its own control, a preparation before and after a
clean-up step, a mutant against the wild type), the time of the reference arm and the ratio of the two times. It is not a rate (rates and kinetic constants are
activity_rate) and not a share converted at one fixed time (the other endpoint_conversion types).

This is what a leaf extraction holds for one such time course, in the operand shape the existing A105 assay grading inputs use (value, unit, status, reason,
measurement_keys, source_refs, origin, native_component, support). A value the source did not give is an operand with status 'unavailable', value None and a reason; it is
never 0 and never omitted.

Record fields
-------------
version, experiment_type ('endpoint_time_course_completion'), experiment_ref, source_ref, assertion_ref
preparations   analyte_preparation_ref, immobilized_preparation_ref, surface_ref, dataset_ref: each a string or None (unknown). The class keys: the enzyme preparation is the
               analyte_preparation_ref; this type has no immobilized enzyme and no electrode, so immobilized_preparation_ref and surface_ref stay None. No passage states a
               preparation reference, so the extraction leaves all four None.
quantities     one operand each:
                 completion_time and completion_time_spread               s, min or h   the time at which the stated completion or equilibrium was reached, and its spread
                 reference_completion_time                                s, min or h   the same state's time in the paper's reference arm (control, earlier preparation, wild type)
                 completion_time_ratio and completion_time_ratio_spread   fold          the reference time over the test time, as the passage states it (more than 1: the test is sooner)
                 sampling_interval                                        s, min or h   the gap between the last sample before completion and the sample at completion (or the regular spacing)
                 enzyme_loading_test and enzyme_loading_reference         nM, uM or mg/mL   the enzyme concentration of the test arm and of the reference arm
                 replicate_count                                          count         the number of independent time courses
spread_kind    'standard_error', 'standard_deviation', 'confidence_interval' or None: what the spreads are.
completion_criterion
               'substrate_gone', 'product_plateau', 'ratio_constant', 'equilibrium_reached', 'other_stated' or None: the state the paper calls complete. Kept for the reviewer.
detection_method
               'nmr', 'chromatography', 'optical', 'mass_spectrometry', 'radiometric', 'other' or None: how the course was followed. Kept for the reviewer.
facts          name -> {'answer', 'source_refs', 'support'}. Names and answer sets in FACTS below. No fact holds text: a controlled answer only.
choice_support name -> support of each plain choice field (spread_kind, completion_criterion, detection_method), None when the field is not stated.
spans          source_ref -> {'locator', 'quote'}: the quoted source span behind each reference the record cites.

A BOUND is not a value. A time given as "more than 18 h" or "less than 10 min" is stored with its number and unit like any other, and the fact completion_time_is_exact says
'no' for it (the same for the reference time and the ratio). The converter never takes a bound as the effect; a bound is recorded, never turned into a point.

Support. Every stated value (an operand with status 'point', a fact whose answer is stated, a choice field) carries 'support', the extraction's fact about how well its quote
supports it: 'direct' (the quote itself states the value or fact), 'implied' (it states it only by implication) or 'about_something_else' (the quote is on the topic but is
really about another measurement or condition). An unavailable operand, an 'unknown' or 'not_applicable' fact and an unstated choice carry None. The grader does not judge it;
the converter does. The constructors take ``support`` and default it to 'direct'; the default is only for forms built by tests that do not go through the extraction (the
extraction always passes the model's answer).
"""

VERSION = 'a105_endpoint_time_course_completion_record_v1'
SUPPORTS = ('direct', 'implied', 'about_something_else')
EXPERIMENT_TYPE = 'endpoint_time_course_completion'
QUANTITIES = ('completion_time', 'completion_time_spread', 'reference_completion_time', 'completion_time_ratio', 'completion_time_ratio_spread', 'sampling_interval',
              'enzyme_loading_test', 'enzyme_loading_reference', 'replicate_count')
PREPARATION_KEYS = ('analyte_preparation_ref', 'immobilized_preparation_ref', 'surface_ref', 'dataset_ref')
SPREAD_KINDS = ('standard_error', 'standard_deviation', 'confidence_interval')
COMPLETION_CRITERIA = ('substrate_gone', 'product_plateau', 'ratio_constant', 'equilibrium_reached', 'other_stated')
DETECTION_METHODS = ('nmr', 'chromatography', 'optical', 'mass_spectrometry', 'radiometric', 'other')
YES_NO = ('yes', 'no', 'unknown', 'not_applicable')
FACTS = {'completion_criterion_stated': YES_NO, 'same_completion_criterion_in_arms': YES_NO, 'samples_stopped_before_analysis': YES_NO, 'no_enzyme_course_done': YES_NO,
         'inactive_enzyme_course_done': YES_NO, 'enzyme_dependence_shown': YES_NO, 'contaminating_activity_examined': YES_NO, 'product_identified_by_standard': YES_NO,
         'substrate_loss_matches_product_gain': YES_NO, 'initial_substrate_determined': YES_NO, 'same_loading_in_arms': YES_NO, 'same_temperature_in_arms': YES_NO,
         'native_substrate': YES_NO, 'purified_enzyme': YES_NO, 'independent_replicates': YES_NO, 'completion_time_is_exact': YES_NO, 'reference_time_is_exact': YES_NO,
         'completion_time_ratio_is_exact': YES_NO, 'conversion_detected_above_control': YES_NO}

TIME_UNITS = ('s', 'min', 'h')
LOADING_UNITS = ('nM', 'uM', 'mg/mL')
# The unit vocabulary of each quantity: the units a record may carry.
UNITS = {'completion_time': TIME_UNITS, 'completion_time_spread': TIME_UNITS, 'reference_completion_time': TIME_UNITS, 'completion_time_ratio': ('fold',),
         'completion_time_ratio_spread': ('fold',), 'sampling_interval': TIME_UNITS, 'enzyme_loading_test': LOADING_UNITS, 'enzyme_loading_reference': LOADING_UNITS,
         'replicate_count': ('count',)}


def point(value, unit, key, refs, native_component=None, support='direct'):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': list(refs), 'origin': 'reported', 'native_component': native_component or key, 'support': support}


def unavailable(unit, key, reason):
    return {'value': None, 'unit': unit, 'status': 'unavailable', 'reason': reason, 'measurement_keys': [], 'source_refs': [], 'origin': 'reported', 'native_component': key, 'support': None}


def fact(answer, refs=(), support='direct'):
    return {'answer': answer, 'source_refs': list(refs), 'support': None if answer in ('unknown', 'not_applicable') else support}
