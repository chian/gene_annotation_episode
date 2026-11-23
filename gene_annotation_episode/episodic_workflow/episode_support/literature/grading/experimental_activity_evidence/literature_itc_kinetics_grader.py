"""Itc_kinetics grader: judges ONE isothermal titration calorimetry enzyme-kinetics experiment by its own standards.

Hand-built and private to itc_kinetics. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_itc_kinetics_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_itc_kinetics_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(dilution_over_signal, noise_over_signal, consumed_percent, enzyme_over_substrate_plus_km, the series count and its two ratios over the Km,
replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact activity_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw activity above its own control. It is recorded in native as 'activity' with its refs and its support (class
decision of 2026-11-21: 'interaction_detected' reads "activity detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series and the preparations, spread_kind, injection_mode, and dilution_over_signal,
noise_over_signal, consumed_percent, enzyme_over_substrate_plus_km, concentration_count, concentration_low_over_km, concentration_high_over_km,
replicate_count, replicate_independent, activity, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_kinetics_criteria import ITC_KINETICS_CRITERIA, POWER_UW_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_itc_kinetics_grade'
CRITERIA = tuple(criterion['id'] for criterion in ITC_KINETICS_CRITERIA)
ACTIVITY = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact activity_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * _SCALES[record['quantities'][name]['unit']]


def _uw(record, name):
    value = _value(record, name)
    return None if value is None else value * POWER_UW_PER_UNIT[record['quantities'][name]['unit']]


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


def _substrate_dilution_control(record, native):
    return _one_fact(record, 'substrate_into_buffer_control')


def _enzyme_dilution_control(record, native):
    return _one_fact(record, 'enzyme_into_buffer_control')


def _signal_over_blank(record, native):
    signal, blank = _uw(record, 'thermal_power'), _uw(record, 'dilution_power')
    if signal is None or blank is None:
        return _result('unknown', 'power_or_blank_missing', [])
    native['dilution_over_signal'] = blank / signal
    native['blank_refs'] = _refs(record['quantities']['thermal_power'], record['quantities']['dilution_power'])
    return _result('unknown', 'blank_share_recorded_for_the_sheet', [])


def _signal_over_noise(record, native):
    signal, noise = _uw(record, 'thermal_power'), _uw(record, 'baseline_noise')
    if signal is None or noise is None:
        return _result('unknown', 'power_or_noise_missing', [])
    native['noise_over_signal'] = noise / signal
    native['noise_refs'] = _refs(record['quantities']['thermal_power'], record['quantities']['baseline_noise'])
    return _result('unknown', 'noise_share_recorded_for_the_sheet', [])


def _enthalpy_stated(record, native):
    if _value(record, 'reaction_enthalpy') is None:
        return _result('unknown', 'reaction_enthalpy_missing', [])
    return _result('supported', 'reaction_enthalpy_stated', _refs(record['quantities']['reaction_enthalpy']))


def _enthalpy_determined(record, native):
    return _one_fact(record, 'enthalpy_determined_in_assay_buffer')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'rate_proportional_to_enzyme')


def _product_identity(record, native):
    return _one_fact(record, 'product_identified')


def _initial_rate_regime(record, native):
    plateau = record['facts']['steady_power_plateau']
    consumed = _value(record, 'substrate_consumed_percent')
    refs = _refs(record['quantities']['substrate_consumed_percent'], plateau)
    if plateau['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if consumed is not None:
        native.update({'consumed_percent': consumed, 'consumed_refs': refs})
        return _result('unknown', 'consumed_recorded_for_the_sheet', [])
    if plateau['answer'] == 'yes':
        return _result('supported', 'steady_power_plateau_stated', refs)
    return _result('unknown', 'rate_regime_not_stated', [])


def _response_time_accounted(record, native):
    return _one_fact(record, 'response_time_accounted')


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


EVALUATORS = {'substrate_dilution_control': _substrate_dilution_control, 'enzyme_dilution_control': _enzyme_dilution_control, 'signal_over_blank': _signal_over_blank,
              'signal_over_noise': _signal_over_noise, 'enthalpy_stated': _enthalpy_stated, 'enthalpy_determined': _enthalpy_determined, 'enzyme_dependence': _enzyme_dependence,
              'product_identity': _product_identity, 'initial_rate_regime': _initial_rate_regime, 'response_time_accounted': _response_time_accounted,
              'enzyme_substrate_ratio': _enzyme_substrate_ratio, 'substrate_range': _substrate_range, 'active_enzyme_amount': _active_enzyme_amount,
              'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_itc_kinetics(record):
    """Grade one isothermal titration calorimetry enzyme-kinetics record. Returns the criterion answers and native values."""
    detected = record['facts']['activity_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'injection_mode': record['injection_mode'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'activity': ACTIVITY.get(detected['answer']), 'activity_refs': list(detected['source_refs']) if detected['answer'] in ACTIVITY else [], 'activity_support': detected['support'],
              'dilution_over_signal': None, 'blank_refs': [], 'noise_over_signal': None, 'noise_refs': [], 'consumed_percent': None, 'consumed_refs': [],
              'enzyme_over_substrate_plus_km': None, 'enzyme_ratio_refs': [], 'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None,
              'concentration_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ITC_KINETICS_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'itc_kinetics', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
