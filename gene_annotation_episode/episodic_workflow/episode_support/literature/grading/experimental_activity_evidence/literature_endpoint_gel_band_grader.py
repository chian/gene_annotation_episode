"""Endpoint_gel_band grader: judges ONE gel or TLC end-point conversion experiment by its own standards (DRAFT 2026-11-22, owner to correct).

Hand-built and private to endpoint_gel_band. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_endpoint_gel_band_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_endpoint_gel_band_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(test_fraction and control_fraction with control_refs, replicate_count with replicate_independent and replicate_refs) and returns 'unknown' with a
reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. A 'supported' or 'conflicting' result always carries support refs: _result raises without them.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact conversion_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw a product band above its own control. It is recorded in native as 'conversion' with its refs and its support
(class decision: 'interaction_detected' reads "conversion detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the two plain choices, the preparations, test_fraction, control_fraction and control_refs,
replicate_count, replicate_independent and replicate_refs, conversion, conversion_refs and conversion_support.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_gel_band_criteria import ENDPOINT_GEL_BAND_CRITERIA, PERCENT_PER_FRACTION
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_endpoint_gel_band_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in ENDPOINT_GEL_BAND_CRITERIA)
CONVERSION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact conversion_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _fraction(record, name):
    value = _value(record, name)
    if value is None:
        return None
    return value / PERCENT_PER_FRACTION if record['quantities'][name]['unit'] == 'percent' else value


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
    names = ('no_enzyme_lane_done', 'inactive_enzyme_lane_done')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'spontaneous_reaction_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _substrate_purity_control(record, native):
    return _one_fact(record, 'zero_time_lane_done')


def _control_lane_background(record, native):
    test, control = _fraction(record, 'conversion_percent'), _fraction(record, 'control_conversion')
    if test is None or control is None:
        return _result('unknown', 'control_or_test_conversion_missing', [])
    if test == 0:
        return _result('unknown', 'test_conversion_is_zero', [])
    native.update({'test_fraction': test, 'control_fraction': control, 'control_refs': _refs(record['quantities']['conversion_percent'], record['quantities']['control_conversion'])})
    return _result('unknown', 'control_background_recorded_for_the_sheet', [])


def _enzyme_dependence(record, native):
    return _one_fact(record, 'product_depends_on_active_enzyme')


def _product_identity(record, native):
    return _one_fact(record, 'band_identified_by_marker')


def _densitometry_linear_range(record, native):
    return _one_fact(record, 'signal_within_linear_range')


def _same_lane_fraction(record, native):
    return _one_fact(record, 'fraction_from_same_lane_bands')


def _endpoint_time_defined(record, native):
    stopped = record['facts']['reaction_stopped_before_loading']
    refs = _refs(record['quantities']['endpoint_time'], stopped)
    if stopped['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if stopped['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    if stopped['answer'] == 'yes' and _value(record, 'endpoint_time') is not None:
        return _result('supported', 'time_and_stop_stated', refs)
    return _result('unknown', 'time_or_stop_not_stated', [])


def _lanes_same_time(record, native):
    return _one_fact(record, 'same_time_for_compared_lanes')


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


EVALUATORS = {'spontaneous_reaction_control': _spontaneous_reaction_control, 'substrate_purity_control': _substrate_purity_control, 'control_lane_background': _control_lane_background,
              'enzyme_dependence': _enzyme_dependence, 'product_identity': _product_identity, 'densitometry_linear_range': _densitometry_linear_range,
              'same_lane_fraction': _same_lane_fraction, 'endpoint_time_defined': _endpoint_time_defined, 'lanes_same_time': _lanes_same_time,
              'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme, 'replicates': _replicates}


def grade_endpoint_gel_band(record):
    """Grade one gel or TLC end-point conversion record. Returns the criterion answers and native values."""
    detected = record['facts']['conversion_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'fraction_defined_over': record['fraction_defined_over'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'conversion': CONVERSION.get(detected['answer']), 'conversion_refs': list(detected['source_refs']) if detected['answer'] in CONVERSION else [], 'conversion_support': detected['support'],
              'test_fraction': None, 'control_fraction': None, 'control_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ENDPOINT_GEL_BAND_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'endpoint_gel_band', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
