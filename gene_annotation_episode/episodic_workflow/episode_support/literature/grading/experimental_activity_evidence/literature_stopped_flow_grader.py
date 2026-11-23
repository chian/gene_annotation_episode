"""Stopped_flow grader: judges ONE stopped-flow rapid-mixing enzyme experiment by its own standards.

DRAFT of 2026-11-22 for the owner to correct. Hand-built and private to stopped_flow, copied in structure from the spectro_direct grader.
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_stopped_flow_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_stopped_flow_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(dead_time_s with fastest_rate_per_s, enzyme_over_substrate, burst_per_site, the series count and its two ratios over the half-saturation
concentration, shots_averaged, replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and
no refs; the converter judges it. The only numbers it uses are the unit conversions fixed by definition that the criteria file declares.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. The one exception is enzyme_excess: there a stated 'no' is a multiple-turnover design, not a
failure, and the criterion is not applicable.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact activity_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw the reaction above its own control. It is recorded in native as 'activity' with its refs and its support (class
decision of 2026-11-21: 'interaction_detected' reads "activity detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series and the preparations, spread_kind, and dead_time_s, fastest_rate_per_s,
enzyme_over_substrate, burst_per_site, concentration_count, concentration_low_over_half, concentration_high_over_half, shots_averaged,
replicate_count, replicate_independent, activity, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_stopped_flow_criteria import (
    PER_SECOND, PER_SITE_UNIT, SECONDS, STOPPED_FLOW_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_stopped_flow_grade'
CRITERIA = tuple(criterion['id'] for criterion in STOPPED_FLOW_CRITERIA)
ACTIVITY = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact activity_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * _SCALES[record['quantities'][name]['unit']]


def _per_second(record, name):
    value = _value(record, name)
    return None if value is None else value * PER_SECOND[record['quantities'][name]['unit']]


def _seconds(record, name):
    value = _value(record, name)
    return None if value is None else value * SECONDS[record['quantities'][name]['unit']]


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


def _spontaneous_reaction_control(record, native):
    names = ('no_enzyme_control', 'inactive_enzyme_control')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'spontaneous_reaction_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _enzyme_only_signal(record, native):
    return _one_fact(record, 'no_substrate_control')


def _phase_assignment(record, native):
    return _one_fact(record, 'phase_assigned_to_chemical_step')


def _product_identity(record, native):
    return _one_fact(record, 'product_identified')


def _dead_time_coverage(record, native):
    dead_time = _seconds(record, 'dead_time')
    rates = [rate for rate in (_per_second(record, 'single_turnover_rate'), _per_second(record, 'observed_rate_constant')) if rate is not None]
    if dead_time is None or not rates:
        return _result('unknown', 'dead_time_or_rate_missing', [])
    native.update({'dead_time_s': dead_time, 'fastest_rate_per_s': max(rates),
                   'dead_time_refs': _refs(*(record['quantities'][n] for n in ('dead_time', 'single_turnover_rate', 'observed_rate_constant')))})
    return _result('unknown', 'dead_time_recorded_for_the_sheet', [])


def _enzyme_excess(record, native):
    single = record['facts']['single_turnover_conditions']
    if single['answer'] == 'no':
        return _result('not_applicable', 'multiple_turnover_stated', [])
    if single['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    if single['answer'] == 'unknown':
        return _result('unknown', 'single_turnover_not_stated', [])
    enzyme, substrate = _nm(record, 'enzyme_concentration'), _nm(record, 'substrate_concentration')
    if enzyme is None or substrate is None:
        return _result('supported', 'single_turnover_stated', _refs(single))
    native['enzyme_over_substrate'] = enzyme / substrate
    native['enzyme_excess_refs'] = _refs(single, record['quantities']['enzyme_concentration'], record['quantities']['substrate_concentration'])
    return _result('unknown', 'enzyme_excess_recorded_for_the_sheet', [])


def _substrate_range(record, native):
    half = native['half_saturation_nM']
    series = record['concentration_series']
    values = series['value']
    if half is None or values is None:
        return _result('unknown', 'half_saturation_or_series_missing', [])
    scale = _SCALES[series['unit']]
    nm = [v * scale for v in values]
    native['concentration_count'] = len(nm)
    native['concentration_low_over_half'] = min(nm) / half
    native['concentration_high_over_half'] = max(nm) / half
    native['concentration_refs'] = _refs(series, record['quantities']['half_saturation_concentration'])
    return _result('unknown', 'substrate_series_recorded_for_the_sheet', [])


def _active_enzyme_amount(record, native):
    return _one_fact(record, 'active_site_concentration_determined')


def _burst_amplitude(record, native):
    burst = record['quantities']['burst_amplitude']
    if burst['status'] != 'point':
        return _result('unknown', 'burst_amplitude_not_stated', [])
    if burst['unit'] == PER_SITE_UNIT:
        native.update({'burst_per_site': burst['value'], 'burst_refs': _refs(burst)})
        return _result('unknown', 'burst_amplitude_recorded_for_the_sheet', [])
    enzyme = _nm(record, 'enzyme_concentration')
    if enzyme is None:
        return _result('unknown', 'burst_amplitude_needs_enzyme_concentration', [])
    native.update({'burst_per_site': burst['value'] * _SCALES[burst['unit']] / enzyme, 'burst_refs': _refs(burst, record['quantities']['enzyme_concentration'])})
    return _result('unknown', 'burst_amplitude_recorded_for_the_sheet', [])


def _shots_averaged(record, native):
    shots = _value(record, 'shots_averaged')
    if shots is None:
        return _result('unknown', 'shots_averaged_not_stated', [])
    native.update({'shots_averaged': shots, 'shots_refs': _refs(record['quantities']['shots_averaged'])})
    return _result('unknown', 'shots_recorded_for_the_sheet', [])


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


EVALUATORS = {'spontaneous_reaction_control': _spontaneous_reaction_control, 'enzyme_only_signal': _enzyme_only_signal, 'phase_assignment': _phase_assignment,
              'product_identity': _product_identity, 'dead_time_coverage': _dead_time_coverage, 'enzyme_excess': _enzyme_excess, 'substrate_range': _substrate_range,
              'active_enzyme_amount': _active_enzyme_amount, 'burst_amplitude': _burst_amplitude, 'shots_averaged': _shots_averaged, 'replicates': _replicates,
              'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_stopped_flow(record):
    """Grade one stopped-flow experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['activity_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'half_saturation_nM': _nm(record, 'half_saturation_concentration'),
              'activity': ACTIVITY.get(detected['answer']), 'activity_refs': list(detected['source_refs']) if detected['answer'] in ACTIVITY else [], 'activity_support': detected['support'],
              'dead_time_s': None, 'fastest_rate_per_s': None, 'dead_time_refs': [], 'enzyme_over_substrate': None, 'enzyme_excess_refs': [], 'concentration_count': None, 'concentration_low_over_half': None,
              'concentration_high_over_half': None, 'concentration_refs': [], 'burst_per_site': None, 'burst_refs': [], 'shots_averaged': None, 'shots_refs': [], 'replicate_count': None,
              'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, STOPPED_FLOW_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'stopped_flow', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
