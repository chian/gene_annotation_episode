"""Endpoint_ms_quant grader: judges ONE fixed-time enzyme reaction with mass-spectrometric product quantification by its own standards.

DRAFT of 2026-11-22 (owner to correct). Hand-built and private to endpoint_ms_quant. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_endpoint_ms_quant_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_endpoint_ms_quant_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(background_share, the read amount over the two ends of the calibration range, calibration_points, the read amount over the limit of
quantification and of detection, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. Two criteria read several controls or several identifications and are supported by any
one 'yes' (the shared rule decides only when none is yes).

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact conversion_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw conversion above its own control. It is recorded in native as 'conversion' with its refs and its support (class
reading: 'interaction_detected' reads "conversion detected"). It is only used by the converter when no effect quantity is stated.

Native values retained: every record quantity as given, the preparations, spread_kind, and background_share, read_over_calibration_low,
read_over_calibration_high, calibration_points, read_over_quantification_limit, read_over_detection_limit, replicate_count,
replicate_independent, conversion, each with its refs. Concentrations are compared in uM and shares as fractions by the fixed scale tables of
the criteria file (FIXED_BY_DEFINITION); an amount in mol is never compared with a calibration range (the volume the sample was analysed in is not the reaction volume).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_ms_quant_criteria import (
    ENDPOINT_MS_QUANT_CRITERIA, FRACTION_PER_UNIT, UM_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_endpoint_ms_quant_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in ENDPOINT_MS_QUANT_CRITERIA)
CONVERSION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact conversion_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _um(record, name):
    """The concentration of a quantity in uM, or None when it is not stated or is an amount in mol (not a concentration)."""
    operand = record['quantities'][name]
    if operand['status'] != 'point' or operand['unit'] not in UM_PER_UNIT:
        return None
    return operand['value'] * UM_PER_UNIT[operand['unit']]


def _fraction(record, name):
    operand = record['quantities'][name]
    return operand['value'] * FRACTION_PER_UNIT[operand['unit']] if operand['status'] == 'point' else None


def _refs(*items):
    refs = []
    for item in items:
        refs += item['source_refs']
    return list(dict.fromkeys(refs))


def _cited(items, answer):
    return _refs(*(item for item in items if item['answer'] == answer))


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


def _any_yes(record, names, reason_yes):
    """Any one of the facts stated yes supports; otherwise the shared rule decides (a stated no fails, silence is unknown)."""
    items = [record['facts'][name] for name in names]
    answers = [item['answer'] for item in items]
    if 'yes' in answers:
        return _result('supported', reason_yes, _cited(items, 'yes'))
    status, reason = _shared_rule(answers)
    return _result(status, reason, _cited(items, 'no'))


def _spontaneous_reaction_control(record, native):
    return _any_yes(record, ('no_enzyme_control_done', 'inactive_enzyme_control_done', 'zero_time_sample_done'), 'spontaneous_reaction_control_stated')


def _signal_above_control(record, native):
    test, control = _fraction(record, 'conversion_fraction'), _fraction(record, 'control_conversion')
    if test is None or control is None:
        return _result('unknown', 'conversion_or_control_not_stated', [])
    native.update({'background_share': control / test, 'background_refs': _refs(record['quantities']['conversion_fraction'], record['quantities']['control_conversion'])})
    return _result('unknown', 'background_share_recorded_for_the_sheet', [])


def _enzyme_dependence(record, native):
    return _one_fact(record, 'enzyme_dependence_shown')


def _internal_standard(record, native):
    return _one_fact(record, 'internal_standard_used')


def _matrix_matched_calibration(record, native):
    return _one_fact(record, 'matrix_matched_calibration')


def _calibration_range(record, native):
    fact = record['facts']['amounts_within_calibration_range']
    if fact['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', fact['source_refs'])
    low, high, read = _um(record, 'calibration_low'), _um(record, 'calibration_high'), _um(record, 'endpoint_amount')
    if low is not None and high is not None and read is not None:
        native.update({'read_over_calibration_low': read / low, 'read_over_calibration_high': read / high,
                       'range_refs': _refs(*(record['quantities'][name] for name in ('calibration_low', 'calibration_high', 'endpoint_amount')))})
        return _result('unknown', 'calibration_range_recorded_for_the_sheet', [])
    return _one_fact(record, 'amounts_within_calibration_range')


def _calibration_points(record, native):
    count = _value(record, 'calibration_points')
    if count is None:
        return _result('unknown', 'calibration_points_not_stated', [])
    native.update({'calibration_points': count, 'points_refs': _refs(record['quantities']['calibration_points'])})
    return _result('unknown', 'calibration_points_recorded_for_the_sheet', [])


def _quantification_floor(record, native):
    read, quantification, detection = _um(record, 'endpoint_amount'), _um(record, 'quantification_limit'), _um(record, 'detection_limit')
    if read is None or (quantification is None and detection is None):
        return _result('unknown', 'amount_or_limit_not_stated', [])
    native.update({'read_over_quantification_limit': None if quantification is None else read / quantification,
                   'read_over_detection_limit': None if detection is None else read / detection,
                   'floor_refs': _refs(*(record['quantities'][name] for name in ('endpoint_amount', 'quantification_limit', 'detection_limit')))})
    return _result('unknown', 'quantification_floor_recorded_for_the_sheet', [])


def _product_identification(record, native):
    return _any_yes(record, ('authentic_standard_used', 'ms_ms_confirmation', 'accurate_mass_match'), 'product_identification_stated')


def _endpoint_time_stated(record, native):
    operand = record['quantities']['endpoint_time']
    if operand['status'] != 'point':
        return _result('unknown', 'endpoint_time_not_stated', [])
    return _result('supported', 'endpoint_time_stated', operand['source_refs'])


def _reaction_stopped(record, native):
    return _one_fact(record, 'reaction_stopped_before_analysis')


def _same_time_across_arms(record, native):
    return _one_fact(record, 'same_time_for_compared_arms')


def _initial_substrate(record, native):
    fact, quantity = record['facts']['initial_substrate_determined'], record['quantities']['substrate_initial']
    if fact['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', fact['source_refs'])
    if fact['answer'] == 'yes':
        return _result('supported', 'facts_answered_yes', _refs(fact, quantity))
    if quantity['status'] == 'point':
        return _result('supported', 'substrate_initial_stated', quantity['source_refs'])
    if fact['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'substrate_initial_not_stated', [])


def _native_reaction(record, native):
    return _one_fact(record, 'native_substrate')


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


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


EVALUATORS = {'spontaneous_reaction_control': _spontaneous_reaction_control, 'signal_above_control': _signal_above_control, 'enzyme_dependence': _enzyme_dependence,
              'internal_standard': _internal_standard, 'matrix_matched_calibration': _matrix_matched_calibration, 'calibration_range': _calibration_range,
              'calibration_points': _calibration_points, 'quantification_floor': _quantification_floor, 'product_identification': _product_identification,
              'endpoint_time_stated': _endpoint_time_stated, 'reaction_stopped': _reaction_stopped, 'same_time_across_arms': _same_time_across_arms,
              'initial_substrate': _initial_substrate, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme, 'replicates': _replicates}


def grade_endpoint_ms_quant(record):
    """Grade one fixed-time mass-spectrometric endpoint record. Returns the criterion answers and native values."""
    detected = record['facts']['conversion_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'conversion': CONVERSION.get(detected['answer']), 'conversion_refs': list(detected['source_refs']) if detected['answer'] in CONVERSION else [], 'conversion_support': detected['support'],
              'background_share': None, 'background_refs': [], 'read_over_calibration_low': None, 'read_over_calibration_high': None, 'range_refs': [], 'calibration_points': None, 'points_refs': [],
              'read_over_quantification_limit': None, 'read_over_detection_limit': None, 'floor_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ENDPOINT_MS_QUANT_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'endpoint_ms_quant', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
