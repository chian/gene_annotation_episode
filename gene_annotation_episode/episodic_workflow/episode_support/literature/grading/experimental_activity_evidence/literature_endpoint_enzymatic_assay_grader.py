"""Endpoint_enzymatic_assay grader: judges ONE end-point determination with a second enzyme by its own standards. DRAFT (2026-11-22), owner to correct.

Hand-built and private to endpoint_enzymatic_assay. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_endpoint_enzymatic_assay_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_endpoint_enzymatic_assay_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(r_squared, standard_points, read_over_standard_high and read_over_standard_low, incubation_minutes, limit_over_initial, replicate_count, each with its
refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it. The only numbers in this file are
the unit scales of the criteria file (FIXED_BY_DEFINITION), used to put two numbers of the paper in one unit before a ratio is recorded.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. A criterion over several facts where one stated yes is enough (the controls, the matrix
check, the product identity) is supported by any yes; otherwise the shared rule applies.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact conversion_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw conversion above its own control or blank. It is recorded in native as 'conversion' with its refs and its support
(class decision: 'interaction_detected' reads "conversion detected"). It is only used by the converter when no effect quantity can be used.

Native values retained: every record quantity as given, the preparations, spread_kind, and r_squared, standard_points, read_over_standard_high,
read_over_standard_low, incubation_minutes, limit_over_initial, replicate_count, replicate_independent, conversion, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_enzymatic_assay_criteria import (
    ENDPOINT_ENZYMATIC_ASSAY_CRITERIA, MIN_PER_UNIT, NMOL_PER_UNIT, UM_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_endpoint_enzymatic_assay_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in ENDPOINT_ENZYMATIC_ASSAY_CRITERIA)
CONVERSION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact conversion_detected_above_control
EFFECT_QUANTITIES = ('net_conversion_percent', 'conversion_percent', 'product_amount')
STANDARD_ENDS = ('standard_series_low', 'standard_series_high')


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _scaled(operand):
    """(kind, value) of a stated concentration (in uM) or amount (in nmol): two numbers are compared only within one kind."""
    if operand['unit'] in UM_PER_UNIT:
        return 'concentration', operand['value'] * UM_PER_UNIT[operand['unit']]
    return 'amount', operand['value'] * NMOL_PER_UNIT[operand['unit']]


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


def _any_yes(record, names, supported_reason):
    items = [record['facts'][n] for n in names]
    answers = [item['answer'] for item in items]
    if 'yes' in answers:
        return _result('supported', supported_reason, _refs(*[item for item in items if item['answer'] == 'yes']))
    status, reason = _shared_rule(answers)
    return _result(status, reason, _refs(*[item for item in items if item['answer'] == 'no']))


def _estimate_identity(record, native):
    effects = [record['quantities'][name] for name in EFFECT_QUANTITIES if record['quantities'][name]['status'] == 'point']
    time = record['quantities']['endpoint_time']
    if not effects:
        return _result('unknown', 'no_effect_quantity_stated', [])
    if time['status'] != 'point':
        return _result('unknown', 'endpoint_time_not_stated', [])
    return _result('supported', 'effect_and_endpoint_time_stated', _refs(*effects, time))


def _standard_series_through_second_enzyme(record, native):
    return _one_fact(record, 'standard_series_through_second_enzyme')


def _standard_curve_fit(record, native):
    value = _value(record, 'standard_curve_r_squared')
    if value is None:
        return _result('unknown', 'r_squared_not_stated', [])
    native.update({'r_squared': value, 'r_squared_refs': _refs(record['quantities']['standard_curve_r_squared'])})
    return _result('unknown', 'r_squared_recorded_for_the_sheet', [])


def _standard_series_size(record, native):
    value = _value(record, 'standard_series_points')
    if value is None:
        return _result('unknown', 'standard_points_not_stated', [])
    native.update({'standard_points': value, 'standard_points_refs': _refs(record['quantities']['standard_series_points'])})
    return _result('unknown', 'standard_points_recorded_for_the_sheet', [])


def _read_inside_standard_series(record, native):
    fact = record['facts']['read_amount_within_standard_series']
    if fact['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', fact['source_refs'])
    read = record['quantities']['read_amount']
    if read['status'] == 'point':
        kind, amount = _scaled(read)
        ends = {name: _scaled(record['quantities'][name])[1] for name in STANDARD_ENDS
                if record['quantities'][name]['status'] == 'point' and _scaled(record['quantities'][name])[0] == kind}
        if ends:
            native.update({'read_over_standard_high': amount / ends['standard_series_high'] if 'standard_series_high' in ends else None,
                           'read_over_standard_low': amount / ends['standard_series_low'] if 'standard_series_low' in ends else None,
                           'standard_refs': _refs(read, *[record['quantities'][name] for name in ends])})
            return _result('unknown', 'read_position_recorded_for_the_sheet', [])
    if fact['answer'] == 'yes':
        return _result('supported', 'read_within_series_stated', fact['source_refs'])
    return _result('unknown', 'read_or_series_missing_or_not_comparable', [])


def _matrix_effect_addressed(record, native):
    return _any_yes(record, ('matrix_matched_standards', 'spike_recovery_done'), 'matrix_control_stated')


def _second_enzyme_specificity(record, native):
    return _one_fact(record, 'second_enzyme_specificity_checked')


def _product_identity(record, native):
    return _any_yes(record, ('product_confirmed_independently', 'substrate_loss_matches_product_gain'), 'product_identity_stated')


def _first_enzyme_controls(record, native):
    return _any_yes(record, ('no_enzyme_control', 'inactive_enzyme_control', 'zero_time_sample'), 'enzyme_free_control_stated')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'enzyme_dependence_shown')


def _endpoint_time_alignment(record, native):
    time = record['quantities']['endpoint_time']
    stopped = record['facts']['reaction_stopped_before_analysis']
    same = record['facts']['same_time_for_compared_arms']
    answered_no = [item for item in (stopped, same) if item['answer'] == 'no']
    if answered_no:
        return _result('conflicting', 'fact_answered_no', _refs(*answered_no))
    if time['status'] != 'point':
        return _result('unknown', 'endpoint_time_not_stated', [])
    if stopped['answer'] == 'yes':
        return _result('supported', 'time_and_stop_stated', _refs(time, stopped, *([same] if same['answer'] == 'yes' else [])))
    return _result('unknown', 'reaction_stop_not_stated', [])


def _reporter_completion(record, native):
    fact = record['facts']['reporter_conversion_complete']
    incubation = record['quantities']['second_enzyme_incubation']
    if fact['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', fact['source_refs'])
    if fact['answer'] == 'yes':
        return _result('supported', 'second_reaction_completion_stated', fact['source_refs'])
    if incubation['status'] == 'point':
        native.update({'incubation_minutes': incubation['value'] * MIN_PER_UNIT[incubation['unit']], 'incubation_refs': _refs(incubation)})
        return _result('unknown', 'incubation_recorded_for_the_sheet', [])
    return _result('unknown', 'second_reaction_completion_not_stated', [])


def _initial_substrate(record, native):
    fact = record['facts']['initial_substrate_determined']
    concentration = record['quantities']['substrate_initial']
    if fact['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', fact['source_refs'])
    if fact['answer'] == 'yes' or concentration['status'] == 'point':
        return _result('supported', 'initial_substrate_stated', _refs(concentration, fact))
    return _result('unknown', 'initial_substrate_not_stated', [])


def _non_detection_limit(record, native):
    if record['facts']['conversion_detected_above_control']['answer'] != 'no':
        return _result('not_applicable', 'no_non_detection_stated', [])
    limit = record['quantities']['detection_limit']
    initial = record['quantities']['substrate_initial']
    if limit['status'] != 'point' or initial['status'] != 'point':
        return _result('unknown', 'detection_limit_or_substrate_not_stated', [])
    native.update({'limit_over_initial': limit['value'] * UM_PER_UNIT[limit['unit']] / (initial['value'] * UM_PER_UNIT[initial['unit']]), 'limit_refs': _refs(limit, initial)})
    return _result('unknown', 'detection_limit_recorded_for_the_sheet', [])


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


EVALUATORS = {'estimate_identity': _estimate_identity, 'standard_series_through_second_enzyme': _standard_series_through_second_enzyme, 'standard_curve_fit': _standard_curve_fit,
              'standard_series_size': _standard_series_size, 'read_inside_standard_series': _read_inside_standard_series, 'matrix_effect_addressed': _matrix_effect_addressed,
              'second_enzyme_specificity': _second_enzyme_specificity, 'product_identity': _product_identity, 'first_enzyme_controls': _first_enzyme_controls,
              'enzyme_dependence': _enzyme_dependence, 'endpoint_time_alignment': _endpoint_time_alignment, 'reporter_completion': _reporter_completion,
              'initial_substrate': _initial_substrate, 'non_detection_limit': _non_detection_limit, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme,
              'replicates': _replicates}


def grade_endpoint_enzymatic_assay(record):
    """Grade one end-point determination with a second enzyme. Returns the criterion answers and native values."""
    detected = record['facts']['conversion_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'conversion': CONVERSION.get(detected['answer']), 'conversion_refs': list(detected['source_refs']) if detected['answer'] in CONVERSION else [], 'conversion_support': detected['support'],
              'r_squared': None, 'r_squared_refs': [], 'standard_points': None, 'standard_points_refs': [], 'read_over_standard_high': None, 'read_over_standard_low': None, 'standard_refs': [],
              'incubation_minutes': None, 'incubation_refs': [], 'limit_over_initial': None, 'limit_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ENDPOINT_ENZYMATIC_ASSAY_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'endpoint_enzymatic_assay', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
