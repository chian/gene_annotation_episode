"""Endpoint_time_course_completion grader: judges ONE sampled reaction followed to a stated completion or equilibrium by its own standards.

Hand-built and private to endpoint_time_course_completion (DRAFT 2026-11-22, nothing run). Deterministic; no model call, no store access.
Input: the record of one time course (forms/.../literature_endpoint_time_course_completion_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_endpoint_time_course_completion_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(sampling_interval_over_time, loading_fold, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact conversion_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying whether it saw
conversion above its own control. It is recorded in native as 'conversion' with its refs and its support (class decision of 2026-11-22: 'interaction_detected' reads
"conversion detected"). It is only used by the converter when no effect can be filled (no exactly stated time or ratio).

Native values retained: every record quantity as given, every fact as given (the converter reads the three exactness facts, the matched-endpoint fact and their supports there),
the preparations, spread_kind, completion_criterion, detection_method, and completion_min, reference_min, sampling_interval_min (the stated times in minutes, exact unit
conversion), reference_over_completion (the reference time over the test time, both as stated, with its refs; it is a number the grader computes from two stated numbers and does
not judge: whether it may be used as a ratio is the converter's decision), sampling_interval_over_time, loading_fold, replicate_count, replicate_independent, conversion, each
with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_time_course_completion_criteria import (
    ENDPOINT_TIME_COURSE_COMPLETION_CRITERIA, LOADING_SCALE, MIN_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_endpoint_time_course_completion_grade'
CRITERIA = tuple(criterion['id'] for criterion in ENDPOINT_TIME_COURSE_COMPLETION_CRITERIA)
CONVERSION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact conversion_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _minutes(record, name):
    value = _value(record, name)
    return None if value is None else value * MIN_PER_UNIT[record['quantities'][name]['unit']]


def _loading(record, name):
    """(kind, amount in the kind's base unit) of a stated loading, or None."""
    value = _value(record, name)
    if value is None:
        return None
    kind, scale = LOADING_SCALE[record['quantities'][name]['unit']]
    return kind, value * scale


def _refs(*items):
    refs = []
    for item in items:
        refs += item['source_refs']
    return list(dict.fromkeys(refs))


def _shared_rule(answers):
    if 'no' in answers:
        return 'conflicting', 'fact_answered_no'
    if 'unknown' in answers:
        return 'unknown', 'fact_unknown'
    if all(a == 'not_applicable' for a in answers):
        return 'not_applicable', 'fact_not_applicable'
    return 'supported', 'facts_answered_yes'


def _result(status, reason, refs):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError(f'a {status} result needs support refs: {reason}')
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _completion_criterion(record, native):
    return _one_fact(record, 'completion_criterion_stated')


def _matched_endpoint(record, native):
    return _one_fact(record, 'same_completion_criterion_in_arms')


def _samples_stopped(record, native):
    return _one_fact(record, 'samples_stopped_before_analysis')


def _sampling_resolution(record, native):
    time, interval = native['completion_min'], native['sampling_interval_min']
    if time is None or interval is None:
        return _result('unknown', 'sampling_interval_or_time_missing', [])
    native.update({'sampling_interval_over_time': interval / time, 'sampling_refs': _refs(record['quantities']['completion_time'], record['quantities']['sampling_interval'])})
    return _result('unknown', 'sampling_recorded_for_the_sheet', [])


def _spontaneous_course_control(record, native):
    names = ('no_enzyme_course_done', 'inactive_enzyme_course_done')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'spontaneous_course_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _enzyme_dependence(record, native):
    return _one_fact(record, 'enzyme_dependence_shown')


def _contaminating_activity(record, native):
    return _one_fact(record, 'contaminating_activity_examined')


def _product_identity(record, native):
    return _one_fact(record, 'product_identified_by_standard')


def _mass_balance(record, native):
    return _one_fact(record, 'substrate_loss_matches_product_gain')


def _initial_substrate(record, native):
    return _one_fact(record, 'initial_substrate_determined')


def _matched_loading(record, native):
    same = record['facts']['same_loading_in_arms']
    if same['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', same['source_refs'])
    test, reference = _loading(record, 'enzyme_loading_test'), _loading(record, 'enzyme_loading_reference')
    if test is not None and reference is not None and test[0] == reference[0]:
        native.update({'loading_fold': max(test[1] / reference[1], reference[1] / test[1]), 'loading_refs': _refs(record['quantities']['enzyme_loading_test'], record['quantities']['enzyme_loading_reference'])})
        return _result('unknown', 'loading_recorded_for_the_sheet', [])
    return _one_fact(record, 'same_loading_in_arms')


def _matched_temperature(record, native):
    return _one_fact(record, 'same_temperature_in_arms')


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


def _native_reaction(record, native):
    return _one_fact(record, 'native_substrate')


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_replicates']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


EVALUATORS = {'completion_criterion': _completion_criterion, 'matched_endpoint': _matched_endpoint, 'samples_stopped': _samples_stopped, 'sampling_resolution': _sampling_resolution,
              'spontaneous_course_control': _spontaneous_course_control, 'enzyme_dependence': _enzyme_dependence, 'contaminating_activity': _contaminating_activity,
              'product_identity': _product_identity, 'mass_balance': _mass_balance, 'initial_substrate': _initial_substrate, 'matched_loading': _matched_loading,
              'matched_temperature': _matched_temperature, 'purified_enzyme': _purified_enzyme, 'native_reaction': _native_reaction, 'replicates': _replicates}


def grade_endpoint_time_course_completion(record):
    """Grade one sampled time course followed to a stated completion or equilibrium. Returns the criterion answers and native values."""
    detected = record['facts']['conversion_detected_above_control']
    completion, reference = _minutes(record, 'completion_time'), _minutes(record, 'reference_completion_time')
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'completion_criterion': record['completion_criterion'], 'detection_method': record['detection_method'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'facts': {name: dict(item) for name, item in record['facts'].items()},
              'completion_min': completion, 'reference_min': reference, 'sampling_interval_min': _minutes(record, 'sampling_interval'),
              'reference_over_completion': None if completion is None or reference is None else reference / completion,
              'ratio_refs': [] if completion is None or reference is None else _refs(record['quantities']['completion_time'], record['quantities']['reference_completion_time']),
              'conversion': CONVERSION.get(detected['answer']), 'conversion_refs': list(detected['source_refs']) if detected['answer'] in CONVERSION else [], 'conversion_support': detected['support'],
              'sampling_interval_over_time': None, 'sampling_refs': [], 'loading_fold': None, 'loading_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ENDPOINT_TIME_COURSE_COMPLETION_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'endpoint_time_course_completion', 'experiment_ref': record['experiment_ref'],
            'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()},
            'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
