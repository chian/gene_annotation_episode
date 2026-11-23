"""Transport_medium_analysis grader: judges ONE medium-analysis transport experiment by its own standards.

DRAFT 2026-11-22 (owner to correct). Hand-built and private to transport_medium_analysis. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_transport_medium_analysis_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in
literature_transport_medium_analysis_criteria.py (the single source). This file only evaluates them: one short function per criterion, in the
same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(moved_percent, the sampling-time count with the zero-time answer, the separation delay over the interval, replicate_count, each with its refs)
and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact transport_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the
paper itself saying whether it saw transport above its own control. It is recorded in native as 'transport' with its refs and its support
(class decision: 'interaction_detected' reads "transport detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the sampling times and the preparations, the three plain choices, and moved_percent,
time_point_count, zero_time_sample, separation_delay_over_interval, replicate_count, replicate_independent, transport, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_medium_analysis_criteria import (
    SECONDS_PER_TIME_UNIT, TRANSPORT_MEDIUM_ANALYSIS_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_transport_medium_analysis_grade'
CRITERIA = tuple(criterion['id'] for criterion in TRANSPORT_MEDIUM_ANALYSIS_CRITERIA)
TRANSPORT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact transport_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _seconds(record, name):
    value = _value(record, name)
    return None if value is None else value * SECONDS_PER_TIME_UNIT[record['quantities'][name]['unit']]


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


def _cell_free_control(record, native):
    return _one_fact(record, 'cell_free_control_done')


def _zero_time_sample(record, native):
    return _one_fact(record, 'zero_time_sample_taken')


def _control_strain(record, native):
    return _one_fact(record, 'empty_vector_control_done')


def _expression_confirmed(record, native):
    return _one_fact(record, 'expression_confirmed')


def _calibration_in_medium(record, native):
    return _one_fact(record, 'calibration_in_medium')


def _internal_standard(record, native):
    return _one_fact(record, 'internal_standard_used')


def _initial_rate_regime(record, native):
    linear = record['facts']['linear_time_course']
    moved = _value(record, 'substrate_moved_percent')
    refs = _refs(record['quantities']['substrate_moved_percent'], linear)
    if linear['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if moved is not None:
        native.update({'moved_percent': moved, 'moved_refs': refs})
        return _result('unknown', 'moved_recorded_for_the_sheet', [])
    if linear['answer'] == 'yes':
        return _result('supported', 'linear_time_course_stated', refs)
    return _result('unknown', 'rate_regime_not_stated', [])


def _time_points(record, native):
    series = record['sampling_times']
    if series['value'] is None:
        return _result('unknown', 'sampling_times_not_stated', [])
    zero = record['facts']['zero_time_sample_taken']
    native.update({'time_point_count': len(set(series['value'])), 'zero_time_sample': zero['answer'], 'time_points_refs': _refs(series, zero)})
    return _result('unknown', 'time_points_recorded_for_the_sheet', [])


def _separation_timing(record, native):
    immediate = record['facts']['immediate_separation']
    delay, interval = _seconds(record, 'separation_delay'), _seconds(record, 'interval')
    refs = _refs(record['quantities']['separation_delay'], record['quantities']['interval'], immediate)
    if immediate['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if delay is not None and interval is not None:
        native.update({'separation_delay_over_interval': delay / interval, 'separation_refs': refs})
        return _result('unknown', 'separation_recorded_for_the_sheet', [])
    if immediate['answer'] == 'yes':
        return _result('supported', 'immediate_separation_stated', refs)
    return _result('unknown', 'separation_not_stated', [])


def _substrate_identity(record, native):
    return _one_fact(record, 'substrate_identity_confirmed')


def _metabolism_excluded(record, native):
    return _one_fact(record, 'substrate_metabolism_excluded')


def _reuptake_excluded(record, native):
    return _one_fact(record, 'reuptake_excluded')


def _lysis_excluded(record, native):
    return _one_fact(record, 'lysis_excluded')


def _energy_source(record, native):
    return _one_fact(record, 'energy_source_provided')


def _native_substrate(record, native):
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


EVALUATORS = {'cell_free_control': _cell_free_control, 'zero_time_sample': _zero_time_sample, 'control_strain': _control_strain, 'expression_confirmed': _expression_confirmed,
              'calibration_in_medium': _calibration_in_medium, 'internal_standard': _internal_standard, 'initial_rate_regime': _initial_rate_regime, 'time_points': _time_points,
              'separation_timing': _separation_timing, 'substrate_identity': _substrate_identity, 'metabolism_excluded': _metabolism_excluded, 'reuptake_excluded': _reuptake_excluded,
              'lysis_excluded': _lysis_excluded, 'energy_source': _energy_source, 'native_substrate': _native_substrate, 'replicates': _replicates}


def grade_transport_medium_analysis(record):
    """Grade one medium-analysis transport experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['transport_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'rate_basis': record['rate_basis'], 'analytical_method': record['analytical_method'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'sampling_times': dict(record['sampling_times']),
              'transport': TRANSPORT.get(detected['answer']), 'transport_refs': list(detected['source_refs']) if detected['answer'] in TRANSPORT else [], 'transport_support': detected['support'],
              'moved_percent': None, 'moved_refs': [], 'time_point_count': None, 'zero_time_sample': None, 'time_points_refs': [], 'separation_delay_over_interval': None, 'separation_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, TRANSPORT_MEDIUM_ANALYSIS_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'transport_medium_analysis', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
