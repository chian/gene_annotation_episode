"""Coupling_electron_balance grader: judges ONE electron balance of a reaction by its own standards.

Hand-built and private to coupling_electron_balance. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_coupling_electron_balance_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_coupling_electron_balance_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(background_share, recovery_fraction, standard_recovery_fraction, replicate_count, each with its refs) and returns 'unknown' with a reason ending
in '_recorded_for_the_sheet', and no refs; the converter judges it. The only arithmetic is a change of unit (FIXED_BY_DEFINITION, in the criteria
file) and the balance itself: the electrons recovered in the product are the electrons per product times the product formed, and the share is
that over the electrons delivered, worked out only when the passage states the three numbers.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact product_detected_from_electrons ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw product formed from the delivered electrons above its own control. It is recorded in native as 'product_detected' with
its refs and its support (class decision of the inventory: 'interaction_detected' reads "coupled product formation detected"). It is only used by
the converter when no share can be stated or worked out.

Native values retained: every record quantity as given, the preparations, the three plain choices, and background_share, recovery_fraction (with
recovery_origin 'reported' or 'derived', recovery_support and recovery_refs), electrons_delivered_umol and electrons_in_product_umol (with
balance_refs and balance_support, when the three amounts are stated), standard_recovery_fraction, replicate_count, replicate_independent,
product_detected, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupling_electron_balance_criteria import (
    COUPLING_ELECTRON_BALANCE_CRITERIA, PERCENT_PER_FRACTION, UMOL_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, criterion_supports

VERSION = 'a105_coupling_electron_balance_grade'
CRITERIA = tuple(criterion['id'] for criterion in COUPLING_ELECTRON_BALANCE_CRITERIA)
DETECTED = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact product_detected_from_electrons


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _umol(record, name):
    value = _value(record, name)
    return None if value is None else value * UMOL_PER_UNIT[record['quantities'][name]['unit']]


def _fraction(record, name):
    value = _value(record, name)
    return None if value is None else value / PERCENT_PER_FRACTION if record['quantities'][name]['unit'] == 'percent' else value


def _refs(*items):
    refs = []
    for item in items:
        refs += item['source_refs']
    return list(dict.fromkeys(refs))


def _weakest(*items):
    return max((item['support'] for item in items), key=SUPPORTS.index)


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


def _facts(record, *names):
    status, reason = _shared_rule([record['facts'][n]['answer'] for n in names])
    return _result(status, reason, _refs(*(record['facts'][n] for n in names)))


def _no_enzyme_control(record, native):
    return _facts(record, 'no_enzyme_control')


def _background_electrons(record, native):
    subtracted = record['facts']['background_charge_subtracted']
    background, delivered = _umol(record, 'background_electrons'), _umol(record, 'electrons_delivered')
    refs = _refs(record['quantities']['background_electrons'], record['quantities']['electrons_delivered'], subtracted)
    if subtracted['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', _refs(subtracted))
    if background is not None and delivered is not None:
        native.update({'background_share': background / delivered, 'background_refs': refs})
        return _result('unknown', 'background_recorded_for_the_sheet', [])
    if subtracted['answer'] == 'yes':
        return _result('supported', 'background_charge_subtracted_stated', _refs(subtracted))
    return _result('unknown', 'background_not_stated', [])


def _inactive_enzyme_control(record, native):
    return _facts(record, 'inactive_enzyme_control')


def _product_identity(record, native):
    return _facts(record, 'product_identified')


def _electrons_per_product_stated(record, native):
    if _value(record, 'electrons_per_product') is None:
        return _result('unknown', 'electrons_per_product_not_stated', [])
    return _result('supported', 'electrons_per_product_stated', _refs(record['quantities']['electrons_per_product']))


def _electron_closure(record, native):
    stated = _fraction(record, 'productive_fraction')
    if stated is not None:
        operand = record['quantities']['productive_fraction']
        native.update({'recovery_fraction': stated, 'recovery_origin': 'reported', 'recovery_support': operand['support'], 'recovery_refs': _refs(operand)})
        return _result('unknown', 'closure_recorded_for_the_sheet', [])
    if native['electrons_delivered_umol'] is None:
        return _result('unknown', 'closure_not_stated', [])
    native.update({'recovery_fraction': native['electrons_in_product_umol'] / native['electrons_delivered_umol'], 'recovery_origin': 'derived',
                   'recovery_support': native['balance_support'], 'recovery_refs': list(native['balance_refs'])})
    return _result('unknown', 'closure_recorded_for_the_sheet', [])


def _both_sides_stated(record, native):
    if _value(record, 'electrons_delivered') is None or _value(record, 'product_formed') is None:
        return _result('unknown', 'an_amount_not_stated', [])
    return _result('supported', 'both_amounts_stated', _refs(record['quantities']['electrons_delivered'], record['quantities']['product_formed']))


def _delivery_calibration(record, native):
    return _facts(record, 'delivery_calibrated')


def _product_calibration(record, native):
    return _facts(record, 'product_calibrated')


def _standard_recovery(record, native):
    recovery = _fraction(record, 'standard_recovery')
    if recovery is None:
        return _result('unknown', 'standard_recovery_not_stated', [])
    native.update({'standard_recovery_fraction': recovery, 'standard_recovery_refs': _refs(record['quantities']['standard_recovery'])})
    return _result('unknown', 'standard_recovery_recorded_for_the_sheet', [])


def _headspace_accounting(record, native):
    return _facts(record, 'headspace_accounted')


def _oxygen_excluded(record, native):
    return _facts(record, 'anaerobic_control')


def _mediator_bypass(record, native):
    return _facts(record, 'mediator_bypass_excluded')


def _matched_windows(record, native):
    return _facts(record, 'same_window', 'same_reaction_mixture')


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


def _native_electron_carrier(record, native):
    return _facts(record, 'native_electron_carrier')


def _purified_enzyme(record, native):
    return _facts(record, 'purified_enzyme')


EVALUATORS = {'no_enzyme_control': _no_enzyme_control, 'background_electrons': _background_electrons, 'inactive_enzyme_control': _inactive_enzyme_control,
              'product_identity': _product_identity, 'electrons_per_product_stated': _electrons_per_product_stated, 'electron_closure': _electron_closure,
              'both_sides_stated': _both_sides_stated, 'delivery_calibration': _delivery_calibration, 'product_calibration': _product_calibration,
              'standard_recovery': _standard_recovery, 'headspace_accounting': _headspace_accounting, 'oxygen_excluded': _oxygen_excluded,
              'mediator_bypass': _mediator_bypass, 'matched_windows': _matched_windows, 'replicates': _replicates,
              'native_electron_carrier': _native_electron_carrier, 'purified_enzyme': _purified_enzyme}


def _balance(record, native):
    """The electrons delivered and the electrons recovered in the product, both in umol, when the passage states the three numbers."""
    operands = [record['quantities'][n] for n in ('electrons_delivered', 'product_formed', 'electrons_per_product')]
    if any(operand['status'] != 'point' for operand in operands):
        return
    delivered, formed, per_product = _umol(record, 'electrons_delivered'), _umol(record, 'product_formed'), _value(record, 'electrons_per_product')
    native.update({'electrons_delivered_umol': delivered, 'electrons_in_product_umol': per_product * formed, 'balance_refs': _refs(*operands), 'balance_support': _weakest(*operands)})


def grade_coupling_electron_balance(record):
    """Grade one electron balance record. Returns the criterion answers and native values."""
    detected = record['facts']['product_detected_from_electrons']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'delivery_kind': record['delivery_kind'], 'product_kind': record['product_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'product_detected': DETECTED.get(detected['answer']), 'product_detected_refs': list(detected['source_refs']) if detected['answer'] in DETECTED else [], 'product_detected_support': detected['support'],
              'electrons_delivered_umol': None, 'electrons_in_product_umol': None, 'balance_refs': [], 'balance_support': None,
              'background_share': None, 'background_refs': [], 'recovery_fraction': None, 'recovery_origin': None, 'recovery_support': None, 'recovery_refs': [],
              'standard_recovery_fraction': None, 'standard_recovery_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    _balance(record, native)
    native['support'] = criterion_supports(record, COUPLING_ELECTRON_BALANCE_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'coupling_electron_balance', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
