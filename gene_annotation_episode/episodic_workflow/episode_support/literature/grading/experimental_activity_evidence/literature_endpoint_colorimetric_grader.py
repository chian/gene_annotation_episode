"""Endpoint_colorimetric grader: judges ONE stopped colorimetric end-point experiment by its own standards.

Hand-built and private to endpoint_colorimetric. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_endpoint_colorimetric_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_endpoint_colorimetric_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(product_over_standard_high and product_over_standard_low, standard_points, replicate_count, each with its refs) and returns 'unknown' with a reason
ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact conversion_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper itself
saying whether it saw conversion (a product) above its own control or blank. It is recorded in native as 'conversion_statement' with its refs and its
support (class decision: 'interaction_detected' reads "conversion detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the preparations, spread_kind, reagent_class, and product_over_standard_high,
product_over_standard_low, standard_points, replicate_count, replicate_independent, conversion_statement, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_colorimetric_criteria import (
    ENDPOINT_COLORIMETRIC_CRITERIA, NM_PER_UNIT, PMOL_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_endpoint_colorimetric_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in ENDPOINT_COLORIMETRIC_CRITERIA)
CONVERSION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact conversion_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _in_base_unit(record, name):
    """(kind, value) of a stated amount or concentration: kind 'concentration' with the value in nM, or kind 'amount' with the value in pmol; None when not stated."""
    operand = record['quantities'][name]
    if operand['status'] != 'point':
        return None
    if operand['unit'] in NM_PER_UNIT:
        return 'concentration', operand['value'] * NM_PER_UNIT[operand['unit']]
    return 'amount', operand['value'] * PMOL_PER_UNIT[operand['unit']]


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


def _either_done(record, names, supported_reason):
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', supported_reason, refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _spontaneous_reaction_control(record, native):
    return _either_done(record, ('no_enzyme_control', 'inactive_enzyme_control'), 'spontaneous_reaction_control_stated')


def _enzyme_borne_signal(record, native):
    return _either_done(record, ('no_substrate_control', 'zero_time_sample'), 'enzyme_borne_signal_control_stated')


def _standard_curve_in_buffer(record, native):
    return _one_fact(record, 'standard_curve_in_buffer')


def _standard_curve_range(record, native):
    product, low, high = (_in_base_unit(record, name) for name in ('product_read_on_curve', 'standard_curve_low', 'standard_curve_high'))
    ends = [end for end in (low, high) if end is not None]
    if product is None or not ends:
        return _result('unknown', 'standard_range_not_stated', [])
    if any(end[0] != product[0] for end in ends):
        return _result('unknown', 'standard_range_units_differ', [])
    native['product_over_standard_low'] = None if low is None else product[1] / low[1]
    native['product_over_standard_high'] = None if high is None else product[1] / high[1]
    native['standard_range_refs'] = _refs(*(record['quantities'][n] for n in ('product_read_on_curve', 'standard_curve_low', 'standard_curve_high')))
    return _result('unknown', 'standard_range_recorded_for_the_sheet', [])


def _standard_curve_points(record, native):
    count = _value(record, 'standard_curve_points')
    if count is None:
        return _result('unknown', 'standard_points_not_stated', [])
    native.update({'standard_points': count, 'standard_points_refs': _refs(record['quantities']['standard_curve_points'])})
    return _result('unknown', 'standard_points_recorded_for_the_sheet', [])


def _reagent_interference_checked(record, native):
    return _one_fact(record, 'reagent_interference_checked')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'product_rises_with_enzyme')


def _product_identity(record, native):
    return _one_fact(record, 'product_identified_independently')


def _endpoint_time_stated(record, native):
    if _value(record, 'endpoint_time') is None:
        return _result('unknown', 'endpoint_time_not_stated', [])
    return _result('supported', 'endpoint_time_stated', _refs(record['quantities']['endpoint_time']))


def _reaction_stopped(record, native):
    return _one_fact(record, 'reaction_stopped')


def _same_time_for_arms(record, native):
    return _one_fact(record, 'same_time_for_compared_arms')


def _denominator_stated(record, native):
    if _value(record, 'substrate_initial') is None:
        return _result('unknown', 'initial_substrate_not_stated', [])
    return _result('supported', 'initial_substrate_stated', _refs(record['quantities']['substrate_initial']))


def _denominator_measured(record, native):
    return _one_fact(record, 'initial_substrate_determined')


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


EVALUATORS = {'spontaneous_reaction_control': _spontaneous_reaction_control, 'enzyme_borne_signal': _enzyme_borne_signal, 'standard_curve_in_buffer': _standard_curve_in_buffer,
              'standard_curve_range': _standard_curve_range, 'standard_curve_points': _standard_curve_points, 'reagent_interference_checked': _reagent_interference_checked,
              'enzyme_dependence': _enzyme_dependence, 'product_identity': _product_identity, 'endpoint_time_stated': _endpoint_time_stated,
              'reaction_stopped': _reaction_stopped, 'same_time_for_arms': _same_time_for_arms, 'denominator_stated': _denominator_stated,
              'denominator_measured': _denominator_measured, 'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_endpoint_colorimetric(record):
    """Grade one stopped colorimetric end-point experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['conversion_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'reagent_class': record['reagent_class'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'conversion_statement': CONVERSION.get(detected['answer']), 'conversion_statement_refs': list(detected['source_refs']) if detected['answer'] in CONVERSION else [], 'conversion_statement_support': detected['support'],
              'product_over_standard_low': None, 'product_over_standard_high': None, 'standard_range_refs': [], 'standard_points': None, 'standard_points_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ENDPOINT_COLORIMETRIC_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'endpoint_colorimetric', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
