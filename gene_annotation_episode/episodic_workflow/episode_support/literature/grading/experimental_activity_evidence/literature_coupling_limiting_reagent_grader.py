"""Coupling_limiting_reagent grader: judges ONE limiting-reagent endpoint experiment (a reaction run to completion with one cofactor or co-substrate limiting; the
product set against the limiting reagent used up, as equivalents per product or as a yield) by its own standards. DRAFT 2026-11-22, owner to correct.

Hand-built and private to coupling_limiting_reagent. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_coupling_limiting_reagent_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable) with support refs, the reason
code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_coupling_limiting_reagent_criteria.py (the single source).
This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (remaining_percent, excess_fold,
equivalents_over_coefficient, titration_points, replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs;
the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all 'not_applicable' ->
not_applicable; else supported. A 'supported' or 'conflicting' result always carries support refs (_result raises without them).

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion (native 'support': criterion id -> the
supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact coupled_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying whether it saw the
claimed product formed from the limiting reagent above its own control or detection limit. It is recorded in native as 'detected' with its refs and its support (class decision
of 2026-11-22: 'interaction_detected' reads "coupled product formation detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the preparations, spread_kind, limiting_reagent_kind, and remaining_percent, excess_fold, equivalents_over_coefficient,
titration_points, replicate_count, replicate_independent, detected, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupling_limiting_reagent_criteria import COUPLING_LIMITING_REAGENT_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_coupling_limiting_reagent_grade'
CRITERIA = tuple(criterion['id'] for criterion in COUPLING_LIMITING_REAGENT_CRITERIA)
DETECTED = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact coupled_product_detected


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


def _completion_shown(record, native):
    items = [record['facts']['completion_shown'], record['facts']['limiting_reagent_consumed_fully']]
    answers = [item['answer'] for item in items]
    remaining = _value(record, 'limiting_reagent_remaining')
    if 'no' in answers:
        return _result('conflicting', 'fact_answered_no', _refs(*[item for item in items if item['answer'] == 'no']))
    if remaining is not None:
        native.update({'remaining_percent': remaining, 'remaining_refs': _refs(record['quantities']['limiting_reagent_remaining'], *items)})
        return _result('unknown', 'remaining_recorded_for_the_sheet', [])
    if 'yes' in answers:      # one stated completion is enough
        return _result('supported', 'completion_stated', _refs(*[item for item in items if item['answer'] == 'yes']))
    if all(answer == 'not_applicable' for answer in answers):
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'fact_unknown', [])


def _excess_of_other_reagents(record, native):
    excess = record['facts']['other_reagents_in_excess']
    fold = _value(record, 'excess_over_limiting')
    refs = _refs(record['quantities']['excess_over_limiting'], excess)
    if excess['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if fold is not None:
        native.update({'excess_fold': fold, 'excess_refs': refs})
        return _result('unknown', 'excess_recorded_for_the_sheet', [])
    if excess['answer'] == 'yes':
        return _result('supported', 'excess_stated', refs)
    return _result('unknown', 'excess_not_stated', [])


def _no_regeneration(record, native):
    return _one_fact(record, 'no_regeneration')


def _limiting_amount_verified(record, native):
    return _one_fact(record, 'limiting_amount_verified')


def _reaction_coefficient(record, native):
    coefficient = _value(record, 'stoichiometric_coefficient')
    measured = _value(record, 'limiting_reagent_per_product')
    if coefficient is None:
        return _result('unknown', 'coefficient_not_stated', [])
    if measured is None:
        return _result('supported', 'coefficient_stated', _refs(record['quantities']['stoichiometric_coefficient']))
    native.update({'equivalents_over_coefficient': measured / coefficient, 'equivalents_refs': _refs(record['quantities']['stoichiometric_coefficient'], record['quantities']['limiting_reagent_per_product'])})
    return _result('unknown', 'equivalents_recorded_for_the_sheet', [])


def _product_identity(record, native):
    return _one_fact(record, 'product_identified')


def _product_calibration(record, native):
    return _one_fact(record, 'product_calibrated')


def _same_reaction(record, native):
    items = [record['facts']['same_mixture'], record['facts']['same_endpoint']]
    status, reason = _shared_rule([item['answer'] for item in items])
    deciding = [item for item in items if item['answer'] == ('no' if status == 'conflicting' else 'yes')]
    return _result(status, reason, _refs(*deciding))


def _no_enzyme_control(record, native):
    return _one_fact(record, 'no_enzyme_control')


def _no_substrate_control(record, native):
    return _one_fact(record, 'no_substrate_control')


def _inactive_enzyme_control(record, native):
    return _one_fact(record, 'inactive_enzyme_control')


def _titration_points(record, native):
    count = _value(record, 'titration_points')
    if count is None:
        return _result('unknown', 'titration_points_not_stated', [])
    native.update({'titration_points': count, 'titration_refs': _refs(record['quantities']['titration_points'])})
    return _result('unknown', 'titration_points_recorded_for_the_sheet', [])


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


EVALUATORS = {'completion_shown': _completion_shown, 'excess_of_other_reagents': _excess_of_other_reagents,
              'no_regeneration': _no_regeneration, 'limiting_amount_verified': _limiting_amount_verified, 'reaction_coefficient': _reaction_coefficient,
              'product_identity': _product_identity, 'product_calibration': _product_calibration, 'same_reaction': _same_reaction, 'no_enzyme_control': _no_enzyme_control,
              'no_substrate_control': _no_substrate_control, 'inactive_enzyme_control': _inactive_enzyme_control, 'titration_points': _titration_points,
              'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_coupling_limiting_reagent(record):
    """Grade one limiting-reagent endpoint experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['coupled_product_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'limiting_reagent_kind': record['limiting_reagent_kind'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'detected': DETECTED.get(detected['answer']), 'detected_refs': list(detected['source_refs']) if detected['answer'] in DETECTED else [], 'detected_support': detected['support'],
              'remaining_percent': None, 'remaining_refs': [], 'excess_fold': None, 'excess_refs': [], 'equivalents_over_coefficient': None, 'equivalents_refs': [],
              'titration_points': None, 'titration_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, COUPLING_LIMITING_REAGENT_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'coupling_limiting_reagent', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()},
            'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
