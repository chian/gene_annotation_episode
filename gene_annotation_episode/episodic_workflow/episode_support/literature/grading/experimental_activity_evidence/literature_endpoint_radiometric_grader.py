"""Endpoint_radiometric grader: judges ONE radiometric end-point conversion experiment (a substrate that carries a radioactive label is incubated with the enzyme for a stated time, the reaction is stopped, the labelled product is separated from the labelled substrate and counted; the result is the share converted, or the amount of product, at that time) by its own standards.

Hand-built and private to endpoint_radiometric. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_endpoint_radiometric_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_endpoint_radiometric_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(signal_over_background with counts_refs, replicate_count with replicate_independent and replicate_refs) and returns 'unknown' with a reason
ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact conversion_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the
paper itself saying whether it saw conversion above its own control. It is recorded in native as 'conversion_statement' with its refs and its
support (class decision, owner to confirm: 'interaction_detected' reads "conversion detected"). It is only used by the converter when no effect
is stated.

Native values retained: every record quantity as given, the choices, the preparations, and signal_over_background (the ratio of the counts, or
the stated ratio when no pair of counts is given; the pair wins when both are stated), counts_refs, replicate_count, replicate_independent,
replicate_refs, conversion_statement, conversion_statement_refs and conversion_statement_support (each None or empty when not stated).
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_radiometric_criteria import ENDPOINT_RADIOMETRIC_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_endpoint_radiometric_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in ENDPOINT_RADIOMETRIC_CRITERIA)
CONVERSION_STATEMENT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact conversion_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


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


def _either_fact_done(record, names, supported_reason):
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', supported_reason, refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _spontaneous_conversion_control(record, native):
    return _either_fact_done(record, ('no_enzyme_control_done', 'inactive_enzyme_control_done'), 'spontaneous_conversion_control_stated')


def _separation_background_control(record, native):
    return _either_fact_done(record, ('separation_control_done', 'zero_time_sample_done'), 'separation_background_control_stated')


def _counts_over_background(record, native):
    quantities = record['quantities']
    test, background, stated = _value(record, 'counts_test'), _value(record, 'counts_background'), _value(record, 'signal_over_background')
    if test is not None and background is not None:
        if quantities['counts_test']['unit'] != quantities['counts_background']['unit'] and stated is None:
            return _result('unknown', 'counts_in_different_units', [])
        if quantities['counts_test']['unit'] == quantities['counts_background']['unit']:
            native.update({'signal_over_background': test / background, 'counts_refs': _refs(quantities['counts_test'], quantities['counts_background'])})
            return _result('unknown', 'counts_recorded_for_the_sheet', [])
    if stated is not None:
        native.update({'signal_over_background': stated, 'counts_refs': _refs(quantities['signal_over_background'])})
        return _result('unknown', 'counts_recorded_for_the_sheet', [])
    return _result('unknown', 'counts_not_stated', [])


def _specific_radioactivity_stated(record, native):
    if _value(record, 'product_amount') is None:
        return _result('not_applicable', 'no_product_amount_stated', [])
    if _value(record, 'specific_radioactivity') is None:
        return _result('unknown', 'specific_radioactivity_not_stated', [])
    return _result('supported', 'specific_radioactivity_stated', _refs(record['quantities']['product_amount'], record['quantities']['specific_radioactivity']))


def _counting_efficiency(record, native):
    return _one_fact(record, 'counting_efficiency_corrected')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'conversion_depends_on_enzyme')


def _product_identity(record, native):
    return _one_fact(record, 'product_identified_by_standard')


def _label_in_product_position(record, native):
    return _one_fact(record, 'label_in_product_position')


def _endpoint_time_and_stop(record, native):
    stop = record['facts']['reaction_stopped_before_analysis']
    refs = _refs(record['quantities']['endpoint_time'], stop)
    if stop['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if _value(record, 'endpoint_time') is not None and stop['answer'] == 'yes':
        return _result('supported', 'time_and_stop_stated', refs)
    return _result('unknown', 'time_or_stop_not_stated', [])


def _same_time_in_compared_arms(record, native):
    return _one_fact(record, 'same_time_for_compared_arms')


def _fraction_over_total_label(record, native):
    return _one_fact(record, 'fraction_over_total_label')


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


EVALUATORS = {'spontaneous_conversion_control': _spontaneous_conversion_control, 'separation_background_control': _separation_background_control,
              'counts_over_background': _counts_over_background, 'specific_radioactivity_stated': _specific_radioactivity_stated,
              'counting_efficiency': _counting_efficiency, 'enzyme_dependence': _enzyme_dependence, 'product_identity': _product_identity,
              'label_in_product_position': _label_in_product_position, 'endpoint_time_and_stop': _endpoint_time_and_stop,
              'same_time_in_compared_arms': _same_time_in_compared_arms, 'fraction_over_total_label': _fraction_over_total_label,
              'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme, 'replicates': _replicates}


def grade_endpoint_radiometric(record):
    """Grade one radiometric end-point conversion record. Returns the criterion answers and native values."""
    detected = record['facts']['conversion_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'label_isotope': record['label_isotope'], 'separation_method': record['separation_method'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'conversion_statement': CONVERSION_STATEMENT.get(detected['answer']), 'conversion_statement_refs': list(detected['source_refs']) if detected['answer'] in CONVERSION_STATEMENT else [],
              'conversion_statement_support': detected['support'],
              'signal_over_background': None, 'counts_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ENDPOINT_RADIOMETRIC_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'endpoint_radiometric', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
