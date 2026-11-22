"""Transport_cell_tracer_uptake grader: judges ONE whole-cell tracer uptake (or efflux) experiment by its own standards.

Hand-built and private to transport_cell_tracer_uptake. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_transport_cell_tracer_uptake_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_transport_cell_tracer_uptake_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(time_window_s, the series count and its two ratios over the Km, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact uptake_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying
whether it saw transport above its own control. It is recorded in native as 'transport' with its refs and its support (class decision of 2026-11-22:
'interaction_detected' reads "transport detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series, the preparations and the two plain choices (spread_kind, rate_basis), and time_window_s,
concentration_count, concentration_low_over_km, concentration_high_over_km, replicate_count, replicate_independent, transport, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_cell_tracer_uptake_criteria import (
    TRANSPORT_CELL_TRACER_UPTAKE_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_transport_cell_tracer_uptake_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in TRANSPORT_CELL_TRACER_UPTAKE_CRITERIA)
TRANSPORT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact uptake_detected_above_control
SECONDS_PER_UNIT = {'s': 1.0, 'min': SECONDS_PER_MINUTE}   # FIXED_BY_DEFINITION: the unit of the uptake interval to seconds


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * _SCALES[record['quantities'][name]['unit']]


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


def _background_controls(record, native):
    items = [record['facts'][name] for name in ('empty_vector_control_done', 'zero_time_control_done')]
    answers = [item['answer'] for item in items]
    if 'yes' in answers:
        return _result('supported', 'background_control_stated', _refs(*(item for item in items if item['answer'] == 'yes')))
    status, reason = _shared_rule(answers)
    return _result(status, reason, _refs(*(item for item in items if item['answer'] == 'no')))


def _expression_confirmed(record, native):
    return _one_fact(record, 'expression_confirmed')


def _cell_integrity(record, native):
    return _one_fact(record, 'viability_checked')


def _initial_rate_regime(record, native):
    linear = record['facts']['linear_interval_shown']
    window = _value(record, 'time_window')
    if linear['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', linear['source_refs'])
    if linear['answer'] == 'yes':
        return _result('supported', 'linear_interval_stated', linear['source_refs'])
    if window is None:
        return _result('unknown', 'rate_regime_not_stated', [])
    native.update({'time_window_s': window * SECONDS_PER_UNIT[record['quantities']['time_window']['unit']], 'time_window_refs': _refs(record['quantities']['time_window'])})
    return _result('unknown', 'time_window_recorded_for_the_sheet', [])


def _substrate_range(record, native):
    km = native['km_nM']
    series = record['concentration_series']
    values = series['value']
    if km is None or values is None:
        return _result('unknown', 'km_or_series_missing', [])
    scale = _SCALES[series['unit']]
    nm = [v * scale for v in values]
    native['concentration_count'] = len(nm)
    native['concentration_low_over_km'] = min(nm) / km
    native['concentration_high_over_km'] = max(nm) / km
    native['concentration_refs'] = _refs(series, record['quantities']['km'])
    return _result('unknown', 'substrate_series_recorded_for_the_sheet', [])


def _competitor_control(record, native):
    return _one_fact(record, 'competitor_control_done')


def _label_identity(record, native):
    return _one_fact(record, 'label_identity_shown')


def _energy_dependence(record, native):
    return _one_fact(record, 'energy_control_done')


def _specific_activity_stated(record, native):
    if _value(record, 'specific_activity') is None:
        return _result('unknown', 'specific_activity_not_stated', [])
    return _result('supported', 'specific_activity_stated', _refs(record['quantities']['specific_activity']))


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


EVALUATORS = {'background_controls': _background_controls, 'expression_confirmed': _expression_confirmed, 'cell_integrity': _cell_integrity,
              'initial_rate_regime': _initial_rate_regime, 'substrate_range': _substrate_range, 'competitor_control': _competitor_control,
              'label_identity': _label_identity, 'energy_dependence': _energy_dependence, 'specific_activity_stated': _specific_activity_stated,
              'native_substrate': _native_substrate, 'replicates': _replicates}


def grade_transport_cell_tracer_uptake(record):
    """Grade one whole-cell tracer uptake record. Returns the criterion answers and native values."""
    detected = record['facts']['uptake_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'rate_basis': record['rate_basis'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'transport': TRANSPORT.get(detected['answer']), 'transport_refs': list(detected['source_refs']) if detected['answer'] in TRANSPORT else [], 'transport_support': detected['support'],
              'time_window_s': None, 'time_window_refs': [], 'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None,
              'concentration_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, TRANSPORT_CELL_TRACER_UPTAKE_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'transport_cell_tracer_uptake', 'experiment_ref': record['experiment_ref'],
            'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()},
            'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
