"""Separation_band grader: judges ONE gel or thin-layer separation assay of an enzyme reaction by its own standards.

DRAFT (2026-11-22). Hand-built and private to separation_band. Deterministic; no model call, no store access.
Input: the record of one assay (forms/.../literature_separation_band_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_separation_band_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(consumed_percent, time_point_count, enzyme_over_substrate, the series count and its two ratios over the Km, replicate_count, each with
its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact activity_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw product above its own control. It is recorded in native as 'activity' with its refs and its support (class
decision of 2026-11-21: 'interaction_detected' reads "activity detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series and the preparations, spread_kind, and consumed_percent, time_point_count,
enzyme_over_substrate, concentration_count, concentration_low_over_km, concentration_high_over_km, replicate_count, replicate_independent,
activity, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_separation_band_criteria import SEPARATION_BAND_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_separation_band_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in SEPARATION_BAND_CRITERIA)
ACTIVITY = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact activity_detected_above_control


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


def _no_enzyme_lane(record, native):
    return _one_fact(record, 'no_enzyme_control')


def _catalytic_mutant_lane(record, native):
    return _one_fact(record, 'inactive_enzyme_control')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'rate_proportional_to_enzyme')


def _product_identity(record, native):
    return _one_fact(record, 'product_marker_run')


def _signal_linearity(record, native):
    return _one_fact(record, 'densitometry_in_linear_range')


def _lane_total_denominator(record, native):
    return _one_fact(record, 'conversion_over_lane_total')


def _initial_rate_regime(record, native):
    linear = record['facts']['linear_time_course']
    consumed = _value(record, 'substrate_converted_percent')
    refs = _refs(record['quantities']['substrate_converted_percent'], linear)
    if linear['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if consumed is not None:
        native.update({'consumed_percent': consumed, 'consumed_refs': refs})
        return _result('unknown', 'consumed_recorded_for_the_sheet', [])
    if linear['answer'] == 'yes':
        return _result('supported', 'linear_time_course_stated', refs)
    return _result('unknown', 'rate_regime_not_stated', [])


def _time_course_points(record, native):
    count = _value(record, 'time_point_count')
    if count is None:
        return _result('unknown', 'time_points_not_stated', [])
    native.update({'time_point_count': count, 'time_point_refs': _refs(record['quantities']['time_point_count'])})
    return _result('unknown', 'time_points_recorded_for_the_sheet', [])


def _reaction_stopped(record, native):
    return _one_fact(record, 'reaction_stopped_at_time_points')


def _enzyme_substrate_ratio(record, native):
    enzyme, substrate = _nm(record, 'enzyme_concentration'), _nm(record, 'substrate_concentration')
    if enzyme is None or substrate is None:
        return _result('unknown', 'enzyme_or_substrate_missing', [])
    native['enzyme_over_substrate'] = enzyme / substrate
    native['enzyme_ratio_refs'] = _refs(*(record['quantities'][n] for n in ('enzyme_concentration', 'substrate_concentration')))
    return _result('unknown', 'enzyme_ratio_recorded_for_the_sheet', [])


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


def _active_enzyme_amount(record, native):
    return _one_fact(record, 'active_site_concentration_determined')


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


EVALUATORS = {'no_enzyme_lane': _no_enzyme_lane, 'catalytic_mutant_lane': _catalytic_mutant_lane, 'enzyme_dependence': _enzyme_dependence,
              'product_identity': _product_identity, 'signal_linearity': _signal_linearity, 'lane_total_denominator': _lane_total_denominator,
              'initial_rate_regime': _initial_rate_regime, 'time_course_points': _time_course_points, 'reaction_stopped': _reaction_stopped,
              'enzyme_substrate_ratio': _enzyme_substrate_ratio, 'substrate_range': _substrate_range,
              'active_enzyme_amount': _active_enzyme_amount, 'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_separation_band(record):
    """Grade one gel or thin-layer separation assay record. Returns the criterion answers and native values."""
    detected = record['facts']['activity_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'activity': ACTIVITY.get(detected['answer']), 'activity_refs': list(detected['source_refs']) if detected['answer'] in ACTIVITY else [], 'activity_support': detected['support'],
              'consumed_percent': None, 'consumed_refs': [], 'time_point_count': None, 'time_point_refs': [], 'enzyme_over_substrate': None, 'enzyme_ratio_refs': [],
              'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None, 'concentration_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, SEPARATION_BAND_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'separation_band', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
