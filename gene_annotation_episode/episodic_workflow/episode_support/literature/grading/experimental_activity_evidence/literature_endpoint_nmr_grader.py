"""Endpoint_nmr grader: judges ONE NMR end-point conversion experiment by its own standards. DRAFT, owner to correct.

Hand-built and private to endpoint_nmr. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_endpoint_nmr_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_endpoint_nmr_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(relaxation_delay_s and longest_t1_s, signal_to_noise, acquisition_over_endpoint_time, detection_limit_fraction, replicate_count, each with its refs) and returns
'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact conversion_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying
whether it saw conversion above its own control or detection limit. It is recorded in native as 'conversion_statement' with its refs and its support (class decision
of the endpoint_conversion class: 'interaction_detected' reads "conversion detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the preparations, spread_kind, and relaxation_delay_s, longest_t1_s, signal_to_noise,
acquisition_over_endpoint_time, detection_limit_fraction, replicate_count, replicate_independent, conversion_statement, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_nmr_criteria import (
    ENDPOINT_NMR_CRITERIA, MINUTES_PER_UNIT, PERCENT_PER_FRACTION, SECONDS_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_endpoint_nmr_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in ENDPOINT_NMR_CRITERIA)
CONVERSION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact conversion_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _seconds(record, name):
    value = _value(record, name)
    return None if value is None else value * SECONDS_PER_UNIT[record['quantities'][name]['unit']]


def _minutes(record, name):
    value = _value(record, name)
    return None if value is None else value * MINUTES_PER_UNIT[record['quantities'][name]['unit']]


def _fraction(record, name):
    value = _value(record, name)
    return None if value is None else value / PERCENT_PER_FRACTION if record['quantities'][name]['unit'] == 'percent' else value


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
    names = ('no_enzyme_control', 'inactive_enzyme_control')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'spontaneous_reaction_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _enzyme_dependence(record, native):
    return _one_fact(record, 'enzyme_dependence_shown')


def _product_assignment(record, native):
    return _one_fact(record, 'product_signal_assigned')


def _mass_balance(record, native):
    return _one_fact(record, 'substrate_loss_matches_product_gain')


def _relaxation_delay(record, native):
    quantitative = record['facts']['quantitative_acquisition']
    delay = _seconds(record, 'relaxation_delay')
    refs = _refs(record['quantities']['relaxation_delay'], record['quantities']['longest_t1'], quantitative)
    if quantitative['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if delay is not None:
        native.update({'relaxation_delay_s': delay, 'longest_t1_s': _seconds(record, 'longest_t1'), 'relaxation_refs': refs})
        return _result('unknown', 'relaxation_delay_recorded_for_the_sheet', [])
    if quantitative['answer'] == 'yes':
        return _result('supported', 'quantitative_acquisition_stated', refs)
    return _result('unknown', 'relaxation_not_stated', [])


def _signal_to_noise(record, native):
    value = _value(record, 'signal_to_noise')
    if value is None:
        return _result('unknown', 'signal_to_noise_not_stated', [])
    native.update({'signal_to_noise': value, 'signal_to_noise_refs': _refs(record['quantities']['signal_to_noise'])})
    return _result('unknown', 'signal_to_noise_recorded_for_the_sheet', [])


def _signals_resolved(record, native):
    return _one_fact(record, 'signals_resolved')


def _time_alignment(record, native):
    same, stopped = record['facts']['same_time_for_compared_arms'], record['facts']['reaction_stopped_before_analysis']
    time, acquisition = record['quantities']['endpoint_time'], record['quantities']['acquisition_duration']
    if same['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', _refs(same))
    if time['status'] != 'point':
        return _result('unknown', 'endpoint_time_not_stated', [])
    if stopped['answer'] == 'yes':
        return _result('supported', 'reaction_stopped_at_the_stated_time', _refs(time, stopped))
    if acquisition['status'] != 'point':
        return _result('unknown', 'acquisition_window_not_stated', [])
    native.update({'acquisition_over_endpoint_time': _minutes(record, 'acquisition_duration') / _minutes(record, 'endpoint_time'), 'window_refs': _refs(time, acquisition)})
    return _result('unknown', 'acquisition_window_recorded_for_the_sheet', [])


def _integral_denominator(record, native):
    items = [record['facts'][n] for n in ('both_species_integrated', 'initial_substrate_determined', 'internal_standard_used')]
    answers = [item['answer'] for item in items]
    if 'yes' in answers:
        return _result('supported', 'denominator_fixed_by_the_spectra', _refs(*(item for item in items if item['answer'] == 'yes')))
    if all(a == 'no' for a in answers):
        return _result('conflicting', 'no_denominator_reference', _refs(*items))
    return _result('unknown', 'denominator_not_stated', [])


def _non_detection_limit(record, native):
    detected = record['facts']['conversion_detected_above_control']
    if detected['answer'] != 'no':
        return _result('not_applicable', 'not_a_stated_non_detection', [])
    limit = _fraction(record, 'detection_limit')
    if limit is None:
        return _result('unknown', 'detection_limit_not_stated', [])
    native.update({'detection_limit_fraction': limit, 'detection_refs': _refs(record['quantities']['detection_limit'], detected)})
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


EVALUATORS = {'spontaneous_reaction_control': _spontaneous_reaction_control, 'enzyme_dependence': _enzyme_dependence, 'product_assignment': _product_assignment,
              'mass_balance': _mass_balance, 'relaxation_delay': _relaxation_delay, 'signal_to_noise': _signal_to_noise, 'signals_resolved': _signals_resolved,
              'time_alignment': _time_alignment, 'integral_denominator': _integral_denominator, 'non_detection_limit': _non_detection_limit,
              'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme, 'replicates': _replicates}


def grade_endpoint_nmr(record):
    """Grade one NMR end-point conversion record. Returns the criterion answers and native values."""
    detected = record['facts']['conversion_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'conversion_statement': CONVERSION.get(detected['answer']), 'conversion_statement_refs': list(detected['source_refs']) if detected['answer'] in CONVERSION else [],
              'conversion_statement_support': detected['support'],
              'relaxation_delay_s': None, 'longest_t1_s': None, 'relaxation_refs': [], 'signal_to_noise': None, 'signal_to_noise_refs': [],
              'acquisition_over_endpoint_time': None, 'window_refs': [], 'detection_limit_fraction': None, 'detection_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ENDPOINT_NMR_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'endpoint_nmr', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
