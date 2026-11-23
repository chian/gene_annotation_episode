"""Transport_oocyte_two_electrode grader: judges ONE two-electrode voltage clamp experiment on Xenopus oocytes by its own standards. DRAFT of 2026-11-22, owner to correct.

Hand-built and private to transport_oocyte_two_electrode. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_transport_oocyte_two_electrode_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_transport_oocyte_two_electrode_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(current_over_control, current_nA, the series count and its two ratios over the Km, oocyte_count, batch_count, each with its refs) and returns 'unknown'
with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact transport_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw a substrate-induced current above its own control. It is recorded in native as 'transport' with its refs and its support (class
decision of 2026-11-22: 'interaction_detected' reads "transport detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series, the preparations, spread_kind, current_direction, and current_over_control, current_nA,
concentration_count, concentration_low_over_km, concentration_high_over_km, oocyte_count, batch_count, batch_independent, transport, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_oocyte_two_electrode_criteria import (
    NA_PER_UNIT, TRANSPORT_OOCYTE_TWO_ELECTRODE_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_transport_oocyte_two_electrode_grade'
CRITERIA = tuple(criterion['id'] for criterion in TRANSPORT_OOCYTE_TWO_ELECTRODE_CRITERIA)
TRANSPORT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact transport_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * _SCALES[record['quantities'][name]['unit']]


def _na(record, name):
    value = _value(record, name)
    return None if value is None else value * NA_PER_UNIT[record['quantities'][name]['unit']]


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


def _uninjected_control(record, native):
    return _one_fact(record, 'uninjected_control_done')


def _background_current(record, native):
    none = record['facts']['control_shows_no_substrate_current']
    if none['answer'] == 'yes':
        return _result('supported', 'control_shows_no_current', none['source_refs'])
    current, control = _na(record, 'current'), _na(record, 'control_current')
    if current is None or control is None:
        return _result('unknown', 'control_current_not_comparable', [])
    native.update({'current_over_control': current / control, 'control_refs': _refs(record['quantities']['current'], record['quantities']['control_current'])})
    return _result('unknown', 'control_current_recorded_for_the_sheet', [])


def _same_oocyte_baseline(record, native):
    return _one_fact(record, 'same_oocyte_baseline_done')


def _leak_subtracted(record, native):
    return _one_fact(record, 'leak_subtracted')


def _non_substrate_control(record, native):
    return _one_fact(record, 'non_substrate_gives_no_current')


def _ion_dependence(record, native):
    return _one_fact(record, 'ion_dependence_shown')


def _substrate_uptake_confirmed(record, native):
    return _one_fact(record, 'substrate_uptake_confirmed')


def _inactive_mutant_control(record, native):
    return _one_fact(record, 'inactive_mutant_gives_no_current')


def _expression_confirmed(record, native):
    return _one_fact(record, 'expression_confirmed')


def _clamp_conditions(record, native):
    voltage = record['facts']['holding_voltage_stated']
    if voltage['answer'] != 'yes' or _value(record, 'substrate_concentration') is None:
        return _result('unknown', 'holding_voltage_or_substrate_concentration_missing', [])
    return _result('supported', 'holding_voltage_and_substrate_concentration_stated', _refs(voltage, record['quantities']['substrate_concentration']))


def _clamp_current_range(record, native):
    current = _na(record, 'current')
    if current is None:
        return _result('unknown', 'current_not_stated', [])
    native.update({'current_nA': current, 'current_refs': _refs(record['quantities']['current'])})
    return _result('unknown', 'current_recorded_for_the_sheet', [])


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


def _replicates(record, native):
    count = _value(record, 'batch_count')
    independent = record['facts']['independent_batches']
    refs = _refs(record['quantities']['batch_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'batches_not_independent', refs)
    if count is None:
        return _result('unknown', 'batch_count_or_independence_unknown', [])
    native.update({'batch_count': count, 'batch_independent': independent['answer'], 'batch_refs': refs})
    return _result('unknown', 'batch_count_recorded_for_the_sheet', [])


def _oocytes_recorded(record, native):
    count = _value(record, 'oocyte_count')
    if count is None:
        return _result('unknown', 'oocyte_count_not_stated', [])
    native.update({'oocyte_count': count, 'oocyte_refs': _refs(record['quantities']['oocyte_count'])})
    return _result('unknown', 'oocyte_count_recorded_for_the_sheet', [])


def _native_substrate(record, native):
    return _one_fact(record, 'native_substrate')


EVALUATORS = {'uninjected_control': _uninjected_control, 'background_current': _background_current, 'same_oocyte_baseline': _same_oocyte_baseline,
              'leak_subtracted': _leak_subtracted, 'non_substrate_control': _non_substrate_control, 'ion_dependence': _ion_dependence,
              'substrate_uptake_confirmed': _substrate_uptake_confirmed, 'inactive_mutant_control': _inactive_mutant_control,
              'expression_confirmed': _expression_confirmed, 'clamp_conditions': _clamp_conditions, 'clamp_current_range': _clamp_current_range,
              'substrate_range': _substrate_range, 'replicates': _replicates, 'oocytes_recorded': _oocytes_recorded, 'native_substrate': _native_substrate}


def grade_transport_oocyte_two_electrode(record):
    """Grade one two-electrode voltage clamp experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['transport_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'current_direction': record['current_direction'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'transport': TRANSPORT.get(detected['answer']), 'transport_refs': list(detected['source_refs']) if detected['answer'] in TRANSPORT else [], 'transport_support': detected['support'],
              'current_over_control': None, 'control_refs': [], 'current_nA': None, 'current_refs': [], 'concentration_count': None, 'concentration_low_over_km': None,
              'concentration_high_over_km': None, 'concentration_refs': [], 'oocyte_count': None, 'oocyte_refs': [], 'batch_count': None, 'batch_independent': None, 'batch_refs': []}
    native['support'] = criterion_supports(record, TRANSPORT_OOCYTE_TWO_ELECTRODE_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'transport_oocyte_two_electrode', 'experiment_ref': record['experiment_ref'],
            'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()},
            'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
