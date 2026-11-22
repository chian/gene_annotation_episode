"""Transport_ssm_electrophysiology grader: judges ONE solid-supported membrane (SSM) electrophysiology experiment by its own standards.

Hand-built and private to transport_ssm_electrophysiology. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_transport_ssm_electrophysiology_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_transport_ssm_electrophysiology_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(decay_time_value and decay_time_unit, the series count and its two ratios over the Km, sensor_count, preparation_count, each with its refs) and
returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. The specificity control has its own rule (any of three alternative controls done is enough).

A supported or conflicting result always carries support refs (``_result`` refuses to build one without them).

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact transport_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw a current above its own control. It is recorded in native as 'interaction' with its refs and its support (class
decision of 2026-11-22: 'interaction_detected' reads "transport detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series, the two choices (spread_kind, readout) and the preparations, and km_nM,
decay_time_value / decay_time_unit / decay_time_refs, concentration_count, concentration_low_over_km, concentration_high_over_km,
concentration_refs, sensor_count / sensor_independent / sensor_refs, preparation_count / preparation_independent / preparation_refs,
interaction / interaction_refs / interaction_support.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_ssm_electrophysiology_criteria import (
    TRANSPORT_SSM_ELECTROPHYSIOLOGY_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_transport_ssm_electrophysiology_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in TRANSPORT_SSM_ELECTROPHYSIOLOGY_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact transport_detected_above_control
SPECIFICITY_FACTS = ('non_substrate_jump_done', 'blocker_control_done', 'ion_substitution_done')


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


def _empty_liposome_control(record, native):
    return _one_fact(record, 'empty_liposome_sensor_done')


def _buffer_artefact(record, native):
    return _one_fact(record, 'buffer_jump_artefact_subtracted')


def _sensor_quality(record, native):
    return _one_fact(record, 'sensor_capacitance_stated')


def _inactive_protein_control(record, native):
    return _one_fact(record, 'inactive_protein_control_done')


def _electrogenic_stated(record, native):
    return _one_fact(record, 'electrogenic_transport_stated')


def _native_substrate(record, native):
    return _one_fact(record, 'native_substrate')


def _reference_normalization(record, native):
    return _one_fact(record, 'same_sensor_reference_jump')


def _time_resolution(record, native):
    decay = record['quantities']['decay_time']
    if decay['status'] != 'point':
        return _result('unknown', 'decay_time_not_stated', [])
    native.update({'decay_time_value': decay['value'], 'decay_time_unit': decay['unit'], 'decay_time_refs': _refs(decay)})
    return _result('unknown', 'decay_time_recorded_for_the_sheet', [])


def _endpoint_stated(record, native):
    stated = [record['quantities'][name] for name in ('peak_current', 'charge') if record['quantities'][name]['status'] == 'point']
    if not stated:
        return _result('unknown', 'endpoint_quantity_not_stated', [])
    return _result('supported', 'endpoint_quantity_stated', _refs(*stated))


def _solutions_matched(record, native):
    return _one_fact(record, 'solutions_matched_except_substrate')


def _specificity_control(record, native):
    items = [record['facts'][name] for name in SPECIFICITY_FACTS]
    answers = [item['answer'] for item in items]
    if 'yes' in answers:
        return _result('supported', 'specificity_control_stated', _refs(*(item for item in items if item['answer'] == 'yes')))
    stated = [answer for answer in answers if answer != 'not_applicable']
    if not stated:
        return _result('not_applicable', 'fact_not_applicable', [])
    if all(answer == 'no' for answer in stated):
        return _result('conflicting', 'fact_answered_no', _refs(*(item for item in items if item['answer'] == 'no')))
    return _result('unknown', 'fact_unknown', [])


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


def _count_criterion(record, native, key, count_name, fact_name):
    """The sensors and the preparations: a stated count is recorded for the sheet; independence stated as no fails."""
    count = _value(record, count_name)
    independent = record['facts'][fact_name]
    refs = _refs(record['quantities'][count_name], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', key + 's_not_independent', refs)
    if count is None:
        return _result('unknown', key + '_count_or_independence_unknown', [])
    native.update({key + '_count': count, key + '_independent': independent['answer'], key + '_refs': refs})
    return _result('unknown', key + '_count_recorded_for_the_sheet', [])


def _sensors(record, native):
    return _count_criterion(record, native, 'sensor', 'sensor_count', 'independent_sensors')


def _preparations(record, native):
    return _count_criterion(record, native, 'preparation', 'preparation_count', 'independent_preparations')


EVALUATORS = {'empty_liposome_control': _empty_liposome_control, 'buffer_artefact': _buffer_artefact, 'sensor_quality': _sensor_quality,
              'inactive_protein_control': _inactive_protein_control, 'electrogenic_stated': _electrogenic_stated, 'native_substrate': _native_substrate,
              'reference_normalization': _reference_normalization, 'time_resolution': _time_resolution, 'endpoint_stated': _endpoint_stated,
              'solutions_matched': _solutions_matched, 'specificity_control': _specificity_control, 'substrate_range': _substrate_range,
              'sensors': _sensors, 'preparations': _preparations}


def grade_transport_ssm_electrophysiology(record):
    """Grade one solid-supported membrane electrophysiology record. Returns the criterion answers and native values."""
    detected = record['facts']['transport_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'readout': record['readout'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'interaction': INTERACTION.get(detected['answer']), 'interaction_refs': list(detected['source_refs']) if detected['answer'] in INTERACTION else [], 'interaction_support': detected['support'],
              'decay_time_value': None, 'decay_time_unit': None, 'decay_time_refs': [],
              'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None, 'concentration_refs': [],
              'sensor_count': None, 'sensor_independent': None, 'sensor_refs': [], 'preparation_count': None, 'preparation_independent': None, 'preparation_refs': []}
    native['support'] = criterion_supports(record, TRANSPORT_SSM_ELECTROPHYSIOLOGY_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'transport_ssm_electrophysiology', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
