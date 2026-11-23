"""Nmr_timecourse grader: judges ONE real-time NMR progress-curve enzyme assay by its own standards.

Hand-built and private to nmr_timecourse. Deterministic; no model call, no store access.
Input: the record of one assay (forms/.../literature_nmr_timecourse_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_nmr_timecourse_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(consumed_percent, enzyme_over_substrate_plus_km, the series count and its two ratios over the Km, signal_to_noise, relaxation_over_t1,
time_point_count, replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs;
the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact activity_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw activity above its own control. It is recorded in native as 'activity' with its refs and its support (class
decision of 2026-11-21: 'interaction_detected' reads "activity detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series, the preparations, spread_kind and nucleus, and consumed_percent,
enzyme_over_substrate_plus_km, concentration_count, concentration_low_over_km, concentration_high_over_km, signal_to_noise, relaxation_over_t1,
time_point_count, replicate_count, replicate_independent, activity, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_nmr_timecourse_criteria import NMR_TIMECOURSE_CRITERIA, S_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_nmr_timecourse_grade'
CRITERIA = tuple(criterion['id'] for criterion in NMR_TIMECOURSE_CRITERIA)
ACTIVITY = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact activity_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * _SCALES[record['quantities'][name]['unit']]


def _seconds(record, name):
    value = _value(record, name)
    return None if value is None else value * S_PER_UNIT[record['quantities'][name]['unit']]


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
    items = [record['facts'][n] for n in ('no_enzyme_control', 'inactive_enzyme_control')]
    answers = [item['answer'] for item in items]
    if 'yes' in answers:
        return _result('supported', 'spontaneous_reaction_control_stated', _refs(*(i for i in items if i['answer'] == 'yes')))
    status, reason = _shared_rule(answers)
    return _result(status, reason, _refs(*items))


def _pre_reaction_spectrum(record, native):
    return _one_fact(record, 'pre_reaction_spectrum')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'rate_proportional_to_enzyme')


def _product_assignment(record, native):
    return _one_fact(record, 'product_assigned')


def _quantitation_reference(record, native):
    standard, balance = record['facts']['internal_standard_used'], record['facts']['mass_balance_closed']
    answers = [standard['answer'], balance['answer']]
    if 'yes' in answers:
        return _result('supported', 'quantitation_reference_stated', _refs(*(i for i in (standard, balance) if i['answer'] == 'yes')))
    if balance['answer'] == 'no':
        return _result('conflicting', 'mass_balance_not_closed', _refs(balance))
    if all(a == 'not_applicable' for a in answers):
        return _result('not_applicable', 'fact_not_applicable', [])
    if standard['answer'] == 'no':
        return _result('unknown', 'internal_standard_not_used', [])
    return _result('unknown', 'fact_unknown', [])


def _signal_to_noise(record, native):
    value = _value(record, 'signal_to_noise')
    if value is None:
        return _result('unknown', 'signal_to_noise_not_stated', [])
    native.update({'signal_to_noise': value, 'signal_refs': _refs(record['quantities']['signal_to_noise'])})
    return _result('unknown', 'signal_to_noise_recorded_for_the_sheet', [])


def _relaxation(record, native):
    fully = record['facts']['fully_relaxed_acquisition']
    delay, t1 = _seconds(record, 'relaxation_delay'), _seconds(record, 'longest_t1')
    refs = _refs(record['quantities']['relaxation_delay'], record['quantities']['longest_t1'], fully)
    if fully['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if delay is not None and t1 is not None:
        native.update({'relaxation_over_t1': delay / t1, 'relaxation_refs': refs})
        return _result('unknown', 'relaxation_recorded_for_the_sheet', [])
    if fully['answer'] == 'yes':
        return _result('supported', 'fully_relaxed_acquisition_stated', refs)
    return _result('unknown', 'relaxation_not_stated', [])


def _initial_rate_regime(record, native):
    linear = record['facts']['linear_progress_curve']
    consumed = _value(record, 'substrate_consumed_percent')
    refs = _refs(record['quantities']['substrate_consumed_percent'], linear)
    if linear['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if consumed is not None:
        native.update({'consumed_percent': consumed, 'consumed_refs': refs})
        return _result('unknown', 'consumed_recorded_for_the_sheet', [])
    if linear['answer'] == 'yes':
        return _result('supported', 'linear_progress_curve_stated', refs)
    return _result('unknown', 'rate_regime_not_stated', [])


def _progress_curve_points(record, native):
    value = _value(record, 'time_point_count')
    if value is None:
        return _result('unknown', 'time_points_not_stated', [])
    native.update({'time_point_count': value, 'time_point_refs': _refs(record['quantities']['time_point_count'])})
    return _result('unknown', 'time_points_recorded_for_the_sheet', [])


def _enzyme_substrate_ratio(record, native):
    enzyme, substrate, km = _nm(record, 'enzyme_concentration'), _nm(record, 'substrate_concentration'), _nm(record, 'km')
    if enzyme is None or substrate is None or km is None:
        return _result('unknown', 'enzyme_substrate_or_km_missing', [])
    native['enzyme_over_substrate_plus_km'] = enzyme / (substrate + km)
    native['enzyme_ratio_refs'] = _refs(*(record['quantities'][n] for n in ('enzyme_concentration', 'substrate_concentration', 'km')))
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


EVALUATORS = {'spontaneous_reaction_control': _spontaneous_reaction_control, 'pre_reaction_spectrum': _pre_reaction_spectrum, 'enzyme_dependence': _enzyme_dependence,
              'product_assignment': _product_assignment, 'quantitation_reference': _quantitation_reference, 'signal_to_noise': _signal_to_noise,
              'relaxation': _relaxation, 'initial_rate_regime': _initial_rate_regime, 'progress_curve_points': _progress_curve_points,
              'enzyme_substrate_ratio': _enzyme_substrate_ratio, 'substrate_range': _substrate_range, 'active_enzyme_amount': _active_enzyme_amount,
              'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_nmr_timecourse(record):
    """Grade one real-time NMR progress-curve assay record. Returns the criterion answers and native values."""
    detected = record['facts']['activity_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'nucleus': record['nucleus'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'activity': ACTIVITY.get(detected['answer']), 'activity_refs': list(detected['source_refs']) if detected['answer'] in ACTIVITY else [], 'activity_support': detected['support'],
              'consumed_percent': None, 'consumed_refs': [], 'enzyme_over_substrate_plus_km': None, 'enzyme_ratio_refs': [], 'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None,
              'concentration_refs': [], 'signal_to_noise': None, 'signal_refs': [], 'relaxation_over_t1': None, 'relaxation_refs': [], 'time_point_count': None, 'time_point_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, NMR_TIMECOURSE_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'nmr_timecourse', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
