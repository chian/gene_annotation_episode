"""Quench_flow grader: judges ONE rapid chemical quench-flow enzyme experiment by its own standards.

Hand-built and private to quench_flow. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_quench_flow_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_quench_flow_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(turnover_design and substrate_over_enzyme, first_point_times_rate and last_point_times_rate, time_point_count, burst_per_enzyme,
replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter
judges it. The only arithmetic is the exact change of a unit (nM, seconds, per second) and the forming of the ratios the converter judges.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact product_formed_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw product above its own control. It is recorded in native as 'activity' with its refs and its support (class
decision of 2026-11-21: 'interaction_detected' reads "activity detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, spread_kind, detection_method, the preparations, and turnover_design,
substrate_over_enzyme, first_point_times_rate, last_point_times_rate, time_point_count, burst_per_enzyme, replicate_count,
replicate_independent, activity, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_quench_flow_criteria import (
    PER_SECOND_PER_RATE_UNIT, QUENCH_FLOW_CRITERIA, SECONDS_PER_TIME_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_quench_flow_grade'
CRITERIA = tuple(criterion['id'] for criterion in QUENCH_FLOW_CRITERIA)
ACTIVITY = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact product_formed_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * _SCALES[record['quantities'][name]['unit']]


def _seconds(record, name):
    value = _value(record, name)
    return None if value is None else value * SECONDS_PER_TIME_UNIT[record['quantities'][name]['unit']]


def _per_second(record, name):
    value = _value(record, name)
    return None if value is None else value * PER_SECOND_PER_RATE_UNIT[record['quantities'][name]['unit']]


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


def _zero_time_control(record, native):
    return _one_fact(record, 'zero_time_control')


def _no_enzyme_control(record, native):
    return _one_fact(record, 'no_enzyme_control')


def _quench_efficiency(record, native):
    return _one_fact(record, 'quench_stops_reaction')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'enzyme_dependence_shown')


def _product_identity(record, native):
    return _one_fact(record, 'product_identified')


def _product_calibration(record, native):
    return _one_fact(record, 'product_quantified_against_standard')


def _enzyme_substrate_ratio(record, native):
    single, multiple = record['facts']['single_turnover_conditions'], record['facts']['multiple_turnover_conditions']
    if single['answer'] == 'yes' and multiple['answer'] == 'yes':
        return _result('unknown', 'both_designs_stated', [])
    if single['answer'] != 'yes' and multiple['answer'] != 'yes':
        return _result('unknown', 'turnover_design_not_stated', [])
    enzyme, substrate = _nm(record, 'enzyme_concentration'), _nm(record, 'substrate_concentration')
    if enzyme is None or substrate is None:
        return _result('unknown', 'enzyme_or_substrate_concentration_missing', [])
    native.update({'turnover_design': 'single_turnover' if single['answer'] == 'yes' else 'multiple_turnover', 'substrate_over_enzyme': substrate / enzyme,
                   'ratio_refs': _refs(single if single['answer'] == 'yes' else multiple, record['quantities']['enzyme_concentration'], record['quantities']['substrate_concentration'])})
    return _result('unknown', 'enzyme_ratio_recorded_for_the_sheet', [])


def _time_range(record, native):
    rate, shortest, longest = _per_second(record, 'chemical_rate_constant'), _seconds(record, 'shortest_time'), _seconds(record, 'longest_time')
    if rate is None or (shortest is None and longest is None):
        return _result('unknown', 'rate_constant_or_time_range_missing', [])
    native.update({'first_point_times_rate': None if shortest is None else rate * shortest, 'last_point_times_rate': None if longest is None else rate * longest,
                   'time_range_refs': _refs(*(record['quantities'][n] for n in ('chemical_rate_constant', 'shortest_time', 'longest_time')))})
    return _result('unknown', 'time_range_recorded_for_the_sheet', [])


def _time_course_fit(record, native):
    return _one_fact(record, 'time_course_fitted')


def _time_points(record, native):
    count = _value(record, 'time_point_count')
    if count is None:
        return _result('unknown', 'time_point_count_not_stated', [])
    native.update({'time_point_count': count, 'time_point_refs': _refs(record['quantities']['time_point_count'])})
    return _result('unknown', 'time_point_count_recorded_for_the_sheet', [])


def _active_enzyme_amount(record, native):
    return _one_fact(record, 'active_site_concentration_determined')


def _burst_stoichiometry(record, native):
    single, multiple = record['facts']['single_turnover_conditions'], record['facts']['multiple_turnover_conditions']
    if single['answer'] == 'yes' and multiple['answer'] != 'yes':
        return _result('not_applicable', 'single_turnover_has_no_burst', [])
    per_enzyme = _value(record, 'burst_amplitude_per_enzyme')
    if per_enzyme is not None:
        native.update({'burst_per_enzyme': per_enzyme, 'burst_refs': _refs(record['quantities']['burst_amplitude_per_enzyme'])})
        return _result('unknown', 'burst_amplitude_recorded_for_the_sheet', [])
    amplitude, enzyme = _nm(record, 'burst_amplitude'), _nm(record, 'enzyme_concentration')
    if multiple['answer'] != 'yes' or amplitude is None or enzyme is None:
        return _result('unknown', 'burst_amplitude_not_stated', [])
    native.update({'burst_per_enzyme': amplitude / enzyme, 'burst_refs': _refs(multiple, record['quantities']['burst_amplitude'], record['quantities']['enzyme_concentration'])})
    return _result('unknown', 'burst_amplitude_recorded_for_the_sheet', [])


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


def _native_reaction(record, native):
    return _one_fact(record, 'native_substrate')


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


EVALUATORS = {'zero_time_control': _zero_time_control, 'no_enzyme_control': _no_enzyme_control, 'quench_efficiency': _quench_efficiency, 'enzyme_dependence': _enzyme_dependence,
              'product_identity': _product_identity, 'product_calibration': _product_calibration, 'enzyme_substrate_ratio': _enzyme_substrate_ratio, 'time_range': _time_range,
              'time_course_fit': _time_course_fit, 'time_points': _time_points, 'active_enzyme_amount': _active_enzyme_amount, 'burst_stoichiometry': _burst_stoichiometry,
              'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_quench_flow(record):
    """Grade one rapid chemical quench-flow experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['product_formed_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'detection_method': record['detection_method'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'activity': ACTIVITY.get(detected['answer']), 'activity_refs': list(detected['source_refs']) if detected['answer'] in ACTIVITY else [], 'activity_support': detected['support'],
              'turnover_design': None, 'substrate_over_enzyme': None, 'ratio_refs': [], 'first_point_times_rate': None, 'last_point_times_rate': None, 'time_range_refs': [],
              'time_point_count': None, 'time_point_refs': [], 'burst_per_enzyme': None, 'burst_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, QUENCH_FLOW_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'quench_flow', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
