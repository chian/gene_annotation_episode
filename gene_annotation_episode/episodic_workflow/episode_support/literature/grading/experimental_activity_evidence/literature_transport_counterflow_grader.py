"""Transport_counterflow grader: judges ONE counterflow (exchange, trans-stimulation) experiment by its own standards.

Hand-built and private to transport_counterflow. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_transport_counterflow_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_transport_counterflow_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(preload_over_label, the series count and its two ratios over the Km, replicate_count, each with its refs) and returns 'unknown' with a reason
ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact transport_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw counterflow (trans-stimulation or an overshoot) above its own baseline. It is recorded in native as 'transport' with its refs
and its support (class decision of 2026-11-22: 'interaction_detected' reads "transport detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series, the preparations and the plain choice spread_kind, and preload_over_label,
concentration_count, concentration_low_over_km, concentration_high_over_km, replicate_count, replicate_independent, transport, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_counterflow_criteria import (
    TRANSPORT_COUNTERFLOW_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_transport_counterflow_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in TRANSPORT_COUNTERFLOW_CRITERIA)
TRANSPORT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact transport_detected_above_control
NM_PER_UNIT = {'nM': 1.0, 'uM': 1.0e3, 'mM': 1.0e6, 'M': 1.0e9}   # FIXED_BY_DEFINITION: the unit of a concentration to nM


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * NM_PER_UNIT[record['quantities'][name]['unit']]


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


def _non_preloaded_baseline(record, native):
    return _one_fact(record, 'non_preloaded_baseline_done')


def _protein_free_control(record, native):
    return _one_fact(record, 'protein_free_control_done')


def _non_substrate_preload(record, native):
    return _one_fact(record, 'non_substrate_preload_control_done')


def _label_identity(record, native):
    return _one_fact(record, 'label_identity_shown')


def _preload_verified(record, native):
    return _one_fact(record, 'preload_verified')


def _preload_over_label(record, native):
    preload, label = _nm(record, 'preload_concentration'), _nm(record, 'label_concentration')
    if preload is None or label is None:
        return _result('unknown', 'preload_or_label_concentration_missing', [])
    native['preload_over_label'] = preload / label
    native['preload_ratio_refs'] = _refs(record['quantities']['preload_concentration'], record['quantities']['label_concentration'])
    return _result('unknown', 'preload_ratio_recorded_for_the_sheet', [])


def _preload_retained(record, native):
    return _one_fact(record, 'preload_retained')


def _uptake_endpoint(record, native):
    items = [record['facts'][name] for name in ('equilibrium_reached', 'linear_interval_shown')]
    answers = [item['answer'] for item in items]
    if 'yes' in answers:
        return _result('supported', 'uptake_endpoint_stated', _refs(*(item for item in items if item['answer'] == 'yes')))
    status, reason = _shared_rule(answers)
    return _result(status, reason, _refs(*(item for item in items if item['answer'] == 'no')))


def _substrate_range(record, native):
    km = native['km_nM']
    series = record['concentration_series']
    values = series['value']
    if km is None or values is None:
        return _result('unknown', 'km_or_series_missing', [])
    scale = NM_PER_UNIT[series['unit']]
    nm = [v * scale for v in values]
    native['concentration_count'] = len(nm)
    native['concentration_low_over_km'] = min(nm) / km
    native['concentration_high_over_km'] = max(nm) / km
    native['concentration_refs'] = _refs(series, record['quantities']['km'])
    return _result('unknown', 'substrate_series_recorded_for_the_sheet', [])


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


EVALUATORS = {'non_preloaded_baseline': _non_preloaded_baseline, 'protein_free_control': _protein_free_control, 'non_substrate_preload': _non_substrate_preload,
              'label_identity': _label_identity, 'preload_verified': _preload_verified, 'preload_over_label': _preload_over_label, 'preload_retained': _preload_retained,
              'uptake_endpoint': _uptake_endpoint, 'substrate_range': _substrate_range, 'native_substrate': _native_substrate, 'replicates': _replicates}


def grade_transport_counterflow(record):
    """Grade one counterflow record. Returns the criterion answers and native values."""
    detected = record['facts']['transport_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'transport': TRANSPORT.get(detected['answer']), 'transport_refs': list(detected['source_refs']) if detected['answer'] in TRANSPORT else [], 'transport_support': detected['support'],
              'preload_over_label': None, 'preload_ratio_refs': [], 'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None,
              'concentration_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, TRANSPORT_COUNTERFLOW_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'transport_counterflow', 'experiment_ref': record['experiment_ref'],
            'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()},
            'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
