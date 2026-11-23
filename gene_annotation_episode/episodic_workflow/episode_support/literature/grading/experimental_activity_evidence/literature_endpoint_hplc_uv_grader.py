"""Endpoint_hplc_uv grader: judges ONE fixed-time enzyme reaction read by HPLC by its own standards. DRAFT of 2026-11-22, owner to correct.

Hand-built and private to endpoint_hplc_uv. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_endpoint_hplc_uv_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_endpoint_hplc_uv_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness, and no number at all. Where a number would be compared with a limit it records the number with its
refs (test_percent and control_percent, read_over_curve_low and read_over_curve_high, calibration_points, detection_limit_over_substrate,
replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. Three criteria read two facts of which one stated yes is enough (the spontaneous-reaction control, the
product identification, the denominator, the matrix control): a yes supports; with no yes the shared rule applies.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact conversion_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw conversion above its own control. It is recorded in native as 'conversion' with its refs and its support (class
decision: 'interaction_detected' reads "conversion detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the preparations, spread_kind and detector, and test_percent, control_percent, read_over_curve_low,
read_over_curve_high, calibration_points, detection_limit_over_substrate, replicate_count, replicate_independent, conversion, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_hplc_uv_criteria import ENDPOINT_HPLC_UV_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_endpoint_hplc_uv_grade'
CRITERIA = tuple(criterion['id'] for criterion in ENDPOINT_HPLC_UV_CRITERIA)
CONVERSION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact conversion_detected_above_control


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


def _either_fact(record, names, stated_reason):
    items = [record['facts'][name] for name in names]
    answers = [item['answer'] for item in items]
    if 'yes' in answers:
        return _result('supported', stated_reason, _refs(*(item for item in items if item['answer'] == 'yes')))
    status, reason = _shared_rule(answers)
    return _result(status, reason, _refs(*items))


def _estimate_defined(record, native):
    quantities = record['quantities']
    if _value(record, 'product_amount') is not None:
        return _result('supported', 'estimate_stated', _refs(quantities['product_amount']))
    shares = [name for name in ('net_conversion_percent', 'conversion_percent') if _value(record, name) is not None]
    if not shares:
        return _result('unknown', 'no_estimate_stated', [])
    if _value(record, 'substrate_initial') is None:
        return _result('unknown', 'substrate_amount_not_stated', [])
    return _result('supported', 'estimate_stated', _refs(*(quantities[name] for name in shares), quantities['substrate_initial']))


def _spontaneous_reaction_control(record, native):
    return _either_fact(record, ('no_enzyme_control_done', 'inactive_enzyme_control_done'), 'spontaneous_reaction_control_stated')


def _zero_time_sample(record, native):
    return _one_fact(record, 'zero_time_sample_done')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'enzyme_dependence_shown')


def _signal_over_control(record, native):
    test, control = _value(record, 'conversion_percent'), _value(record, 'control_conversion_percent')
    if test is None or control is None:
        return _result('unknown', 'test_or_control_conversion_not_stated', [])
    native.update({'test_percent': test, 'control_percent': control, 'control_refs': _refs(record['quantities']['conversion_percent'], record['quantities']['control_conversion_percent'])})
    return _result('unknown', 'control_comparison_recorded_for_the_sheet', [])


def _product_identified(record, native):
    return _either_fact(record, ('authentic_standard_used', 'peak_confirmed_by_second_method'), 'product_identified_stated')


def _mass_balance(record, native):
    return _one_fact(record, 'substrate_loss_matches_product_gain')


def _endpoint_time_stated(record, native):
    same = record['facts']['same_time_for_compared_arms']
    if same['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', same['source_refs'])
    if _value(record, 'endpoint_time') is None:
        return _result('unknown', 'endpoint_time_not_stated', [])
    return _result('supported', 'endpoint_time_stated', _refs(record['quantities']['endpoint_time']))


def _reaction_stopped(record, native):
    return _one_fact(record, 'reaction_stopped_before_analysis')


def _denominator_established(record, native):
    return _either_fact(record, ('initial_substrate_determined', 'both_species_quantified'), 'denominator_established_stated')


def _standard_curve_range(record, native):
    read, low, high = _nm(record, 'product_amount'), _nm(record, 'standard_curve_low'), _nm(record, 'standard_curve_high')
    if read is None or low is None or high is None:
        return _result('unknown', 'product_amount_or_curve_missing', [])
    native.update({'read_over_curve_low': read / low, 'read_over_curve_high': read / high,
                   'curve_refs': _refs(*(record['quantities'][name] for name in ('product_amount', 'standard_curve_low', 'standard_curve_high')))})
    return _result('unknown', 'standard_curve_range_recorded_for_the_sheet', [])


def _standard_curve_points(record, native):
    points = _value(record, 'standard_curve_points')
    if points is None:
        return _result('unknown', 'calibration_points_not_stated', [])
    native.update({'calibration_points': points, 'calibration_points_refs': _refs(record['quantities']['standard_curve_points'])})
    return _result('unknown', 'calibration_points_recorded_for_the_sheet', [])


def _detection_limit_share(record, native):
    limit, substrate = _nm(record, 'detection_limit'), _nm(record, 'substrate_initial')
    if limit is None or substrate is None:
        return _result('unknown', 'detection_limit_or_substrate_missing', [])
    native.update({'detection_limit_over_substrate': limit / substrate, 'detection_limit_refs': _refs(record['quantities']['detection_limit'], record['quantities']['substrate_initial'])})
    return _result('unknown', 'detection_limit_recorded_for_the_sheet', [])


def _matrix_matched_calibration(record, native):
    return _either_fact(record, ('calibration_in_matrix', 'internal_standard_used'), 'matrix_control_stated')


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


EVALUATORS = {'estimate_defined': _estimate_defined, 'spontaneous_reaction_control': _spontaneous_reaction_control, 'zero_time_sample': _zero_time_sample,
              'enzyme_dependence': _enzyme_dependence, 'signal_over_control': _signal_over_control, 'product_identified': _product_identified,
              'mass_balance': _mass_balance, 'endpoint_time_stated': _endpoint_time_stated, 'reaction_stopped': _reaction_stopped,
              'denominator_established': _denominator_established, 'standard_curve_range': _standard_curve_range, 'standard_curve_points': _standard_curve_points,
              'detection_limit_share': _detection_limit_share, 'matrix_matched_calibration': _matrix_matched_calibration, 'replicates': _replicates,
              'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_endpoint_hplc_uv(record):
    """Grade one fixed-time HPLC reaction record. Returns the criterion answers and native values."""
    detected = record['facts']['conversion_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'detector': record['detector'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'conversion': CONVERSION.get(detected['answer']), 'conversion_refs': list(detected['source_refs']) if detected['answer'] in CONVERSION else [], 'conversion_support': detected['support'],
              'test_percent': None, 'control_percent': None, 'control_refs': [], 'read_over_curve_low': None, 'read_over_curve_high': None, 'curve_refs': [],
              'calibration_points': None, 'calibration_points_refs': [], 'detection_limit_over_substrate': None, 'detection_limit_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ENDPOINT_HPLC_UV_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'endpoint_hplc_uv', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()},
            'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
