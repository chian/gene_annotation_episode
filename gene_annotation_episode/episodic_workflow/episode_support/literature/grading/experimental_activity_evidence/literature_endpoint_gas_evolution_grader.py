"""Endpoint_gas_evolution grader: judges ONE gas-evolution end-point enzyme experiment by its own standards. DRAFT of 2026-11-22, owner to correct.

Hand-built and private to endpoint_gas_evolution. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_endpoint_gas_evolution_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_endpoint_gas_evolution_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(control_over_test, amount_over_calibration_high and amount_over_calibration_low, amount_over_detection_limit, yield_over_theoretical, replicate_count, each with
its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact gas_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying whether
it saw gas above its own control. It is recorded in native as 'gas' with its refs and its support (class decision: 'interaction_detected' reads "conversion
detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, spread_kind, gas_species, readout_method and the preparations, and control_over_test, amount_over_calibration_high,
amount_over_calibration_low, amount_over_detection_limit, yield_over_theoretical, replicate_count, replicate_independent, gas, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_gas_evolution_criteria import (
    ENDPOINT_GAS_EVOLUTION_CRITERIA, NMOL_PER_UNIT, PERCENT_PER_FRACTION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_endpoint_gas_evolution_grade'
CRITERIA = tuple(criterion['id'] for criterion in ENDPOINT_GAS_EVOLUTION_CRITERIA)
GAS = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact gas_detected_above_control
CONTROL_PAIRS = (('gas_amount', 'control_gas_amount'), ('conversion_percent', 'control_conversion_percent'))   # a test value and its control of the same kind, amounts first


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _number(record, name):
    """The stated number of a quantity on a common scale: a gas amount in nmol, any other quantity as stated; None when not stated."""
    operand = record['quantities'][name]
    if operand['status'] != 'point':
        return None
    return operand['value'] * NMOL_PER_UNIT[operand['unit']] if operand['unit'] in NMOL_PER_UNIT else operand['value']


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


def _spontaneous_gas_control(record, native):
    names = ('no_enzyme_control_done', 'inactive_enzyme_control_done')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'spontaneous_gas_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _zero_time_gas(record, native):
    return _one_fact(record, 'zero_time_sample_done')


def _leak_control(record, native):
    return _one_fact(record, 'leak_control_done')


def _signal_over_control(record, native):
    for test, control in CONTROL_PAIRS:
        if _number(record, test) is not None and _number(record, control) is not None:
            native['control_over_test'] = _number(record, control) / _number(record, test)
            native['control_refs'] = _refs(record['quantities'][test], record['quantities'][control])
            return _result('unknown', 'control_recorded_for_the_sheet', [])
    return _result('unknown', 'control_or_test_not_stated', [])


def _enzyme_dependence(record, native):
    return _one_fact(record, 'enzyme_dependence_shown')


def _gas_identity(record, native):
    return _one_fact(record, 'gas_identified_by_detector')


def _calibration_gas(record, native):
    return _one_fact(record, 'calibration_gas_in_same_vessel')


def _calibration_range(record, native):
    amount, low, high = _number(record, 'gas_amount'), _number(record, 'calibration_low'), _number(record, 'calibration_high')
    if amount is None or low is None or high is None:
        return _result('unknown', 'calibration_range_or_amount_missing', [])
    native.update({'amount_over_calibration_high': amount / high, 'amount_over_calibration_low': amount / low,
                   'calibration_refs': _refs(*(record['quantities'][n] for n in ('gas_amount', 'calibration_low', 'calibration_high')))})
    return _result('unknown', 'calibration_range_recorded_for_the_sheet', [])


def _detection_margin(record, native):
    amount, limit = _number(record, 'gas_amount'), _number(record, 'detection_limit')
    if amount is None or limit is None:
        return _result('unknown', 'amount_or_detection_limit_missing', [])
    native.update({'amount_over_detection_limit': amount / limit, 'detection_refs': _refs(record['quantities']['gas_amount'], record['quantities']['detection_limit'])})
    return _result('unknown', 'detection_margin_recorded_for_the_sheet', [])


def _dissolved_gas(record, native):
    return _one_fact(record, 'dissolved_gas_accounted_for')


def _vessel_volumes(record, native):
    if _value(record, 'headspace_volume') is None or _value(record, 'liquid_volume') is None:
        return _result('unknown', 'headspace_or_liquid_volume_missing', [])
    return _result('supported', 'headspace_and_liquid_volume_stated', _refs(record['quantities']['headspace_volume'], record['quantities']['liquid_volume']))


def _time_point_stated(record, native):
    if _value(record, 'endpoint_time') is None:
        return _result('unknown', 'endpoint_time_not_stated', [])
    return _result('supported', 'endpoint_time_stated', _refs(record['quantities']['endpoint_time']))


def _same_time_for_compared_arms(record, native):
    return _one_fact(record, 'same_time_for_compared_arms')


def _yield_denominator(record, native):
    return _one_fact(record, 'initial_substrate_determined')


def _yield_not_above_theoretical(record, native):
    ratios, used = [], []
    if _number(record, 'gas_amount') is not None and _number(record, 'theoretical_yield') is not None:
        ratios.append(_number(record, 'gas_amount') / _number(record, 'theoretical_yield'))
        used += [record['quantities']['gas_amount'], record['quantities']['theoretical_yield']]
    if _number(record, 'conversion_percent') is not None:
        ratios.append(_number(record, 'conversion_percent') / PERCENT_PER_FRACTION)
        used.append(record['quantities']['conversion_percent'])
    if not ratios:
        return _result('unknown', 'yield_or_theoretical_not_stated', [])
    native.update({'yield_over_theoretical': max(ratios), 'yield_refs': _refs(*used)})
    return _result('unknown', 'yield_recorded_for_the_sheet', [])


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


EVALUATORS = {'spontaneous_gas_control': _spontaneous_gas_control, 'zero_time_gas': _zero_time_gas, 'leak_control': _leak_control, 'signal_over_control': _signal_over_control,
              'enzyme_dependence': _enzyme_dependence, 'gas_identity': _gas_identity, 'calibration_gas': _calibration_gas, 'calibration_range': _calibration_range,
              'detection_margin': _detection_margin, 'dissolved_gas': _dissolved_gas, 'vessel_volumes': _vessel_volumes, 'time_point_stated': _time_point_stated,
              'same_time_for_compared_arms': _same_time_for_compared_arms, 'yield_denominator': _yield_denominator, 'yield_not_above_theoretical': _yield_not_above_theoretical,
              'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_endpoint_gas_evolution(record):
    """Grade one gas-evolution end-point experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['gas_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'gas_species': record['gas_species'], 'readout_method': record['readout_method'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'gas': GAS.get(detected['answer']), 'gas_refs': list(detected['source_refs']) if detected['answer'] in GAS else [], 'gas_support': detected['support'],
              'control_over_test': None, 'control_refs': [], 'amount_over_calibration_high': None, 'amount_over_calibration_low': None, 'calibration_refs': [],
              'amount_over_detection_limit': None, 'detection_refs': [], 'yield_over_theoretical': None, 'yield_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ENDPOINT_GAS_EVOLUTION_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'endpoint_gas_evolution', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
