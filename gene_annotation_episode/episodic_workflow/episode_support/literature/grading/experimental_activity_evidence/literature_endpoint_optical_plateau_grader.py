"""Endpoint_optical_plateau grader: judges ONE reaction run to an optical plateau by its own standards. DRAFT 2026-11-22, owner to correct.

Hand-built and private to endpoint_optical_plateau. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_endpoint_optical_plateau_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_endpoint_optical_plateau_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(control_over_test and baseline_over_signal, full_over_expected, signal_over_full, absorbance_max, replicate_count, each with its refs) and returns
'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it. The unit conversions it uses are the criteria file's
FIXED_BY_DEFINITION tables.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact conversion_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper itself
saying whether it saw conversion above its own control. It is recorded in native as 'conversion' with its refs and its support ('interaction_detected'
reads "conversion detected" for this class). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, spread_kind, and control_over_test, baseline_over_signal, full_over_expected, signal_over_full,
absorbance_max, replicate_count, replicate_independent, conversion, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_optical_plateau_criteria import (
    CM_PER_UNIT, ENDPOINT_OPTICAL_PLATEAU_CRITERIA, FRACTION_PER_UNIT, M_PER_UNIT, PER_M_CM_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_endpoint_optical_plateau_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in ENDPOINT_OPTICAL_PLATEAU_CRITERIA)
CONVERSION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact conversion_detected_above_control
ABSORBANCE_UNIT = 'AU'


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _fraction(record, name):
    value = _value(record, name)
    return None if value is None else value * FRACTION_PER_UNIT[record['quantities'][name]['unit']]


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


def _same_unit_ratio(record, top, bottom):
    """top over bottom when both are given in one unit, else None."""
    first, second = record['quantities'][top], record['quantities'][bottom]
    if first['status'] != 'point' or second['status'] != 'point' or first['unit'] != second['unit']:
        return None
    return first['value'] / second['value']


def _readout_stated(record, native):
    if _value(record, 'wavelength') is None or _value(record, 'substrate_initial') is None:
        return _result('unknown', 'wavelength_or_substrate_missing', [])
    return _result('supported', 'wavelength_and_substrate_stated', _refs(record['quantities']['wavelength'], record['quantities']['substrate_initial']))


def _baseline_control(record, native):
    names = ('no_enzyme_control_done', 'inactive_enzyme_control_done')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'baseline_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _baseline_level(record, native):
    control, test = _fraction(record, 'control_conversion'), _fraction(record, 'conversion_percent')
    control_over_test = None if control is None or test is None else control / test
    baseline_over_signal = _same_unit_ratio(record, 'signal_change_baseline', 'signal_change_total')
    if control_over_test is None and baseline_over_signal is None:
        return _result('unknown', 'baseline_level_not_stated', [])
    names = (('control_conversion', 'conversion_percent') if control_over_test is not None else ()) + (('signal_change_baseline', 'signal_change_total') if baseline_over_signal is not None else ())
    native.update({'control_over_test': control_over_test, 'baseline_over_signal': baseline_over_signal, 'baseline_refs': _refs(*(record['quantities'][n] for n in names))})
    return _result('unknown', 'baseline_level_recorded_for_the_sheet', [])


def _control_same_window(record, native):
    return _one_fact(record, 'control_read_over_same_time')


def _calibration_basis(record, native):
    reference = record['facts']['full_conversion_reference_done']
    if reference['answer'] == 'yes':
        return _result('supported', 'full_conversion_reference_stated', reference['source_refs'])
    if _value(record, 'extinction_coefficient') is not None and _value(record, 'wavelength') is not None:
        return _result('supported', 'extinction_coefficient_and_wavelength_stated', _refs(record['quantities']['extinction_coefficient'], record['quantities']['wavelength']))
    if reference['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', reference['source_refs'])
    return _result('unknown', 'calibration_basis_not_stated', [])


def _calibration_agreement(record, native):
    quantities = record['quantities']
    names = ('signal_change_full', 'extinction_coefficient', 'path_length', 'substrate_initial')
    if any(_value(record, n) is None for n in names) or quantities['signal_change_full']['unit'] != ABSORBANCE_UNIT:
        return _result('unknown', 'calibration_agreement_inputs_missing', [])
    expected = (quantities['extinction_coefficient']['value'] * PER_M_CM_PER_UNIT[quantities['extinction_coefficient']['unit']]
                * quantities['path_length']['value'] * CM_PER_UNIT[quantities['path_length']['unit']]
                * quantities['substrate_initial']['value'] * M_PER_UNIT[quantities['substrate_initial']['unit']])
    native.update({'full_over_expected': quantities['signal_change_full']['value'] / expected, 'calibration_refs': _refs(*(quantities[n] for n in names))})
    return _result('unknown', 'calibration_agreement_recorded_for_the_sheet', [])


def _signal_linear_range(record, native):
    linear = record['facts']['signal_in_linear_range']
    highest = _value(record, 'absorbance_max')
    refs = _refs(record['quantities']['absorbance_max'], linear)
    if linear['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if highest is not None:
        native.update({'absorbance_max': highest, 'absorbance_refs': refs})
        return _result('unknown', 'absorbance_recorded_for_the_sheet', [])
    if linear['answer'] == 'yes':
        return _result('supported', 'signal_in_linear_range_stated', refs)
    return _result('unknown', 'linear_range_not_stated', [])


def _inner_filter_check(record, native):
    return _one_fact(record, 'inner_filter_checked')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'enzyme_dependence_shown')


def _plateau_reached(record, native):
    return _one_fact(record, 'plateau_stable')


def _initial_substrate_determined(record, native):
    return _one_fact(record, 'initial_substrate_determined')


def _conversion_within_full_scale(record, native):
    ratio = _same_unit_ratio(record, 'signal_change_total', 'signal_change_full')
    if ratio is None:
        return _result('unknown', 'full_scale_comparison_missing', [])
    native.update({'signal_over_full': ratio, 'full_scale_refs': _refs(record['quantities']['signal_change_total'], record['quantities']['signal_change_full'])})
    return _result('unknown', 'full_scale_recorded_for_the_sheet', [])


def _product_identity(record, native):
    return _one_fact(record, 'product_identified_by_standard')


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


EVALUATORS = {'readout_stated': _readout_stated, 'baseline_control': _baseline_control, 'baseline_level': _baseline_level, 'control_same_window': _control_same_window,
              'calibration_basis': _calibration_basis, 'calibration_agreement': _calibration_agreement, 'signal_linear_range': _signal_linear_range,
              'inner_filter_check': _inner_filter_check, 'enzyme_dependence': _enzyme_dependence, 'plateau_reached': _plateau_reached,
              'initial_substrate_determined': _initial_substrate_determined, 'conversion_within_full_scale': _conversion_within_full_scale,
              'product_identity': _product_identity, 'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_endpoint_optical_plateau(record):
    """Grade one optical-plateau record. Returns the criterion answers and native values."""
    detected = record['facts']['conversion_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'conversion': CONVERSION.get(detected['answer']), 'conversion_refs': list(detected['source_refs']) if detected['answer'] in CONVERSION else [], 'conversion_support': detected['support'],
              'control_over_test': None, 'baseline_over_signal': None, 'baseline_refs': [], 'full_over_expected': None, 'calibration_refs': [], 'signal_over_full': None, 'full_scale_refs': [],
              'absorbance_max': None, 'absorbance_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ENDPOINT_OPTICAL_PLATEAU_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'endpoint_optical_plateau', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
